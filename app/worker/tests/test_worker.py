"""Unit tests (no AWS, no DB). A real ffmpeg run is included when ffmpeg is installed."""

import json
import shutil
import subprocess
import uuid

import pytest

from mytube_worker import db, main
from mytube_worker.transcode import build_command, transcode

VIDEO_ID = str(uuid.uuid4())
RAW_KEY = f"raw/user-1/{VIDEO_ID}"


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        (RAW_KEY, VIDEO_ID),
        (f"raw//{VIDEO_ID}", None),
        ("raw/user-1/not-a-uuid", None),
        (f"other/user-1/{VIDEO_ID}", None),
        (f"raw/user-1/{VIDEO_ID}/extra", None),
    ],
)
def test_parse_raw_key(key, expected):
    assert main.parse_raw_key(key) == expected


def test_object_keys_decodes_keys_and_ignores_test_events():
    event = {
        "Records": [
            {
                "eventName": "ObjectCreated:Put",
                "s3": {"bucket": {"name": "raw"}, "object": {"key": "raw/a%3Ab/" + VIDEO_ID}},
            }
        ]
    }
    assert main.object_keys(json.dumps(event)) == [("raw", f"raw/a:b/{VIDEO_ID}")]
    assert main.object_keys(json.dumps({"Event": "s3:TestEvent"})) == []


def test_build_command_maps_audio_only_when_present(tmp_path):
    with_audio = " ".join(build_command(tmp_path / "in", tmp_path, has_audio=True))
    without = " ".join(build_command(tmp_path / "in", tmp_path, has_audio=False))
    assert "v:0,a:0,name:360p v:1,a:1,name:720p" in with_audio
    assert "v:0,name:360p v:1,name:720p" in without
    assert "0:a:0" not in without


def test_deleted_video_is_skipped(monkeypatch):
    monkeypatch.setattr(db, "get_video", lambda *_: None)
    monkeypatch.setattr(db, "set_status", lambda *_: pytest.fail("must not update a missing row"))
    main.process_object("raw", RAW_KEY)


def test_failure_marks_failed_and_propagates(monkeypatch):
    statuses = []
    monkeypatch.setattr(db, "get_video", lambda *_: {"id": VIDEO_ID, "status": "UPLOADING"})
    monkeypatch.setattr(db, "set_status", lambda _id, status, *_: statuses.append(status) or True)
    monkeypatch.setattr(main.s3, "download_file", lambda *_: (_ for _ in ()).throw(OSError("boom")))
    with pytest.raises(OSError):
        main.process_object("raw", RAW_KEY)
    assert statuses == ["PROCESSING", "FAILED"]


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_real_transcode(tmp_path):
    src = tmp_path / "in.mp4"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc=duration=8:size=1280x720:rate=24",
         "-f", "lavfi", "-i", "sine=duration=8", "-shortest", str(src)],
        check=True,
    )  # fmt: skip
    out = tmp_path / "hls"
    transcode(src, out)
    master = (out / "master.m3u8").read_text()
    assert "360p/index.m3u8" in master and "720p/index.m3u8" in master
    assert list((out / "720p").glob("seg_*.ts"))

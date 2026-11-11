"""ffmpeg: one input file -> HLS with 360p and 720p renditions and a master playlist."""

import json
import subprocess
from pathlib import Path

# (name, height, video bitrate, maxrate, bufsize)
RENDITIONS = [
    ("360p", 360, "800k", "856k", "1200k"),
    ("720p", 720, "2800k", "2996k", "4200k"),
]
SEGMENT_SECONDS = 6
MAX_TRANSCODE_SECONDS = 2 * 3600

CONTENT_TYPES = {".m3u8": "application/vnd.apple.mpegurl", ".ts": "video/mp2t"}


class InvalidVideoError(Exception):
    """The input is not something we can transcode."""


def probe_streams(path: Path) -> set[str]:
    """Return the codec types present in the file, e.g. {"video", "audio"}."""
    try:
        out = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "json", str(path)],
            capture_output=True,
            check=True,
            text=True,
            timeout=120,
        ).stdout
    except subprocess.CalledProcessError as exc:
        raise InvalidVideoError(f"ffprobe failed: {exc.stderr.strip()[-500:]}") from exc
    return {s["codec_type"] for s in json.loads(out).get("streams", [])}


def build_command(src: Path, out_dir: Path, has_audio: bool) -> list[str]:
    n = len(RENDITIONS)
    split = f"[0:v]split={n}" + "".join(f"[v{i}]" for i in range(n))
    scales = [f"[v{i}]scale=w=-2:h={h}[v{i}out]" for i, (_, h, *_rest) in enumerate(RENDITIONS)]
    cmd = ["ffmpeg", "-hide_banner", "-nostdin", "-y", "-i", str(src)]
    cmd += ["-filter_complex", ";".join([split, *scales])]

    stream_map = []
    for i, (name, _h, bitrate, maxrate, bufsize) in enumerate(RENDITIONS):
        cmd += ["-map", f"[v{i}out]"]
        cmd += [f"-b:v:{i}", bitrate, f"-maxrate:v:{i}", maxrate, f"-bufsize:v:{i}", bufsize]
        stream_map.append(f"v:{i},a:{i},name:{name}" if has_audio else f"v:{i},name:{name}")
    if has_audio:
        for _ in RENDITIONS:
            cmd += ["-map", "0:a:0"]
        cmd += ["-c:a", "aac", "-b:a", "128k", "-ac", "2"]

    # Fixed GOP aligned to the segment length so every segment starts on a keyframe.
    cmd += ["-c:v", "libx264", "-preset", "veryfast", "-profile:v", "main", "-pix_fmt", "yuv420p"]
    cmd += ["-force_key_frames", f"expr:gte(t,n_forced*{SEGMENT_SECONDS})", "-sc_threshold", "0"]
    cmd += [
        "-f", "hls",
        "-hls_time", str(SEGMENT_SECONDS),
        "-hls_playlist_type", "vod",
        "-hls_flags", "independent_segments",
        "-hls_segment_filename", str(out_dir / "%v" / "seg_%04d.ts"),
        "-master_pl_name", "master.m3u8",
        "-var_stream_map", " ".join(stream_map),
        str(out_dir / "%v" / "index.m3u8"),
    ]  # fmt: skip
    return cmd


def transcode(src: Path, out_dir: Path) -> None:
    """Write out_dir/master.m3u8 plus out_dir/<rendition>/{index.m3u8,seg_*.ts}."""
    streams = probe_streams(src)
    if "video" not in streams:
        raise InvalidVideoError("no video stream")
    cmd = build_command(src, out_dir, has_audio="audio" in streams)
    try:
        subprocess.run(cmd, capture_output=True, check=True, text=True, timeout=MAX_TRANSCODE_SECONDS)
    except subprocess.CalledProcessError as exc:
        raise InvalidVideoError(f"ffmpeg failed: {exc.stderr.strip()[-1000:]}") from exc
    if not (out_dir / "master.m3u8").is_file():
        raise RuntimeError("ffmpeg produced no master playlist")

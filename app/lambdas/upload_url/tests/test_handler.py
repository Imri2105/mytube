"""Unit tests: no AWS or database (DB insert is patched; presigning works offline)."""

import json
from urllib.parse import parse_qs, urlparse

import pytest

import handler

VALID = {"contentType": "video/mp4", "filename": "cat.mp4", "size": 1024}


def _event(body):
    return {
        "requestContext": {"authorizer": {"claims": {"sub": "user-123"}}},
        "body": json.dumps(body) if not isinstance(body, str) else body,
    }


@pytest.fixture
def inserted(monkeypatch):
    rows = []
    monkeypatch.setattr(handler, "insert_video", lambda *args: rows.append(args))
    return rows


@pytest.mark.parametrize(
    "body",
    [
        "not json",
        [],
        {**VALID, "contentType": "text/html"},
        {**VALID, "size": 0},
        {**VALID, "size": handler.MAX_UPLOAD_BYTES + 1},
        {**VALID, "size": True},
        {**VALID, "filename": ""},
    ],
)
def test_rejects_bad_requests(body, inserted):
    assert handler.handler(_event(body), None)["statusCode"] == 400
    assert inserted == []


def test_returns_presigned_url_for_owner_prefix(inserted):
    resp = handler.handler(_event({**VALID, "title": "  My cat  "}), None)
    assert resp["statusCode"] == 201
    body = json.loads(resp["body"])

    (video_id, owner, title, raw_key) = inserted[0]
    assert str(video_id) == body["videoId"]
    assert (owner, title, raw_key) == ("user-123", "My cat", f"raw/user-123/{video_id}")

    url = urlparse(body["uploadUrl"])
    assert url.hostname == "test-raw.s3.il-central-1.amazonaws.com"
    assert url.path == f"/raw/user-123/{video_id}"
    signed = parse_qs(url.query)["X-Amz-SignedHeaders"][0].split(";")
    assert {"content-type", "content-length"} <= set(signed)


def test_title_defaults_to_filename(inserted):
    handler.handler(_event(VALID), None)
    assert inserted[0][2] == "cat"

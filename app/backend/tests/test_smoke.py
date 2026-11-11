"""Smoke tests: no AWS or database needed (lifespan isn't run, DB calls are patched)."""

import datetime as dt
import uuid

import pytest
from fastapi.testclient import TestClient

from mytube_api import db
from mytube_api.auth import current_user
from mytube_api.main import app

client = TestClient(app)
VIDEO_ID = uuid.uuid4()


def _row(owner="alice", status="READY"):
    return {
        "id": VIDEO_ID,
        "owner_sub": owner,
        "title": "cat",
        "status": status,
        "hls_path": f"videos/{VIDEO_ID}/master.m3u8" if status == "READY" else None,
        "created_at": dt.datetime(2026, 1, 1, tzinfo=dt.UTC),
    }


@pytest.fixture
def as_bob():
    app.dependency_overrides[current_user] = lambda: "bob"
    yield
    app.dependency_overrides.clear()


def test_healthz():
    assert client.get("/healthz").json() == {"status": "ok"}


def test_requires_token():
    assert client.get("/api/videos").status_code == 401


def test_rejects_garbage_token():
    resp = client.get("/api/videos", headers={"Authorization": "Bearer not-a-jwt"})
    assert resp.status_code == 401


def test_list_videos(as_bob, monkeypatch):
    monkeypatch.setattr(db, "fetch_all", lambda sql, params=(): [_row()])
    body = client.get("/api/videos").json()
    assert body[0]["hls_url"] == f"/videos/{VIDEO_ID}/master.m3u8"


def test_other_users_unfinished_video_is_hidden(as_bob, monkeypatch):
    monkeypatch.setattr(db, "fetch_one", lambda sql, params=(): _row(status="PROCESSING"))
    assert client.get(f"/api/videos/{VIDEO_ID}").status_code == 404


def test_delete_requires_owner(as_bob, monkeypatch):
    monkeypatch.setattr(db, "fetch_one", lambda sql, params=(): _row(owner="alice"))
    assert client.delete(f"/api/videos/{VIDEO_ID}").status_code == 403

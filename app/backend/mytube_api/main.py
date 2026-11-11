import os
import uuid
from contextlib import asynccontextmanager

import boto3
from fastapi import FastAPI, HTTPException, Response

from . import db
from .auth import User


@asynccontextmanager
async def lifespan(_app: FastAPI):
    db.create_schema()
    yield


app = FastAPI(title="MyTube API", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)

COLUMNS = "id, owner_sub, title, status, hls_path, created_at"


def _to_api(row: dict) -> dict:
    return {
        "id": str(row["id"]),
        "title": row["title"],
        "status": row["status"],
        "owner_sub": row["owner_sub"],
        "created_at": row["created_at"].isoformat(),
        # Served by CloudFront from processed-videos, never through this API.
        "hls_url": f"/{row['hls_path']}" if row["hls_path"] else None,
    }


@app.get("/healthz")
def healthz() -> dict:
    # Process-level only: a DB blip must not make the ALB drain every instance.
    return {"status": "ok"}


@app.get("/api/videos")
def list_videos(user: User, mine: bool = False) -> list[dict]:
    """READY videos newest first, or with ?mine=true all of the caller's videos (any status)."""
    if mine:
        sql = f"SELECT {COLUMNS} FROM videos WHERE owner_sub = %s ORDER BY created_at DESC LIMIT 100"
        rows = db.fetch_all(sql, (user,))
    else:
        sql = f"SELECT {COLUMNS} FROM videos WHERE status = 'READY' ORDER BY created_at DESC LIMIT 100"
        rows = db.fetch_all(sql)
    return [_to_api(r) for r in rows]


@app.get("/api/videos/{video_id}")
def get_video(video_id: uuid.UUID, user: User) -> dict:
    row = db.fetch_one(f"SELECT {COLUMNS} FROM videos WHERE id = %s", (video_id,))
    # Non-owners only see READY videos; anything else looks like it doesn't exist.
    if row is None or (row["status"] != "READY" and row["owner_sub"] != user):
        raise HTTPException(404, "video not found")
    return _to_api(row)


@app.delete("/api/videos/{video_id}", status_code=204)
def delete_video(video_id: uuid.UUID, user: User) -> Response:
    row = db.fetch_one("SELECT owner_sub, raw_key FROM videos WHERE id = %s", (video_id,))
    if row is None:
        raise HTTPException(404, "video not found")
    if row["owner_sub"] != user:
        raise HTTPException(403, "not the owner")

    # Objects first, then the row: if S3 fails the user can simply retry the delete.
    s3 = boto3.client("s3")
    processed = os.environ["PROCESSED_BUCKET"]
    pages = s3.get_paginator("list_objects_v2").paginate(Bucket=processed, Prefix=f"videos/{video_id}/")
    for page in pages:
        keys = [{"Key": o["Key"]} for o in page.get("Contents", [])]
        if keys:
            s3.delete_objects(Bucket=processed, Delete={"Objects": keys, "Quiet": True})
    s3.delete_object(Bucket=os.environ["RAW_BUCKET"], Key=row["raw_key"])

    db.execute("DELETE FROM videos WHERE id = %s", (video_id,))
    return Response(status_code=204)

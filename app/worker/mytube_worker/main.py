"""SQS consumer: S3 ObjectCreated events for raw uploads -> HLS in processed-videos.

The message is deleted only after the video is READY (or there is nothing left to do).
Any failure leaves it on the queue; after 3 receives SQS moves it to the DLQ.
"""

import json
import logging
import os
import signal
import tempfile
import threading
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import unquote_plus

import boto3

from . import db
from .transcode import CONTENT_TYPES, InvalidVideoError, transcode

log = logging.getLogger("worker")

QUEUE_URL = os.environ.get("QUEUE_URL", "")
PROCESSED_BUCKET = os.environ.get("PROCESSED_BUCKET", "")
ASG_NAME = os.environ.get("ASG_NAME", "")
HEARTBEAT_SECONDS = 300
VISIBILITY_EXTENSION_SECONDS = 900

sqs = boto3.client("sqs")
s3 = boto3.client("s3")
autoscaling = boto3.client("autoscaling")
_stopping = threading.Event()


def parse_raw_key(key: str) -> str | None:
    """raw/<ownerSub>/<videoId> -> videoId, or None for anything else."""
    parts = key.split("/")
    if len(parts) != 3 or parts[0] != "raw" or not parts[1]:
        return None
    try:
        return str(uuid.UUID(parts[2]))
    except ValueError:
        return None


def object_keys(message_body: str) -> list[tuple[str, str]]:
    """(bucket, key) pairs from an S3 event notification; [] for s3:TestEvent."""
    body = json.loads(message_body)
    return [
        (r["s3"]["bucket"]["name"], unquote_plus(r["s3"]["object"]["key"]))
        for r in body.get("Records", [])
        if r.get("eventName", "").startswith("ObjectCreated:")
    ]


# --- side effects -------------------------------------------------------------


def _instance_id() -> str | None:
    """Own instance ID via IMDSv2, or None when not on EC2 (local runs)."""
    try:
        req = urllib.request.Request(
            "http://169.254.169.254/latest/api/token",
            method="PUT",
            headers={"X-aws-ec2-metadata-token-ttl-seconds": "60"},
        )
        token = urllib.request.urlopen(req, timeout=2).read().decode()  # noqa: S310 (fixed IMDS URL)
        req = urllib.request.Request(
            "http://169.254.169.254/latest/meta-data/instance-id",
            headers={"X-aws-ec2-metadata-token": token},
        )
        return urllib.request.urlopen(req, timeout=2).read().decode()  # noqa: S310
    except OSError:
        return None


INSTANCE_ID: str | None = None  # set in run()


def _protect(on: bool) -> None:
    """Scale-in protection while busy, so the ASG never terminates a running transcode."""
    if not (INSTANCE_ID and ASG_NAME):
        return
    try:
        autoscaling.set_instance_protection(
            AutoScalingGroupName=ASG_NAME, InstanceIds=[INSTANCE_ID], ProtectedFromScaleIn=on
        )
    except Exception:
        log.exception("could not set scale-in protection=%s", on)


def _heartbeat(receipt_handle: str, done: threading.Event) -> None:
    """Keep the message invisible while ffmpeg runs, however long it takes."""
    while not done.wait(HEARTBEAT_SECONDS):
        try:
            sqs.change_message_visibility(
                QueueUrl=QUEUE_URL,
                ReceiptHandle=receipt_handle,
                VisibilityTimeout=VISIBILITY_EXTENSION_SECONDS,
            )
        except Exception:
            log.exception("visibility heartbeat failed")


def _delete_prefix(prefix: str) -> None:
    for page in s3.get_paginator("list_objects_v2").paginate(Bucket=PROCESSED_BUCKET, Prefix=prefix):
        keys = [{"Key": o["Key"]} for o in page.get("Contents", [])]
        if keys:
            s3.delete_objects(Bucket=PROCESSED_BUCKET, Delete={"Objects": keys, "Quiet": True})


def _upload_dir(local: Path, prefix: str) -> None:
    for path in sorted(local.rglob("*")):
        if path.is_file():
            s3.upload_file(
                str(path),
                PROCESSED_BUCKET,
                f"{prefix}{path.relative_to(local).as_posix()}",
                ExtraArgs={
                    "ContentType": CONTENT_TYPES.get(path.suffix, "application/octet-stream"),
                    "CacheControl": "public, max-age=31536000, immutable",
                },
            )


def process_object(bucket: str, key: str) -> None:
    """Transcode one raw upload. Returns normally when the message can be deleted."""
    video_id = parse_raw_key(key)
    if video_id is None:
        log.warning("ignoring unexpected key %s", key)
        return
    row = db.get_video(video_id, key)
    if row is None:
        log.info("video %s no longer exists; skipping", video_id)
        return
    if row["status"] == "READY":
        log.info("video %s already READY (duplicate event); skipping", video_id)
        return

    db.set_status(video_id, "PROCESSING")
    prefix = f"videos/{video_id}/"
    try:
        with tempfile.TemporaryDirectory(prefix="mytube-") as tmp:
            src, out = Path(tmp) / "input", Path(tmp) / "hls"
            s3.download_file(bucket, key, str(src))
            transcode(src, out)
            _upload_dir(out, prefix)
    except Exception:
        db.set_status(video_id, "FAILED")
        raise

    if not db.set_status(video_id, "READY", f"{prefix}master.m3u8"):
        log.info("video %s was deleted during processing; removing output", video_id)
        _delete_prefix(prefix)
    log.info("video %s READY", video_id)


def handle_message(message: dict) -> None:
    done = threading.Event()
    beat = threading.Thread(target=_heartbeat, args=(message["ReceiptHandle"], done), daemon=True)
    beat.start()
    _protect(True)
    try:
        for bucket, key in object_keys(message["Body"]):
            process_object(bucket, key)
        sqs.delete_message(QueueUrl=QUEUE_URL, ReceiptHandle=message["ReceiptHandle"])
    except InvalidVideoError as exc:
        log.warning("invalid video (message %s): %s", message["MessageId"], exc)
    except Exception:
        log.exception("failed to process message %s; it will be retried", message["MessageId"])
    finally:
        done.set()
        _protect(False)


def run() -> None:
    global INSTANCE_ID
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    INSTANCE_ID = _instance_id()
    # docker stop sends SIGTERM: stop taking new messages. An interrupted job's message
    # simply becomes visible again and is retried elsewhere.
    signal.signal(signal.SIGTERM, lambda *_: _stopping.set())
    log.info("polling %s (instance %s)", QUEUE_URL, INSTANCE_ID)
    while not _stopping.is_set():
        resp = sqs.receive_message(QueueUrl=QUEUE_URL, MaxNumberOfMessages=1, WaitTimeSeconds=20)
        for message in resp.get("Messages", []):
            handle_message(message)


if __name__ == "__main__":
    run()

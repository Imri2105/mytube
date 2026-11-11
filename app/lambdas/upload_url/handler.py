"""POST /api/upload: create a video row and return a presigned PUT URL for the raw file.

Invoked by API Gateway (REST, Lambda proxy) behind a Cognito authorizer, so the caller's
claims are already verified when we get here.
"""

import json
import os
import uuid

import boto3
import psycopg
from botocore.config import Config

# A single presigned PUT is limited to 5 GB by S3. Larger files need multipart (stretch goal).
MAX_UPLOAD_BYTES = 5 * 1024**3
URL_TTL_SECONDS = 3600
ALLOWED_CONTENT_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/webm",
    "video/x-matroska",
    "video/x-msvideo",
    "video/mpeg",
}
MAX_TITLE_LEN = 200

s3 = boto3.client(
    "s3",
    region_name=os.environ.get("AWS_REGION"),
    config=Config(signature_version="s3v4", s3={"addressing_style": "virtual"}),
)
_conn: psycopg.Connection | None = None
_creds: dict | None = None


def _load_creds(refresh: bool = False) -> dict:
    global _creds
    if _creds is None or refresh:
        sm = boto3.client("secretsmanager")
        _creds = json.loads(sm.get_secret_value(SecretId=os.environ["DB_SECRET_ARN"])["SecretString"])
    return _creds


def _connect(refresh_creds: bool = False) -> psycopg.Connection:
    creds = _load_creds(refresh_creds)
    return psycopg.connect(
        host=os.environ["DB_HOST"],
        port=int(os.environ.get("DB_PORT", "5432")),
        dbname=os.environ.get("DB_NAME", "mytube"),
        user=creds["username"],
        password=creds["password"],
        sslmode="verify-full",
        sslrootcert=os.path.join(os.path.dirname(__file__), "rds-global-bundle.pem"),
        connect_timeout=5,
        autocommit=True,
    )


def insert_video(video_id: uuid.UUID, owner_sub: str, title: str, raw_key: str) -> None:
    """Insert the UPLOADING row, reusing the connection across warm invocations."""
    global _conn
    sql = "INSERT INTO videos (id, owner_sub, title, status, raw_key) VALUES (%s, %s, %s, 'UPLOADING', %s)"
    for attempt in range(2):
        try:
            if _conn is None or _conn.closed:
                # Second attempt re-reads the secret in case RDS rotated the password.
                _conn = _connect(refresh_creds=attempt > 0)
            _conn.execute(sql, (video_id, owner_sub, title, raw_key))
            return
        except psycopg.OperationalError:
            _conn = None
            if attempt:
                raise


def _response(status: int, body: dict) -> dict:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json", "Cache-Control": "no-store"},
        "body": json.dumps(body),
    }


def parse_request(raw_body: str | None) -> dict:
    """Validate the request body. Raises ValueError with a user-facing message."""
    try:
        body = json.loads(raw_body or "{}")
    except json.JSONDecodeError as exc:
        raise ValueError("body must be JSON") from exc
    if not isinstance(body, dict):
        raise ValueError("body must be a JSON object")

    content_type = body.get("contentType")
    if content_type not in ALLOWED_CONTENT_TYPES:
        raise ValueError(f"contentType must be one of {sorted(ALLOWED_CONTENT_TYPES)}")

    size = body.get("size")
    if not isinstance(size, int) or isinstance(size, bool) or not 0 < size <= MAX_UPLOAD_BYTES:
        raise ValueError(f"size must be an integer between 1 and {MAX_UPLOAD_BYTES} bytes")

    filename = body.get("filename")
    if not isinstance(filename, str) or not filename.strip():
        raise ValueError("filename is required")

    title = body.get("title") or filename.rsplit(".", 1)[0]
    if not isinstance(title, str):
        raise ValueError("title must be a string")
    title = title.strip()[:MAX_TITLE_LEN] or "Untitled"

    return {"content_type": content_type, "size": size, "title": title}


def handler(event: dict, _context: object) -> dict:
    owner_sub = event["requestContext"]["authorizer"]["claims"]["sub"]
    try:
        req = parse_request(event.get("body"))
    except ValueError as exc:
        return _response(400, {"message": str(exc)})

    video_id = uuid.uuid4()
    raw_key = f"raw/{owner_sub}/{video_id}"
    insert_video(video_id, owner_sub, req["title"], raw_key)

    # Content-Type and Content-Length are signed: S3 rejects a PUT that doesn't match them.
    upload_url = s3.generate_presigned_url(
        "put_object",
        Params={
            "Bucket": os.environ["RAW_BUCKET"],
            "Key": raw_key,
            "ContentType": req["content_type"],
            "ContentLength": req["size"],
        },
        ExpiresIn=URL_TTL_SECONDS,
    )
    return _response(201, {"videoId": str(video_id), "uploadUrl": upload_url})

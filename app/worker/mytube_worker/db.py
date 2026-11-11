"""PostgreSQL access (same approach as the backend: RDS-managed secret, TLS verify-full)."""

import json
import os

import boto3
import psycopg
from psycopg.rows import dict_row

_creds: dict | None = None


def _load_creds(refresh: bool = False) -> dict:
    global _creds
    if _creds is None or refresh:
        sm = boto3.client("secretsmanager")
        _creds = json.loads(sm.get_secret_value(SecretId=os.environ["DB_SECRET_ARN"])["SecretString"])
    return _creds


def connect() -> psycopg.Connection:
    """Open a connection; on failure re-read the secret once (RDS rotates it every 7 days)."""
    for attempt in range(2):
        creds = _load_creds(refresh=attempt > 0)
        try:
            return psycopg.connect(
                host=os.environ["DB_HOST"],
                port=int(os.environ.get("DB_PORT", "5432")),
                dbname=os.environ.get("DB_NAME", "mytube"),
                user=creds["username"],
                password=creds["password"],
                sslmode=os.environ.get("DB_SSLMODE", "verify-full"),
                sslrootcert=os.environ.get("DB_SSLROOTCERT", "/etc/ssl/rds-global-bundle.pem"),
                connect_timeout=5,
                row_factory=dict_row,
            )
        except psycopg.OperationalError:
            if attempt:
                raise
    raise AssertionError("unreachable")


def get_video(video_id: str, raw_key: str) -> dict | None:
    with connect() as conn:
        sql = "SELECT id, status FROM videos WHERE id = %s AND raw_key = %s"
        return conn.execute(sql, (video_id, raw_key)).fetchone()


def set_status(video_id: str, status: str, hls_path: str | None = None) -> bool:
    """Update the row; returns False if it no longer exists (the owner deleted it)."""
    with connect() as conn:
        cur = conn.execute(
            "UPDATE videos SET status = %s, hls_path = %s WHERE id = %s",
            (status, hls_path, video_id),
        )
        return cur.rowcount == 1

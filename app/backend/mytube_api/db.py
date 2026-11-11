"""PostgreSQL access. Credentials come from the RDS-managed Secrets Manager secret."""

import json
import os

import boto3
import psycopg
from psycopg.rows import dict_row

SCHEMA = """
CREATE TABLE IF NOT EXISTS videos (
    id         uuid PRIMARY KEY,
    owner_sub  text NOT NULL,
    title      text NOT NULL,
    status     text NOT NULL CHECK (status IN ('UPLOADING', 'PROCESSING', 'READY', 'FAILED')),
    raw_key    text NOT NULL,
    hls_path   text,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS videos_status_created_idx ON videos (status, created_at DESC);
CREATE INDEX IF NOT EXISTS videos_owner_created_idx ON videos (owner_sub, created_at DESC);
"""

# Arbitrary constant so concurrent instances don't race on CREATE TABLE.
SCHEMA_LOCK_ID = 7_202_611

_creds: dict | None = None


def _load_creds(refresh: bool = False) -> dict:
    global _creds
    if _creds is None or refresh:
        sm = boto3.client("secretsmanager")
        secret = sm.get_secret_value(SecretId=os.environ["DB_SECRET_ARN"])
        _creds = json.loads(secret["SecretString"])
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


def create_schema() -> None:
    with connect() as conn:
        conn.execute("SELECT pg_advisory_xact_lock(%s)", (SCHEMA_LOCK_ID,))
        conn.execute(SCHEMA)


def fetch_all(sql: str, params: tuple = ()) -> list[dict]:
    with connect() as conn:
        return conn.execute(sql, params).fetchall()


def fetch_one(sql: str, params: tuple = ()) -> dict | None:
    with connect() as conn:
        return conn.execute(sql, params).fetchone()


def execute(sql: str, params: tuple = ()) -> None:
    with connect() as conn:
        conn.execute(sql, params)

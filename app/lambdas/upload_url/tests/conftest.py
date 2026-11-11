import os

# Set before the handler module is imported (it creates its S3 client at import time).
os.environ.setdefault("AWS_REGION", "il-central-1")
os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("RAW_BUCKET", "test-raw")

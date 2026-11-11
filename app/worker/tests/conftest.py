import os

# boto3 clients are created at import time; they only need a region (no calls are made).
os.environ.setdefault("AWS_REGION", "il-central-1")
os.environ.setdefault("AWS_DEFAULT_REGION", "il-central-1")

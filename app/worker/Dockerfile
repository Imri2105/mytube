# syntax=docker/dockerfile:1
FROM python:3.12-slim

RUN apt-get update \
 && apt-get install -y --no-install-recommends ffmpeg \
 && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# RDS CA bundle so the DB connection can use sslmode=verify-full.
ADD --chmod=644 https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem /etc/ssl/rds-global-bundle.pem

COPY mytube_worker ./mytube_worker

RUN useradd --uid 10001 --no-create-home --shell /usr/sbin/nologin app
USER app

CMD ["python", "-m", "mytube_worker.main"]

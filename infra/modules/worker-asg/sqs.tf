# raw-uploads ObjectCreated -> jobs queue -> workers. 3 failed receives -> DLQ (+ alarm).

resource "aws_sqs_queue" "dlq" {
  name                      = "${var.name}-dlq"
  message_retention_seconds = 1209600 # 14 days, time to investigate
  sqs_managed_sse_enabled   = true
}

resource "aws_sqs_queue" "jobs" {
  name                       = "${var.name}-jobs"
  visibility_timeout_seconds = var.visibility_timeout_seconds
  receive_wait_time_seconds  = 20
  message_retention_seconds  = 345600 # 4 days
  sqs_managed_sse_enabled    = true

  redrive_policy = jsonencode({
    deadLetterTargetArn = aws_sqs_queue.dlq.arn
    maxReceiveCount     = 3
  })
}

resource "aws_sqs_queue_redrive_allow_policy" "dlq" {
  queue_url = aws_sqs_queue.dlq.id
  redrive_allow_policy = jsonencode({
    redrivePermission = "byQueue"
    sourceQueueArns   = [aws_sqs_queue.jobs.arn]
  })
}

data "aws_caller_identity" "current" {}

data "aws_iam_policy_document" "jobs_queue" {
  statement {
    sid       = "AllowRawBucketEvents"
    actions   = ["sqs:SendMessage"]
    resources = [aws_sqs_queue.jobs.arn]
    principals {
      type        = "Service"
      identifiers = ["s3.amazonaws.com"]
    }
    condition {
      test     = "ArnEquals"
      variable = "aws:SourceArn"
      values   = ["arn:aws:s3:::${var.raw_bucket}"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_sqs_queue_policy" "jobs" {
  queue_url = aws_sqs_queue.jobs.id
  policy    = data.aws_iam_policy_document.jobs_queue.json
}

resource "aws_s3_bucket_notification" "raw" {
  bucket = var.raw_bucket

  queue {
    queue_arn     = aws_sqs_queue.jobs.arn
    events        = ["s3:ObjectCreated:*"]
    filter_prefix = "raw/"
  }

  depends_on = [aws_sqs_queue_policy.jobs]
}

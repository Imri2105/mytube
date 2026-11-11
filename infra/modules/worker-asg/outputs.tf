output "queue_url" {
  value = aws_sqs_queue.jobs.url
}

output "dlq_url" {
  value = aws_sqs_queue.dlq.url
}

output "asg_name" {
  value = aws_autoscaling_group.this.name
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.this.name
}

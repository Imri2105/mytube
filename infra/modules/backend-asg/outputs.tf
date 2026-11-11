output "alb_arn" {
  description = "For the CloudFront VPC origin."
  value       = aws_lb.this.arn
}

output "alb_dns_name" {
  value = aws_lb.this.dns_name
}

output "asg_name" {
  value = aws_autoscaling_group.this.name
}

output "log_group_name" {
  value = aws_cloudwatch_log_group.this.name
}

output "bucket_names" {
  description = "Bucket names by role: raw, processed, frontend."
  value       = { for k, b in aws_s3_bucket.this : k => b.bucket }
}

output "bucket_arns" {
  value = { for k, b in aws_s3_bucket.this : k => b.arn }
}

output "bucket_regional_domain_names" {
  description = "For CloudFront S3 origins."
  value       = { for k, b in aws_s3_bucket.this : k => b.bucket_regional_domain_name }
}

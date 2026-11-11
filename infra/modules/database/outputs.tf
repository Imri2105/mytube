output "address" {
  value = aws_db_instance.this.address
}

output "port" {
  value = aws_db_instance.this.port
}

output "db_name" {
  value = aws_db_instance.this.db_name
}

output "master_secret_arn" {
  description = "ARN (not the value) of the RDS-managed master credentials secret."
  value       = aws_db_instance.this.master_user_secret[0].secret_arn
}

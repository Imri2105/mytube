output "vpc_id" {
  value = aws_vpc.this.id
}

output "public_subnet_ids" {
  value = aws_subnet.public[*].id
}

output "app_subnet_ids" {
  value = aws_subnet.app[*].id
}

output "db_subnet_ids" {
  value = aws_subnet.db[*].id
}

output "security_group_ids" {
  description = "Security group IDs by component."
  value = {
    alb     = aws_security_group.alb.id
    backend = aws_security_group.backend.id
    worker  = aws_security_group.worker.id
    lambda  = aws_security_group.lambda.id
    db      = aws_security_group.db.id
  }
}

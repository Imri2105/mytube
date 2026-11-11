# All component security groups live here so cross-references (db <- backend/worker/lambda)
# stay in one place. Rules use the standalone rule resources, one rule per resource.

data "aws_ec2_managed_prefix_list" "cloudfront" {
  name = "com.amazonaws.global.cloudfront.origin-facing"
}

resource "aws_security_group" "alb" {
  name        = "${var.name}-alb"
  description = "Internal ALB, reachable only from CloudFront (VPC origin)"
  vpc_id      = aws_vpc.this.id
  tags        = { Name = "${var.name}-alb" }
}

resource "aws_security_group" "backend" {
  name        = "${var.name}-backend"
  description = "Backend API instances"
  vpc_id      = aws_vpc.this.id
  tags        = { Name = "${var.name}-backend" }
}

resource "aws_security_group" "worker" {
  name        = "${var.name}-worker"
  description = "Transcode workers, no inbound"
  vpc_id      = aws_vpc.this.id
  tags        = { Name = "${var.name}-worker" }
}

resource "aws_security_group" "lambda" {
  name        = "${var.name}-upload-lambda"
  description = "Upload-URL Lambda ENIs, no inbound"
  vpc_id      = aws_vpc.this.id
  tags        = { Name = "${var.name}-upload-lambda" }
}

resource "aws_security_group" "db" {
  name        = "${var.name}-db"
  description = "PostgreSQL, from app tiers only"
  vpc_id      = aws_vpc.this.id
  tags        = { Name = "${var.name}-db" }
}

# --- ALB --------------------------------------------------------------------

resource "aws_vpc_security_group_ingress_rule" "alb_from_cloudfront" {
  security_group_id = aws_security_group.alb.id
  description       = "CloudFront origin-facing"
  prefix_list_id    = data.aws_ec2_managed_prefix_list.cloudfront.id
  ip_protocol       = "tcp"
  from_port         = var.alb_port
  to_port           = var.alb_port
}

resource "aws_vpc_security_group_egress_rule" "alb_to_backend" {
  security_group_id            = aws_security_group.alb.id
  description                  = "To backend app port"
  referenced_security_group_id = aws_security_group.backend.id
  ip_protocol                  = "tcp"
  from_port                    = var.app_port
  to_port                      = var.app_port
}

# --- Backend ----------------------------------------------------------------

resource "aws_vpc_security_group_ingress_rule" "backend_from_alb" {
  security_group_id            = aws_security_group.backend.id
  description                  = "From ALB"
  referenced_security_group_id = aws_security_group.alb.id
  ip_protocol                  = "tcp"
  from_port                    = var.app_port
  to_port                      = var.app_port
}

# --- Shared egress for backend, worker, lambda: HTTPS out (AWS APIs, ECR, dnf) + Postgres ---

locals {
  app_sgs = {
    backend = aws_security_group.backend.id
    worker  = aws_security_group.worker.id
    lambda  = aws_security_group.lambda.id
  }
}

resource "aws_vpc_security_group_egress_rule" "app_https" {
  for_each          = local.app_sgs
  security_group_id = each.value
  description       = "HTTPS to AWS APIs / package repos"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = 443
  to_port           = 443
}

resource "aws_vpc_security_group_egress_rule" "app_to_db" {
  for_each                     = local.app_sgs
  security_group_id            = each.value
  description                  = "PostgreSQL"
  referenced_security_group_id = aws_security_group.db.id
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

resource "aws_vpc_security_group_ingress_rule" "db_from_app" {
  for_each                     = local.app_sgs
  security_group_id            = aws_security_group.db.id
  description                  = "PostgreSQL from ${each.key}"
  referenced_security_group_id = each.value
  ip_protocol                  = "tcp"
  from_port                    = 5432
  to_port                      = 5432
}

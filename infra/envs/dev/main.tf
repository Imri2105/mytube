locals {
  name = "${var.project}-${var.env}"

  # Public site URLs. Phase 5 (edge) adds the CloudFront / custom domain URL here.
  site_urls = []
}

module "network" {
  source     = "../../modules/network"
  name       = local.name
  az_count   = var.az_count
  nat_per_az = var.nat_per_az
}

module "storage" {
  source                 = "../../modules/storage"
  name                   = local.name
  force_destroy          = true
  upload_allowed_origins = [for u in local.site_urls : trimsuffix(u, "/")]
}

module "auth" {
  source        = "../../modules/auth"
  name          = local.name
  callback_urls = concat(local.site_urls, var.local_dev_urls)
  logout_urls   = concat(local.site_urls, var.local_dev_urls)
}

module "database" {
  source            = "../../modules/database"
  name              = local.name
  subnet_ids        = module.network.db_subnet_ids
  security_group_id = module.network.security_group_ids["db"]
  multi_az          = var.db_multi_az
}

# Shared secret between CloudFront (custom origin header) and the ALB listener rule.
# Lives in state only; never output.
resource "random_password" "origin_verify" {
  length  = 40
  special = false
}

module "backend" {
  source                     = "../../modules/backend-asg"
  name                       = "${local.name}-backend"
  vpc_id                     = module.network.vpc_id
  subnet_ids                 = module.network.app_subnet_ids
  alb_security_group_id      = module.network.security_group_ids["alb"]
  instance_security_group_id = module.network.security_group_ids["backend"]
  origin_verify_secret       = random_password.origin_verify.result
  ecr_repository_url         = aws_ecr_repository.app["backend"].repository_url
  ecr_repository_arn         = aws_ecr_repository.app["backend"].arn
  db_secret_arn              = module.database.master_secret_arn
  raw_bucket                 = module.storage.bucket_names["raw"]
  processed_bucket           = module.storage.bucket_names["processed"]

  container_env = {
    DB_HOST           = module.database.address
    DB_PORT           = tostring(module.database.port)
    DB_NAME           = module.database.db_name
    DB_SECRET_ARN     = module.database.master_secret_arn
    COGNITO_ISSUER    = module.auth.issuer
    COGNITO_CLIENT_ID = module.auth.client_id
    RAW_BUCKET        = module.storage.bucket_names["raw"]
    PROCESSED_BUCKET  = module.storage.bucket_names["processed"]
  }
}

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

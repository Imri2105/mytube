locals {
  tags = {
    Project   = var.project
    Env       = var.env
    ManagedBy = "terraform"
  }
}

provider "aws" {
  region = var.region
  default_tags {
    tags = local.tags
  }
}


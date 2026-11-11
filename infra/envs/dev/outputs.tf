output "vpc_id" {
  value = module.network.vpc_id
}

output "bucket_names" {
  value = module.storage.bucket_names
}

output "cognito_user_pool_id" {
  value = module.auth.user_pool_id
}

output "cognito_client_id" {
  value = module.auth.client_id
}

output "cognito_hosted_ui_base_url" {
  value = module.auth.hosted_ui_base_url
}

output "db_address" {
  value = module.database.address
}

output "db_secret_arn" {
  description = "ARN only; the secret value is never exposed by Terraform."
  value       = module.database.master_secret_arn
}

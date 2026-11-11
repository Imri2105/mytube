output "api_domain_name" {
  description = "Execute-API hostname, for the CloudFront origin."
  value       = "${aws_api_gateway_rest_api.this.id}.execute-api.${data.aws_region.current.name}.amazonaws.com"
}

output "stage_name" {
  description = "Stage name; CloudFront origin path is /<stage>."
  value       = aws_api_gateway_stage.this.stage_name
}

output "invoke_url" {
  value = aws_api_gateway_stage.this.invoke_url
}

output "lambda_function_name" {
  value = aws_lambda_function.upload_url.function_name
}

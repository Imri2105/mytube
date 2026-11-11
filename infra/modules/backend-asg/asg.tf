data "aws_region" "current" {}

data "aws_default_tags" "current" {}

# Latest Amazon Linux 2023 AMI. A new AMI release changes the launch template, which
# triggers an instance refresh on the next apply (that is how instances get patched).
data "aws_ssm_parameter" "al2023" {
  name = "/aws/service/ami-amazon-linux-latest/al2023-ami-kernel-default-x86_64"
}

resource "aws_cloudwatch_log_group" "this" {
  name              = "/${var.name}"
  retention_in_days = var.log_retention_days
}

resource "aws_launch_template" "this" {
  name                   = var.name
  image_id               = data.aws_ssm_parameter.al2023.value
  instance_type          = var.instance_type
  vpc_security_group_ids = [var.instance_security_group_id]
  update_default_version = true

  iam_instance_profile {
    arn = aws_iam_instance_profile.this.arn
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
    # 2 hops so the container (one hop behind docker's bridge) can still reach IMDS for role credentials.
    http_put_response_hop_limit = 2
  }

  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = 20
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
    }
  }

  # Only names, ARNs and endpoints here. The DB password is read from Secrets Manager at runtime.
  user_data = base64encode(templatefile("${path.module}/user_data.sh.tftpl", {
    region    = data.aws_region.current.name
    image     = "${var.ecr_repository_url}:${var.image_tag}"
    log_group = aws_cloudwatch_log_group.this.name
    app_port  = var.app_port
    env       = var.container_env
  }))

  tag_specifications {
    resource_type = "instance"
    tags          = merge(data.aws_default_tags.current.tags, { Name = var.name })
  }

  tag_specifications {
    resource_type = "volume"
    tags          = merge(data.aws_default_tags.current.tags, { Name = var.name })
  }
}

resource "aws_autoscaling_group" "this" {
  name                      = var.name
  min_size                  = var.min_size
  max_size                  = var.max_size
  vpc_zone_identifier       = var.subnet_ids
  target_group_arns         = [aws_lb_target_group.this.arn]
  health_check_type         = "ELB"
  health_check_grace_period = 180

  launch_template {
    id      = aws_launch_template.this.id
    version = aws_launch_template.this.latest_version
  }

  # Rolls instances whenever the launch template changes.
  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage = 50
    }
  }

  tag {
    key                 = "Name"
    value               = var.name
    propagate_at_launch = false
  }
}

resource "aws_autoscaling_policy" "requests_per_target" {
  name                   = "${var.name}-requests-per-target"
  autoscaling_group_name = aws_autoscaling_group.this.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    target_value = var.target_requests_per_instance
    predefined_metric_specification {
      predefined_metric_type = "ALBRequestCountPerTarget"
      resource_label         = "${aws_lb.this.arn_suffix}/${aws_lb_target_group.this.arn_suffix}"
    }
  }
}

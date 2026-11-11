data "aws_region" "current" {}

data "aws_default_tags" "current" {}

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
    # 2 hops so the container can reach IMDS (role credentials, own instance ID).
    http_put_response_hop_limit = 2
  }

  # Room for one raw upload (up to 5 GB) plus its HLS output, inside docker's storage.
  block_device_mappings {
    device_name = "/dev/xvda"
    ebs {
      volume_size           = var.volume_size_gb
      volume_type           = "gp3"
      encrypted             = true
      delete_on_termination = true
    }
  }

  user_data = base64encode(templatefile("${path.module}/user_data.sh.tftpl", {
    region    = data.aws_region.current.name
    image     = "${var.ecr_repository_url}:${var.image_tag}"
    log_group = aws_cloudwatch_log_group.this.name
    env = merge(var.container_env, {
      QUEUE_URL = aws_sqs_queue.jobs.url
      ASG_NAME  = var.name
    })
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
  health_check_type         = "EC2"
  health_check_grace_period = 120

  # GroupInServiceInstances feeds the backlog-per-instance scaling metric below.
  enabled_metrics = ["GroupInServiceInstances"]

  launch_template {
    id      = aws_launch_template.this.id
    version = aws_launch_template.this.latest_version
  }

  # Launch the replacement first; wait for busy (scale-in protected) workers to finish.
  instance_refresh {
    strategy = "Rolling"
    preferences {
      min_healthy_percentage       = 100
      max_healthy_percentage       = 200
      scale_in_protected_instances = "Wait"
    }
  }

  tag {
    key                 = "Name"
    value               = var.name
    propagate_at_launch = false
  }
}

# Target tracking on backlog per instance = visible messages / in-service workers.
resource "aws_autoscaling_policy" "backlog_per_instance" {
  name                   = "${var.name}-backlog-per-instance"
  autoscaling_group_name = aws_autoscaling_group.this.name
  policy_type            = "TargetTrackingScaling"

  target_tracking_configuration {
    target_value = var.target_backlog_per_instance

    customized_metric_specification {
      metrics {
        id          = "visible"
        return_data = false
        metric_stat {
          stat = "Sum"
          metric {
            namespace   = "AWS/SQS"
            metric_name = "ApproximateNumberOfMessagesVisible"
            dimensions {
              name  = "QueueName"
              value = aws_sqs_queue.jobs.name
            }
          }
        }
      }

      metrics {
        id          = "workers"
        return_data = false
        metric_stat {
          stat = "Average"
          metric {
            namespace   = "AWS/AutoScaling"
            metric_name = "GroupInServiceInstances"
            dimensions {
              name  = "AutoScalingGroupName"
              value = aws_autoscaling_group.this.name
            }
          }
        }
      }

      metrics {
        id          = "backlog_per_instance"
        label       = "Visible messages per in-service worker"
        expression  = "visible / workers"
        return_data = true
      }
    }
  }
}

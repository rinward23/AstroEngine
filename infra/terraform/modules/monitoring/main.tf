locals {
  is_aws   = lower(var.cloud) == "aws"
  is_gcp   = lower(var.cloud) == "gcp"
  is_azure = lower(var.cloud) == "azure"
  tags = merge(var.tags, {
    "astroengine:environment" = var.environment
    "astroengine:module"      = "monitoring"
  })
}

resource "aws_prometheus_workspace" "this" {
  count = local.is_aws ? 1 : 0
  alias = "astroengine-${var.environment}"
  tags  = local.tags
}

resource "aws_cloudwatch_metric_alarm" "latency_budget" {
  count               = local.is_aws ? 1 : 0
  alarm_name          = "astroengine-${var.environment}-latency-budget"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 3
  metric_name         = "LatencyP95"
  namespace           = "AstroEngine/API"
  period              = 60
  statistic           = "Average"
  threshold           = 0.6
  alarm_actions       = values(var.alert_endpoints)
}

resource "google_monitoring_alert_policy" "error_budget" {
  count       = local.is_gcp ? 1 : 0
  display_name = "AstroEngine Error Budget ${var.environment}"
  combiner     = "OR"
  conditions {
    display_name = "High error rate"
    condition_threshold {
      filter = "metric.type=\"custom.googleapis.com/astroengine/error_rate\""
      comparison = "COMPARISON_GT"
      duration   = "300s"
      threshold_value = 0.005
    }
  }
  notification_channels = values(var.alert_endpoints)
}

resource "azurerm_monitor_action_group" "this" {
  count               = local.is_azure ? 1 : 0
  name                = "ag-astroengine-${var.environment}"
  resource_group_name = var.tags["resource_group"]
  short_name          = "ae${substr(var.environment,0,4)}"
  webhook_receiver {
    name        = "primary"
    service_uri = lookup(var.alert_endpoints, "primary", "")
  }
  tags = local.tags
}

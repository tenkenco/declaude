# Uptime check + alerting on the public gateway.

resource "google_monitoring_uptime_check_config" "gateway" {
  display_name = "declaude-gateway-health"
  timeout      = "10s"
  period       = "300s"

  http_check {
    path         = "/health"
    port         = 443
    use_ssl      = true
    validate_ssl = true
  }

  monitored_resource {
    type = "uptime_url"
    labels = {
      project_id = var.project_id
      host       = replace(google_cloud_run_v2_service.gateway.uri, "https://", "")
    }
  }
}

resource "google_monitoring_notification_channel" "email" {
  display_name = "declaude ops email"
  type         = "email"
  labels = {
    email_address = "rryoung98@tenken.co"
  }
}

resource "google_monitoring_alert_policy" "gateway_down" {
  display_name = "declaude gateway down"
  combiner     = "OR"

  conditions {
    display_name = "uptime check failing"
    condition_threshold {
      filter          = "metric.type=\"monitoring.googleapis.com/uptime_check/check_passed\" AND resource.type=\"uptime_url\" AND metric.label.check_id=\"${google_monitoring_uptime_check_config.gateway.uptime_check_id}\""
      comparison      = "COMPARISON_GT"
      threshold_value = 1
      duration        = "600s"
      aggregations {
        alignment_period     = "300s"
        per_series_aligner   = "ALIGN_NEXT_OLDER"
        cross_series_reducer = "REDUCE_COUNT_FALSE"
        group_by_fields      = ["resource.label.host"]
      }
      trigger {
        count = 1
      }
    }
  }

  notification_channels = [google_monitoring_notification_channel.email.id]
}

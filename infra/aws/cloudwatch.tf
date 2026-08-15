resource "aws_cloudwatch_log_group" "demo_logs" {
  name              = "/${var.project_name}/demo-instance"
  retention_in_days = 14 # free tier friendly, adjust in cost_breakdown.md if you change this
}

resource "aws_cloudwatch_log_group" "detector_lambda" {
  name              = "/aws/lambda/${var.project_name}-detector"
  retention_in_days = 14
}

# Metric filter counting failed-login lines so there's a native CloudWatch
# metric to alarm on, independent of the Lambda's own SNS publish. Belt
# and suspenders: this is what data.cost_breakdown.md counts as "the
# CloudWatch Alarms" requirement, the Lambda's rule engine is the more
# precise detector, this filter is a cheap backstop.
resource "aws_cloudwatch_log_metric_filter" "failed_logins" {
  name           = "${var.project_name}-failed-logins"
  log_group_name = aws_cloudwatch_log_group.demo_logs.name
  pattern        = "\"Failed password\""

  metric_transformation {
    name      = "FailedLoginCount"
    namespace = var.project_name
    value     = "1"
    unit      = "Count"
  }
}

resource "aws_cloudwatch_metric_alarm" "failed_login_spike" {
  alarm_name          = "${var.project_name}-failed-login-spike"
  comparison_operator = "GreaterThanOrEqualToThreshold"
  evaluation_periods   = 1
  metric_name         = aws_cloudwatch_log_metric_filter.failed_logins.metric_transformation[0].name
  namespace           = aws_cloudwatch_log_metric_filter.failed_logins.metric_transformation[0].namespace
  period              = 300
  statistic           = "Sum"
  threshold           = var.brute_force_threshold
  alarm_description   = "Backstop alarm mirroring the Lambda detector's brute-force rule"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"
}

resource "aws_cloudwatch_dashboard" "main" {
  dashboard_name = "${var.project_name}-dashboard"
  dashboard_body = templatefile("${path.module}/../../dashboards/cloudwatch_dashboard.json.tpl", {
    log_group_name    = aws_cloudwatch_log_group.demo_logs.name
    metric_namespace  = var.project_name
    aws_region        = var.aws_region
  })
}

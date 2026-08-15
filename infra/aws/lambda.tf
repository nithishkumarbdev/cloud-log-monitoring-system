data "archive_file" "detector" {
  type        = "zip"
  source_dir  = "${path.module}/../../detector"
  output_path = "${path.module}/.build/detector.zip"
  excludes    = ["tests", "__pycache__"]
}

resource "aws_lambda_function" "detector" {
  function_name = "${var.project_name}-detector"
  role          = aws_iam_role.detector_lambda.arn
  handler       = "handler.handler"
  runtime       = "python3.12"
  timeout       = 30
  memory_size   = 128

  filename         = data.archive_file.detector.output_path
  source_code_hash = data.archive_file.detector.output_base64sha256

  environment {
    variables = {
      LOG_GROUP_NAME       = aws_cloudwatch_log_group.demo_logs.name
      SNS_TOPIC_ARN        = aws_sns_topic.alerts.arn
      IP_ALLOWLIST         = var.ip_allowlist
      POLL_WINDOW_MINUTES  = tostring(var.poll_window_minutes)
    }
  }

  depends_on = [aws_cloudwatch_log_group.detector_lambda]
}

# Scheduled poll rather than a subscription filter, see architecture.md.
resource "aws_cloudwatch_event_rule" "detector_schedule" {
  name                = "${var.project_name}-detector-schedule"
  schedule_expression = "rate(${var.poll_window_minutes} minutes)"
}

resource "aws_cloudwatch_event_target" "detector_target" {
  rule = aws_cloudwatch_event_rule.detector_schedule.name
  arn  = aws_lambda_function.detector.arn
}

resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowEventBridgeInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.detector.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.detector_schedule.arn
}

# --- Optional Slack subscriber ---

data "archive_file" "slack_formatter" {
  count       = var.slack_webhook_url != "" ? 1 : 0
  type        = "zip"
  source_dir  = "${path.module}/../../alerting"
  output_path = "${path.module}/.build/slack_formatter.zip"
}

resource "aws_iam_role" "slack_formatter" {
  count = var.slack_webhook_url != "" ? 1 : 0
  name  = "${var.project_name}-slack-formatter-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "slack_formatter_logs" {
  count = var.slack_webhook_url != "" ? 1 : 0
  name  = "${var.project_name}-slack-formatter-logs"
  role  = aws_iam_role.slack_formatter[0].id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"]
      Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${var.project_name}-slack-formatter*"
    }]
  })
}

resource "aws_lambda_function" "slack_formatter" {
  count         = var.slack_webhook_url != "" ? 1 : 0
  function_name = "${var.project_name}-slack-formatter"
  role          = aws_iam_role.slack_formatter[0].arn
  handler       = "slack_formatter.handler"
  runtime       = "python3.12"
  timeout       = 10
  memory_size   = 128

  filename         = data.archive_file.slack_formatter[0].output_path
  source_code_hash = data.archive_file.slack_formatter[0].output_base64sha256

  environment {
    variables = {
      SLACK_WEBHOOK_URL = var.slack_webhook_url
    }
  }
}

resource "aws_lambda_permission" "allow_sns_slack" {
  count         = var.slack_webhook_url != "" ? 1 : 0
  statement_id  = "AllowSNSInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.slack_formatter[0].function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.alerts.arn
}

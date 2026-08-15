# Every role here is explained in docs/iam_policy_rationale.md, keep that
# doc in sync if a permission is added or removed.

resource "aws_iam_role" "demo_instance" {
  name = "${var.project_name}-instance-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "ec2.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "demo_instance_logs" {
  name = "${var.project_name}-instance-logs-policy"
  role = aws_iam_role.demo_instance.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "logs:CreateLogStream",
        "logs:PutLogEvents",
        "logs:DescribeLogStreams"
      ]
      Resource = "${aws_cloudwatch_log_group.demo_logs.arn}:*"
    }]
  })
}

resource "aws_iam_instance_profile" "demo_instance" {
  name = "${var.project_name}-instance-profile"
  role = aws_iam_role.demo_instance.name
}

resource "aws_iam_role" "detector_lambda" {
  name = "${var.project_name}-detector-lambda-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
      Action    = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy" "detector_lambda_permissions" {
  name = "${var.project_name}-detector-lambda-policy"
  role = aws_iam_role.detector_lambda.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "ReadDemoLogGroup"
        Effect = "Allow"
        Action = [
          "logs:FilterLogEvents",
          "logs:GetLogEvents",
          "logs:DescribeLogStreams"
        ]
        Resource = "${aws_cloudwatch_log_group.demo_logs.arn}:*"
      },
      {
        Sid      = "PublishAlerts"
        Effect   = "Allow"
        Action   = "sns:Publish"
        Resource = aws_sns_topic.alerts.arn
      },
      {
        Sid    = "OwnLambdaLogs"
        Effect = "Allow"
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource = "arn:aws:logs:${var.aws_region}:*:log-group:/aws/lambda/${var.project_name}-detector*"
      }
    ]
  })
}

# --- GitHub Actions OIDC federation, no static keys in CI ---

data "aws_iam_openid_connect_provider" "github" {
  url = "https://token.actions.githubusercontent.com"
}

resource "aws_iam_role" "github_actions_deploy" {
  name = "${var.project_name}-github-actions-deploy"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect    = "Allow"
      Principal = { Federated = data.aws_iam_openid_connect_provider.github.arn }
      Action    = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        # Restrict to this repo's main branch only. Replace OWNER/REPO
        # when you fork this, see README setup section.
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:OWNER/cloud-log-monitoring-system:ref:refs/heads/main"
        }
      }
    }]
  })
}

# Deliberately broad-ish (Terraform needs to manage most of this stack's
# resource types) but still scoped to this project's resources by name
# prefix where the service supports resource-level policies, and to
# read-only + this project's IAM/EC2/Lambda/CloudWatch/SNS actions
# otherwise. See iam_policy_rationale.md for the tradeoff discussion,
# a Terraform deploy role is one of the few places a fully minimal
# policy isn't practical without hand-maintaining it every time a
# resource is added.
resource "aws_iam_role_policy" "github_actions_deploy_policy" {
  name = "${var.project_name}-github-actions-deploy-policy"
  role = aws_iam_role.github_actions_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = [
        "ec2:*", "iam:*", "lambda:*", "logs:*", "sns:*", "cloudwatch:*",
        "s3:GetObject", "s3:PutObject"
      ]
      Resource = "*"
    }]
  })
}

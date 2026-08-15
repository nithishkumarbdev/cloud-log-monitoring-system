# IAM policy rationale

Every role in `infra/aws/iam.tf`, and why it has the permissions it has.

## `demo-instance` role (EC2)

Attached to the EC2 instance via an instance profile. Permissions:

- `logs:CreateLogStream`, `logs:PutLogEvents`, `logs:DescribeLogStreams`,
  scoped to `${demo_logs log group arn}:*`.

That's it. The instance never reads its own logs back, never touches SNS,
never touches another service. The CloudWatch agent only needs to write.

## `detector-lambda` role

Attached to the scheduled detector Lambda. Permissions:

- `logs:FilterLogEvents`, `logs:GetLogEvents`, `logs:DescribeLogStreams`,
  scoped to the demo log group, because the whole job is reading recent
  events out of it.
- `sns:Publish`, scoped to the one alerts topic ARN, because publishing
  alerts is the whole point of the function.
- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`
  scoped to its own `/aws/lambda/*-detector*` log group, which is just
  Lambda's own execution logging, not the application's log data.

No wildcard resource, no permissions on EC2, IAM, or anything outside
what this function actually touches.

## `slack-formatter` role (optional)

Only created if `slack_webhook_url` is set. Permissions:

- `logs:CreateLogGroup`, `logs:CreateLogStream`, `logs:PutLogEvents`
  scoped to its own log group.

Notably absent: any SNS or CloudWatch Logs read permission. SNS invokes
this function directly with the message payload already attached, the
function has no reason to call back into AWS for anything except its own
execution logs.

## `github-actions-deploy` role (OIDC)

This is the one role that isn't tightly scoped, and that's a deliberate,
documented tradeoff rather than an oversight. Terraform needs to create,
update, and destroy EC2 instances, IAM roles, Lambda functions, CloudWatch
resources, and SNS topics as the stack evolves. Hand-maintaining an
exact-match policy that's kept in sync with every resource Terraform might
touch, across every future addition to this project, isn't practical for
a demo repo one person maintains.

The mitigations actually in place instead:

- The trust policy's `StringLike` condition restricts which repo and
  branch can assume this role at all (`repo:OWNER/cloud-log-monitoring-
  system:ref:refs/heads/main`), so no other GitHub Actions workflow
  anywhere can use it, OIDC-federated or not.
- No static credentials exist for this role, it's assumed per-workflow-run
  via short-lived OIDC tokens, so there's no long-lived key to leak.
- `terraform apply` on `main` requires a GitHub Environment approval, see
  `deploy.yml`, so even a compromised PR can't reach `apply` without a
  human clicking approve.

If this were a real production system rather than a portfolio demo, the
next step would be splitting this into per-resource-type policies and
adding a permissions boundary, noted in `known_limitations.md`.

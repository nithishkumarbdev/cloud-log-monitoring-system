# Deployment

Everything in `detector/`, `log-generator/`, and `alerting/` runs and is
tested with zero cloud access, see `bootstrap.sh`. This file covers the
part that does need real AWS and GCP accounts: actually standing up the
infrastructure.

## Prerequisites

- An AWS account with permissions to create IAM roles, EC2 instances,
  Lambda functions, CloudWatch and SNS resources.
- [Terraform](https://developer.hashicorp.com/terraform/install) >= 1.7.
- AWS CLI configured locally (`aws configure`) for the manual/local deploy
  path below. Not needed for the GitHub Actions path, that uses OIDC.
- A GCP project with billing enabled (Cloud Functions and Cloud Logging
  are free-tier eligible but the project itself needs billing on) and the
  `gcloud` CLI, if you're doing the GCP piece too.

## Option A: deploy locally from your machine

### AWS

```bash
cd infra/aws
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars: set alert_email and ssh_ingress_cidr at minimum
# find your IP with: curl -s ifconfig.me

terraform init
terraform plan    # review what it's about to create
terraform apply   # type yes to confirm
```

Terraform will print outputs including `dashboard_url` and
`instance_public_ip`. Check your email and confirm the SNS subscription,
alerts won't arrive until you do.

### GCP

```bash
cd infra/gcp
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars: set gcp_project_id

gcloud auth application-default login
terraform init
terraform plan
terraform apply
```

Terraform prints `ingest_function_url`. Test it:

```bash
curl -X POST "$(terraform output -raw ingest_function_url)" \
  -H "Content-Type: application/json" \
  -d '{"event_type": "login_failure", "source_ip": "203.0.113.5"}'
```

Then check Cloud Logging in the GCP console for the entry.

## Option B: deploy via GitHub Actions (recommended for the actual demo)

This is the path that backs the "GitHub Actions CI/CD" part of the
project, and the one to use if you want `git push` to be the whole deploy
step.

1. **Create the GitHub OIDC provider and deploy role**, once, from your
   machine (Terraform can't create the role that Terraform-via-GitHub-
   Actions will assume without a chicken-and-egg problem, so this one
   step is manual):

   ```bash
   cd infra/aws
   terraform apply -target=aws_iam_role.github_actions_deploy \
                    -target=data.aws_iam_openid_connect_provider.github
   ```

   If your AWS account has never used GitHub OIDC before, you'll need
   the OIDC provider itself first:

   ```bash
   aws iam create-open-id-connect-provider \
     --url https://token.actions.githubusercontent.com \
     --client-id-list sts.amazonaws.com \
     --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
   ```

2. **Edit `infra/aws/iam.tf`**: replace `OWNER/cloud-log-monitoring-system`
   in the trust policy's `StringLike` condition with your actual GitHub
   `owner/repo`.

3. **In your fork's repo settings**, add:
   - Settings > Secrets and variables > Actions:
     - `AWS_DEPLOY_ROLE_ARN`: the `github_actions_role_arn` Terraform
       output from step 1.
     - `ALERT_EMAIL`: your email.
     - `SSH_INGRESS_CIDR`: your IP in `/32` form.
   - Settings > Environments: create an environment named `production`
     and add yourself (or a teammate) as a required reviewer. This is
     the actual approval gate for `terraform apply`, not anything in
     the workflow YAML.

4. **Push to `main`.** The `CI` workflow runs lint/validate/tfsec/tests
   on every PR and posts the plan as a comment. Merging to `main` triggers
   `Deploy`, which pauses for the environment approval before running
   `terraform apply`.

## Verifying it's actually working

```bash
# watch for synthetic events landing in CloudWatch Logs
aws logs tail /cloud-log-monitor/demo-instance --follow

# manually invoke the detector instead of waiting for the schedule
aws lambda invoke --function-name cloud-log-monitor-detector /tmp/out.json
cat /tmp/out.json
```

You should see an alert email (and Slack message, if configured) within
one polling cycle of a brute-force burst landing in the logs, the cron on
the EC2 instance generates one roughly every 1 in 7 runs, or trigger one
faster by SSHing in and running `/opt/synthetic_logs.py` a few times
manually.

## Teardown

**Don't leave this running after you're done demoing it.**

```bash
cd infra/aws && terraform destroy
cd ../gcp && terraform destroy
```

Confirm in both the AWS and GCP consoles that the EC2 instance, Lambda
functions, and Cloud Function are actually gone, Terraform destroy is
reliable but a quick console check costs nothing.

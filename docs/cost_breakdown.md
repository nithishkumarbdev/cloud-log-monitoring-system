# Cost breakdown

Everything here fits inside AWS and GCP free tier limits for a single
demo deployment. Approximate, based on published free tier terms, actual
billing depends on your account's free tier status and region.

| Resource | Free tier limit | This project's usage | Expected cost |
|---|---|---|---|
| EC2 t2.micro | 750 hrs/month for 12 months (new accounts) | 1 instance, run continuously | $0 within free tier |
| Lambda (detector) | 1M requests + 400,000 GB-seconds/month, always free | ~288 invocations/day at 5 min interval | $0 |
| Lambda (Slack formatter) | same as above | only invoked when an alert fires | $0 |
| CloudWatch Logs | 5GB ingestion + 5GB storage/month, always free | synthetic traffic only, well under 5GB/month | $0 |
| CloudWatch Alarms | 10 alarms, always free | 1 alarm | $0 |
| CloudWatch Dashboard | 3 dashboards, always free | 1 dashboard | $0 |
| SNS | 1,000 email notifications/month, always free | demo alert volume | $0 |
| GCP Cloud Function | 2M invocations/month, always free | demo volume only | $0 |
| GCP Cloud Logging | 50GB/month, always free | demo volume only | $0 |

## After free tier expires

The EC2 free tier (750 hrs/month) is time-limited to 12 months on new AWS
accounts. After that, a t2.micro runs roughly $0.0116/hr on-demand in
us-east-1, which is about $8.50/month if left running continuously. Every
other resource in this stack (Lambda, CloudWatch, SNS at this volume,
GCP Cloud Functions/Logging) is in AWS/GCP's *always-free* tier, not the
12-month new-account tier, so those stay at $0 regardless of account age.

**Run `terraform destroy` when you're not actively demoing this.** See
the README's Teardown section.

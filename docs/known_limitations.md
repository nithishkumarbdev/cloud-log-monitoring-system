# Known limitations

This is a portfolio-scale demo, not a production security system. Specific
gaps, in rough order of how much they'd matter for real use:

- **Synthetic traffic only.** The EC2 instance never sees real user
  traffic, everything the detector analyzes comes from the cron-driven
  generator. The detection rules work against a real `auth.log`/access
  log shape too, but that's untested here, there's no real workload to
  validate against.

- **Static baseline for the traffic-spike rule.** `traffic_spike_baseline`
  is a fixed config value, not computed from historical volume. A real
  system would compute a rolling baseline (e.g. trailing 7-day average by
  hour-of-day) so "normal" adapts instead of needing manual retuning.

- **No deduplication or alert suppression.** If a brute-force burst spans
  multiple polling windows, it's possible to get more than one alert for
  the same underlying attacker IP. A real system would track
  already-alerted IPs with a TTL to avoid alert fatigue.

- **Terraform state is local by default.** `infra/aws/versions.tf` uses a
  local backend so a fresh clone works with zero setup. That means state
  isn't shared or locked, fine for one person running this alone, not
  fine for a team. Switching to an S3 backend with DynamoDB locking is a
  small, well-documented Terraform change if this ever needs multiple
  people applying to it.

- **`github-actions-deploy` IAM role is broader than ideal.** See
  `iam_policy_rationale.md` for the specific tradeoff and what mitigates
  it (OIDC scoped to one repo/branch, required manual approval on
  `apply`). A production version would split this into per-resource-type
  policies.

- **GCP piece doesn't share detection logic with AWS.** It proves a real,
  deployable second-cloud component, it doesn't correlate alerts across
  clouds. A real multi-cloud detection system would need a shared event
  schema and a central correlation layer, out of scope here.

- **No dead-letter queue on the Lambda.** If `detector.handler` throws
  (e.g. a malformed log line the parser doesn't expect), that invocation's
  failure is only visible in the Lambda's own CloudWatch Logs, nothing
  retries or pages anyone. Fine for a demo, not fine for anything
  alert-critical.

- **Single AWS region, single availability zone.** No failover if the AZ
  hosting the EC2 instance has an issue. Acceptable for a demo, would
  need multi-AZ (or an ASG) for anything real.

variable "aws_region" {
  description = "AWS region to deploy into"
  type        = string
  default     = "us-east-1"
}

variable "project_name" {
  description = "Prefix applied to resource names and tags"
  type        = string
  default     = "cloud-log-monitor"
}

variable "alert_email" {
  description = "Email address subscribed to the SNS alert topic"
  type        = string
}

variable "ip_allowlist" {
  description = "IPs excluded from the suspicious-IP rule (comma-separated, no spaces)"
  type        = string
  default     = ""
}

variable "brute_force_threshold" {
  description = "Failed logins from one IP within the window before it's flagged"
  type        = number
  default     = 5
}

variable "traffic_spike_baseline" {
  description = "Expected requests per minute under normal conditions"
  type        = number
  default     = 20
}

variable "poll_window_minutes" {
  description = "How far back the scheduled detector looks each run"
  type        = number
  default     = 5
}

variable "slack_webhook_url" {
  description = "Optional Slack incoming webhook URL. Leave blank to skip the Slack subscriber entirely."
  type        = string
  default     = ""
  sensitive   = true
}

variable "ssh_ingress_cidr" {
  description = "CIDR allowed to reach the demo instance on port 22. Restrict this to your own IP/32, do not leave it open to 0.0.0.0/0."
  type        = string
}

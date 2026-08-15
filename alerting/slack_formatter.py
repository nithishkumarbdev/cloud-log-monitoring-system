"""SNS-triggered Lambda. Only deployed if SLACK_WEBHOOK_URL is set, see
infra/aws/lambda.tf. Takes the JSON the detector published to SNS and
posts a readable line to Slack instead of raw JSON in an email.
"""

from __future__ import annotations

import json
import os
import urllib.request

# Read lazily inside _post_to_slack rather than at import time, so the
# pure build_slack_payload function stays importable/testable without the
# env var set (e.g. in CI, which has no real webhook to give it).
def _webhook_url() -> str:
    return os.environ["SLACK_WEBHOOK_URL"]

_RULE_EMOJI = {
    "brute_force": ":rotating_light:",
    "suspicious_ip": ":eyes:",
    "traffic_spike": ":chart_with_upwards_trend:",
}


def handler(event, context):
    for record in event["Records"]:
        alert = json.loads(record["Sns"]["Message"])
        _post_to_slack(alert)
    return {"posted": len(event["Records"])}


def build_slack_payload(alert: dict) -> dict:
    """Pure formatting, split out so it's testable without hitting the network."""
    emoji = _RULE_EMOJI.get(alert["rule"], ":warning:")
    text = (
        f"{emoji} *{alert['rule']}* from `{alert['source_ip']}`\n"
        f"{alert['detail']} (at {alert['triggered_at']})"
    )
    return {"text": text}


def _post_to_slack(alert: dict) -> None:
    body = json.dumps(build_slack_payload(alert)).encode("utf-8")
    req = urllib.request.Request(
        _webhook_url(), data=body, headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=5) as response:
        response.read()

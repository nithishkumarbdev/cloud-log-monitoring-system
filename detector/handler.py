"""Lambda entry point. Scheduled poll rather than subscription-filter push,
see docs/architecture.md for why. Pulls recent CloudWatch Logs, parses them,
runs the rules, publishes anything that fires to SNS.

Not unit tested directly, boto3 calls need mocking that adds more noise than
value here. rules.py and log_parser.py carry the actual test coverage.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timedelta, timezone

import boto3

from .log_parser import parse_cloudwatch_events
from .rules import run_all_rules

LOG_GROUP = os.environ["LOG_GROUP_NAME"]
SNS_TOPIC_ARN = os.environ["SNS_TOPIC_ARN"]
ALLOWLIST = set(os.environ.get("IP_ALLOWLIST", "").split(",")) - {""}
POLL_WINDOW_MINUTES = int(os.environ.get("POLL_WINDOW_MINUTES", "5"))

logs_client = boto3.client("logs")
sns_client = boto3.client("sns")


def handler(event, context):
    end_time = datetime.now(timezone.utc)
    start_time = end_time - timedelta(minutes=POLL_WINDOW_MINUTES)

    raw_events = _fetch_log_events(start_time, end_time)
    events = parse_cloudwatch_events(raw_events)
    alerts = run_all_rules(events, ALLOWLIST)

    for alert in alerts:
        sns_client.publish(
            TopicArn=SNS_TOPIC_ARN,
            Subject=f"[{alert.rule}] anomaly detected",
            Message=json.dumps(
                {
                    "rule": alert.rule,
                    "source_ip": alert.source_ip,
                    "detail": alert.detail,
                    "triggered_at": alert.triggered_at.isoformat(),
                    "event_count": alert.event_count,
                }
            ),
        )

    return {"events_scanned": len(events), "alerts_fired": len(alerts)}


def _fetch_log_events(start_time: datetime, end_time: datetime) -> list[dict]:
    paginator = logs_client.get_paginator("filter_log_events")
    events = []
    for page in paginator.paginate(
        logGroupName=LOG_GROUP,
        startTime=int(start_time.timestamp() * 1000),
        endTime=int(end_time.timestamp() * 1000),
    ):
        events.extend(page["events"])
    return events

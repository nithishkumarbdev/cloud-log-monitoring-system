"""Turns raw log lines (CloudWatch Logs events or synthetic-generator output,
same format) into LogEvent objects. Only handles the two line shapes the
generator produces, sshd auth failures/successes and a simple HTTP access
line. Extend the regexes here if the log source changes, keep that change
out of rules.py.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from .models import EventType, LogEvent

_SSH_FAILURE = re.compile(
    r"Failed password for (?:invalid user )?(?P<user>\S+) from (?P<ip>[\d.]+) port \d+"
)
_SSH_SUCCESS = re.compile(
    r"Accepted password for (?P<user>\S+) from (?P<ip>[\d.]+) port \d+"
)
_HTTP_LINE = re.compile(
    r"(?P<ip>[\d.]+) - - .*?\"(?:GET|POST|PUT|DELETE) (?P<path>\S+)"
)


def parse_line(timestamp: datetime, message: str) -> LogEvent | None:
    if match := _SSH_FAILURE.search(message):
        return LogEvent(
            timestamp=timestamp,
            source_ip=match.group("ip"),
            event_type=EventType.LOGIN_FAILURE,
            username=match.group("user"),
            raw=message,
        )
    if match := _SSH_SUCCESS.search(message):
        return LogEvent(
            timestamp=timestamp,
            source_ip=match.group("ip"),
            event_type=EventType.LOGIN_SUCCESS,
            username=match.group("user"),
            raw=message,
        )
    if match := _HTTP_LINE.search(message):
        return LogEvent(
            timestamp=timestamp,
            source_ip=match.group("ip"),
            event_type=EventType.HTTP_REQUEST,
            path=match.group("path"),
            raw=message,
        )
    return None


def parse_cloudwatch_events(raw_events: list[dict]) -> list[LogEvent]:
    parsed = []
    for raw in raw_events:
        ts = datetime.fromtimestamp(raw["timestamp"] / 1000, tz=timezone.utc)
        event = parse_line(ts, raw["message"])
        if event is not None:
            parsed.append(event)
    return parsed

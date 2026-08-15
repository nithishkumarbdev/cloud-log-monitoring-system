"""Normalized event shape the detection rules operate on.

Log sources (CloudWatch Logs, the synthetic generator, whatever gets added
later) all need to map into this before they hit the rules. Keeping the
parsing separate from the detection logic is the whole point: the rules
never touch a raw log line.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class EventType(str, Enum):
    LOGIN_FAILURE = "login_failure"
    LOGIN_SUCCESS = "login_success"
    HTTP_REQUEST = "http_request"


@dataclass(frozen=True)
class LogEvent:
    timestamp: datetime
    source_ip: str
    event_type: EventType
    username: str | None = None
    path: str | None = None
    raw: str | None = None

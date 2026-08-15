from datetime import datetime, timezone

from detector.models import EventType
from detector.log_parser import parse_line

TS = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_parses_ssh_failure():
    line = "Failed password for admin from 203.0.113.5 port 51234 ssh2"
    event = parse_line(TS, line)
    assert event is not None
    assert event.event_type == EventType.LOGIN_FAILURE
    assert event.source_ip == "203.0.113.5"
    assert event.username == "admin"


def test_parses_ssh_failure_invalid_user():
    line = "Failed password for invalid user root from 198.51.100.7 port 22 ssh2"
    event = parse_line(TS, line)
    assert event is not None
    assert event.username == "root"
    assert event.source_ip == "198.51.100.7"


def test_parses_ssh_success():
    line = "Accepted password for ec2-user from 10.0.0.12 port 22 ssh2"
    event = parse_line(TS, line)
    assert event is not None
    assert event.event_type == EventType.LOGIN_SUCCESS


def test_parses_http_line():
    line = '192.0.2.44 - - [01/Jan/2026:00:00:00 +0000] "GET /login HTTP/1.1" 200 512'
    event = parse_line(TS, line)
    assert event is not None
    assert event.event_type == EventType.HTTP_REQUEST
    assert event.path == "/login"


def test_returns_none_for_unrecognized_line():
    assert parse_line(TS, "some unrelated kernel message") is None

from datetime import datetime, timedelta, timezone

from detector.models import EventType, LogEvent
from detector.rules import detect_brute_force, detect_suspicious_ip, detect_traffic_spike

BASE = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _login_failure(offset_seconds: int, ip: str, user: str = "admin") -> LogEvent:
    return LogEvent(
        timestamp=BASE + timedelta(seconds=offset_seconds),
        source_ip=ip,
        event_type=EventType.LOGIN_FAILURE,
        username=user,
    )


def _http(offset_seconds: int, ip: str, path: str = "/") -> LogEvent:
    return LogEvent(
        timestamp=BASE + timedelta(seconds=offset_seconds),
        source_ip=ip,
        event_type=EventType.HTTP_REQUEST,
        path=path,
    )


class TestBruteForce:
    def test_fires_on_burst_within_window(self):
        events = [_login_failure(i * 10, "203.0.113.5") for i in range(6)]
        alerts = detect_brute_force(events, window=timedelta(minutes=5), threshold=5)
        assert len(alerts) == 1
        assert alerts[0].source_ip == "203.0.113.5"
        assert alerts[0].event_count == 6

    def test_no_alert_below_threshold(self):
        events = [_login_failure(i * 10, "203.0.113.5") for i in range(3)]
        alerts = detect_brute_force(events, window=timedelta(minutes=5), threshold=5)
        assert alerts == []

    def test_no_alert_when_spread_beyond_window(self):
        # 5 failures but 20 minutes apart each, never 5 within a 5 minute window
        events = [_login_failure(i * 1200, "203.0.113.5") for i in range(5)]
        alerts = detect_brute_force(events, window=timedelta(minutes=5), threshold=5)
        assert alerts == []

    def test_tracks_ips_independently(self):
        events = [_login_failure(i * 10, "203.0.113.5") for i in range(6)]
        events += [_login_failure(i * 10, "198.51.100.7") for i in range(2)]
        alerts = detect_brute_force(events, threshold=5)
        assert len(alerts) == 1
        assert alerts[0].source_ip == "203.0.113.5"


class TestSuspiciousIP:
    def test_fires_for_non_allowlisted_repeat_ip(self):
        events = [_http(i, "198.51.100.20") for i in range(12)]
        alerts = detect_suspicious_ip(events, allowlist=set(), threshold=10)
        assert len(alerts) == 1
        assert alerts[0].source_ip == "198.51.100.20"
        assert alerts[0].event_count == 12

    def test_allowlisted_ip_never_fires(self):
        events = [_http(i, "10.0.0.5") for i in range(50)]
        alerts = detect_suspicious_ip(events, allowlist={"10.0.0.5"}, threshold=10)
        assert alerts == []

    def test_no_alert_below_threshold(self):
        events = [_http(i, "198.51.100.20") for i in range(4)]
        alerts = detect_suspicious_ip(events, allowlist=set(), threshold=10)
        assert alerts == []


class TestTrafficSpike:
    def test_fires_when_volume_exceeds_baseline(self):
        # baseline 20/min * 3x multiplier = 60 needed; put 100 in one window
        # (half-second spacing keeps all 100 inside the same 60s bucket)
        events = [_http(i * 0.5, f"192.0.2.{i % 200}") for i in range(100)]
        alerts = detect_traffic_spike(
            events, window=timedelta(minutes=1), baseline_per_window=20.0, multiplier=3.0
        )
        assert len(alerts) == 1
        assert alerts[0].event_count == 100

    def test_no_alert_under_normal_volume(self):
        events = [_http(i * 3, f"192.0.2.{i % 200}") for i in range(15)]
        alerts = detect_traffic_spike(
            events, window=timedelta(minutes=1), baseline_per_window=20.0, multiplier=3.0
        )
        assert alerts == []

    def test_empty_events_no_crash(self):
        assert detect_traffic_spike([]) == []

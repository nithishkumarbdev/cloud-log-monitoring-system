"""Rule-based anomaly detection.

Each function takes a list of LogEvent and returns a list of Alert. No AWS
SDK calls in here on purpose, the handler module owns talking to Lambda /
CloudWatch / SNS, this module just needs a list of events and answers. That
split is what makes it possible to unit test the actual detection logic
without deploying anything.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .models import EventType, LogEvent


@dataclass(frozen=True)
class Alert:
    rule: str
    source_ip: str
    detail: str
    triggered_at: datetime
    event_count: int


def detect_brute_force(
    events: list[LogEvent],
    window: timedelta = timedelta(minutes=5),
    threshold: int = 5,
) -> list[Alert]:
    """Flag an IP with >= threshold failed logins inside a rolling window.

    Threshold of 5 in 5 minutes is roughly what fail2ban's sshd default
    ships with. Sliding window rather than fixed buckets so a burst that
    straddles a bucket boundary doesn't get split and hide under the
    threshold.
    """
    failures = sorted(
        (e for e in events if e.event_type == EventType.LOGIN_FAILURE),
        key=lambda e: e.timestamp,
    )

    by_ip: dict[str, list[datetime]] = defaultdict(list)
    for event in failures:
        by_ip[event.source_ip].append(event.timestamp)

    alerts: list[Alert] = []
    for ip, timestamps in by_ip.items():
        for i, start in enumerate(timestamps):
            window_end = start + window
            count = sum(1 for t in timestamps[i:] if t <= window_end)
            if count >= threshold:
                alerts.append(
                    Alert(
                        rule="brute_force",
                        source_ip=ip,
                        detail=f"{count} failed logins within {window}",
                        triggered_at=start,
                        event_count=count,
                    )
                )
                break  # one alert per IP is enough, don't re-fire on every sub-window
    return alerts


def detect_suspicious_ip(
    events: list[LogEvent],
    allowlist: set[str],
    threshold: int = 10,
) -> list[Alert]:
    """Flag any non-allowlisted IP making >= threshold requests total.

    Deliberately not time-windowed, this one's meant to catch an IP that's
    just persistently poking the instance over a longer stretch, not a
    short burst (that's what the brute-force and traffic-spike rules are
    for).
    """
    counts: dict[str, int] = defaultdict(int)
    last_seen: dict[str, datetime] = {}
    for event in events:
        if event.source_ip in allowlist:
            continue
        counts[event.source_ip] += 1
        last_seen[event.source_ip] = event.timestamp

    alerts = []
    for ip, count in counts.items():
        if count >= threshold:
            alerts.append(
                Alert(
                    rule="suspicious_ip",
                    source_ip=ip,
                    detail=f"{count} requests from non-allowlisted IP",
                    triggered_at=last_seen[ip],
                    event_count=count,
                )
            )
    return alerts


def detect_traffic_spike(
    events: list[LogEvent],
    window: timedelta = timedelta(minutes=1),
    baseline_per_window: float = 20.0,
    multiplier: float = 3.0,
) -> list[Alert]:
    """Flag a time bucket where total event volume exceeds baseline * multiplier.

    Fixed buckets are fine here (unlike brute force) since a spike by
    definition affects a whole window, not a handful of events that could
    fall on a boundary. Baseline is a static config value for now, not
    computed from history, see known_limitations.md.
    """
    if not events:
        return []

    ordered = sorted(events, key=lambda e: e.timestamp)
    bucket_start = ordered[0].timestamp
    threshold = baseline_per_window * multiplier

    alerts = []
    bucket_events: list[LogEvent] = []
    for event in ordered:
        if event.timestamp < bucket_start + window:
            bucket_events.append(event)
            continue

        if len(bucket_events) >= threshold:
            alerts.append(
                Alert(
                    rule="traffic_spike",
                    source_ip="aggregate",
                    detail=f"{len(bucket_events)} events in {window}, baseline {baseline_per_window}",
                    triggered_at=bucket_start,
                    event_count=len(bucket_events),
                )
            )

        bucket_start = event.timestamp
        bucket_events = [event]

    if len(bucket_events) >= threshold:
        alerts.append(
            Alert(
                rule="traffic_spike",
                source_ip="aggregate",
                detail=f"{len(bucket_events)} events in {window}, baseline {baseline_per_window}",
                triggered_at=bucket_start,
                event_count=len(bucket_events),
            )
        )
    return alerts


def run_all_rules(
    events: list[LogEvent],
    allowlist: set[str],
) -> list[Alert]:
    return [
        *detect_brute_force(events),
        *detect_suspicious_ip(events, allowlist),
        *detect_traffic_spike(events),
    ]

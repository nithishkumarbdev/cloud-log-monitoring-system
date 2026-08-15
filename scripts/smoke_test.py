"""Proves the detector actually catches something, not just that the code
imports cleanly. Generates synthetic traffic with a known brute-force burst,
suspicious IP, and traffic spike baked in, runs it through the parser and
rules, and fails loudly if any of the three don't fire.

No AWS access needed, this is the first thing to run after cloning.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "log-generator"))

from detector.log_parser import parse_line  # noqa: E402
from detector.rules import run_all_rules  # noqa: E402
from generate import generate_events  # noqa: E402


def main() -> int:
    lines = generate_events(minutes=10, seed=7)

    events = []
    for line in lines:
        ts_str, message = line.split(" ", 1)
        ts = datetime.fromisoformat(ts_str)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        parsed = parse_line(ts, message)
        if parsed:
            events.append(parsed)

    print(f"generated {len(lines)} raw lines, parsed {len(events)} events")

    alerts = run_all_rules(events, allowlist=set())
    rules_fired = {a.rule for a in alerts}

    print(f"\n{len(alerts)} alert(s) fired:")
    for alert in alerts:
        print(f"  [{alert.rule}] {alert.source_ip}: {alert.detail}")

    expected = {"brute_force", "suspicious_ip", "traffic_spike"}
    missing = expected - rules_fired

    if missing:
        print(f"\nFAIL: expected all of {expected} to fire, missing {missing}")
        return 1

    print(f"\nOK: all {len(expected)} rule types fired on synthetic data")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

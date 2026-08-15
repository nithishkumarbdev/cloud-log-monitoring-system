"""Demo data generator. This is NOT real traffic, it's synthetic events
written in auth.log / access.log format so the detector has something to
chew on without a live instance. Run standalone (prints or writes to a
file) or point it at a CloudWatch Log Group with --push if you've deployed
the infra and want to see the alarms actually fire.

Usage:
    python generate.py --out sample.log --minutes 10
    python generate.py --push --log-group /demo/synthetic-auth
"""

from __future__ import annotations

import argparse
import ipaddress
import random
from datetime import datetime, timedelta, timezone

NORMAL_USERS = ["ec2-user", "deploy", "ops"]
ATTACK_USERNAMES = ["root", "admin", "test", "oracle", "postgres", "ubuntu"]


def _random_ip(rng: random.Random) -> str:
    return str(ipaddress.IPv4Address(rng.randint(0x01000000, 0xDFFFFFFF)))


def generate_events(minutes: int, seed: int | None = None) -> list[str]:
    rng = random.Random(seed)
    start = datetime.now(timezone.utc) - timedelta(minutes=minutes)
    lines: list[str] = []

    # baseline normal traffic across the whole window
    t = start
    while t < start + timedelta(minutes=minutes):
        t += timedelta(seconds=rng.uniform(5, 20))
        if rng.random() < 0.85:
            lines.append(_http_line(t, _random_ip(rng), success=True))
        else:
            user = rng.choice(NORMAL_USERS)
            lines.append(_ssh_success(t, user, _random_ip(rng)))

    # a brute-force burst from one IP partway through
    attacker_ip = _random_ip(rng)
    burst_start = start + timedelta(minutes=minutes * rng.uniform(0.3, 0.6))
    for i in range(rng.randint(8, 15)):
        lines.append(
            _ssh_failure(
                burst_start + timedelta(seconds=i * rng.uniform(2, 8)),
                rng.choice(ATTACK_USERNAMES),
                attacker_ip,
            )
        )

    # a persistent-but-quiet suspicious IP scattered across the window
    suspicious_ip = _random_ip(rng)
    for _ in range(rng.randint(12, 20)):
        t = start + timedelta(seconds=rng.uniform(0, minutes * 60))
        lines.append(_http_line(t, suspicious_ip, success=rng.random() > 0.3))

    # a short traffic spike
    spike_start = start + timedelta(minutes=minutes * rng.uniform(0.6, 0.8))
    for i in range(rng.randint(80, 150)):
        lines.append(
            _http_line(
                spike_start + timedelta(milliseconds=i * rng.uniform(50, 300)),
                _random_ip(rng),
                success=True,
            )
        )

    lines.sort(key=lambda line: line.split(" ", 1)[0])
    return lines


def _ssh_failure(t: datetime, user: str, ip: str) -> str:
    return f"{t.isoformat()} sshd[1234]: Failed password for {user} from {ip} port {random.randint(1024, 65000)} ssh2"


def _ssh_success(t: datetime, user: str, ip: str) -> str:
    return f"{t.isoformat()} sshd[1234]: Accepted password for {user} from {ip} port {random.randint(1024, 65000)} ssh2"


def _http_line(t: datetime, ip: str, success: bool) -> str:
    status = 200 if success else 404
    path = random.choice(["/", "/login", "/api/health", "/assets/app.js"])
    return f'{t.isoformat()} {ip} - - "GET {path} HTTP/1.1" {status} {random.randint(200, 4096)}'


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=int, default=10, help="span of synthetic traffic to generate")
    parser.add_argument("--out", type=str, default=None, help="file to write to, defaults to stdout")
    parser.add_argument("--seed", type=int, default=None, help="RNG seed for reproducible output")
    args = parser.parse_args()

    lines = generate_events(args.minutes, seed=args.seed)
    output = "\n".join(lines) + "\n"

    if args.out:
        with open(args.out, "w") as f:
            f.write(output)
        print(f"wrote {len(lines)} synthetic events to {args.out}")
    else:
        print(output)


if __name__ == "__main__":
    main()

#!/bin/bash
set -euo pipefail

dnf install -y amazon-cloudwatch-agent python3

mkdir -p /var/log/demo
touch /var/log/demo/auth.log /var/log/demo/access.log

# Trimmed inline version of log-generator/generate.py's SSH failure and
# HTTP line shapes, kept dependency-free (stdlib only) since this runs on
# a bare AL2023 box with nothing pre-installed beyond python3 itself.
cat > /opt/synthetic_logs.py << 'PYEOF'
import random
import time
from datetime import datetime, timezone

ATTACK_USERS = ["root", "admin", "test", "oracle"]
NORMAL_USERS = ["ec2-user", "deploy"]

def rand_ip():
    return f"{random.randint(1,223)}.{random.randint(0,255)}.{random.randint(0,255)}.{random.randint(1,254)}"

def now():
    return datetime.now(timezone.utc).isoformat()

with open("/var/log/demo/auth.log", "a") as auth, open("/var/log/demo/access.log", "a") as access:
    # occasional brute-force burst
    if random.random() < 0.15:
        attacker = rand_ip()
        for _ in range(random.randint(6, 12)):
            auth.write(f"{now()} sshd[1234]: Failed password for {random.choice(ATTACK_USERS)} from {attacker} port {random.randint(1024,65000)} ssh2\n")
    else:
        auth.write(f"{now()} sshd[1234]: Accepted password for {random.choice(NORMAL_USERS)} from {rand_ip()} port {random.randint(1024,65000)} ssh2\n")

    # baseline HTTP noise, occasional spike
    request_count = random.randint(80, 150) if random.random() < 0.1 else random.randint(3, 10)
    for _ in range(request_count):
        access.write(f'{now()} {rand_ip()} - - "GET / HTTP/1.1" 200 512\n')
PYEOF

echo "*/2 * * * * root /usr/bin/python3 /opt/synthetic_logs.py" > /etc/cron.d/synthetic-logs
chmod 644 /etc/cron.d/synthetic-logs

cat > /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json << EOF
{
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/demo/auth.log",
            "log_group_name": "${log_group_name}",
            "log_stream_name": "{instance_id}/auth",
            "timezone": "UTC"
          },
          {
            "file_path": "/var/log/demo/access.log",
            "log_group_name": "${log_group_name}",
            "log_stream_name": "{instance_id}/access",
            "timezone": "UTC"
          }
        ]
      }
    }
  }
}
EOF

/opt/aws/amazon-cloudwatch-agent/bin/amazon-cloudwatch-agent-ctl \
  -a fetch-config -m ec2 -s \
  -c file:/opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json

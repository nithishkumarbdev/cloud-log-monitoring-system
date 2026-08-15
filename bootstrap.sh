#!/usr/bin/env bash
# One-command setup for everything that doesn't need a cloud account:
# venv, dependencies, lint, tests, and the end-to-end smoke test.
# Deploying the actual infrastructure is a separate, explicit step,
# see docs/DEPLOYMENT.md, that one needs your own AWS/GCP credentials
# and isn't something a bootstrap script should do silently.
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate

pip install --quiet --upgrade pip
pip install --quiet -r detector/requirements.txt -r detector/requirements-dev.txt
pip install --quiet ruff mypy

echo "==> lint"
ruff check detector alerting log-generator scripts

echo "==> type check"
mypy detector --ignore-missing-imports

echo "==> unit tests"
python -m pytest detector/tests alerting/tests -v

echo "==> smoke test"
python scripts/smoke_test.py

echo ""
echo "Bootstrap complete. Detector logic, log generator, and Slack"
echo "formatter are all verified working locally, no AWS account needed."
echo "Next: docs/DEPLOYMENT.md to actually deploy the infrastructure."

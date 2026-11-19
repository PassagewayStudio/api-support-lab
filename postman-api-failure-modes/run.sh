#!/usr/bin/env bash
# Runs the whole collection with newman. Token comes from the environment, never the repo.
# Usage: GITHUB_TOKEN=... ./run.sh
set -euo pipefail
cd "$(dirname "$0")"
python3 mock/failure_lab.py 8099 >/tmp/failure_lab.log 2>&1 &
LAB_PID=$!
trap 'kill $LAB_PID 2>/dev/null' EXIT
sleep 1
newman run collections/api-failure-modes.postman_collection.json \
  -e environments/local.postman_environment.json \
  --env-var "github_token=${GITHUB_TOKEN:-}"

#!/bin/bash
set -e
cd ~/deploy/handoff-api

[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -q -r requirements.txt

if [ -n "${HANDOFF_DATABASE_URL}" ]; then
  echo "HANDOFF_DATABASE_URL=${HANDOFF_DATABASE_URL}" > .env
fi

.venv/bin/python seed.py 2>/dev/null || true

pkill -f "handoff-api.*uvicorn main:app" 2>/dev/null || true
sleep 3

setsid nohup .venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000 > handoff.log 2>&1 < /dev/null &
sleep 5

.venv/bin/python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')" || exit 1
echo "Handoff API deployed and healthy."

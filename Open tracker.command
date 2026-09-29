#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ ! -f pipeline.local.md ]; then
  cp pipeline.example.md pipeline.local.md
fi
/usr/bin/python3 build_dashboard.py
if ! /usr/bin/curl --silent --fail http://127.0.0.1:8770/dashboard.local.html >/dev/null; then
  /usr/bin/nohup /usr/bin/python3 tracker_server.py > /tmp/manuscript-tracker-public.log 2>&1 &
  for attempt in 1 2 3 4 5; do
    /usr/bin/curl --silent --fail http://127.0.0.1:8770/dashboard.local.html >/dev/null && break
    sleep 0.3
  done
fi
open http://127.0.0.1:8770/dashboard.local.html

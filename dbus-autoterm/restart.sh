#!/bin/bash
set -euo pipefail

SERVICE_NAME="dbus-autoterm"

if command -v svc >/dev/null 2>&1 && [ -d "/service/$SERVICE_NAME" ]; then
    svc -t "/service/$SERVICE_NAME"
else
    pkill -f "/data/apps/dbus-autoterm/app.py" || true
fi

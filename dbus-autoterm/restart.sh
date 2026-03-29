#!/bin/bash
set -euo pipefail

SERVICE_NAME="dbus-autoterm"
SERVICE_LINK="/service/$SERVICE_NAME"

if command -v svc >/dev/null 2>&1 && [ -d "$SERVICE_LINK" ]; then
    svc -d "$SERVICE_LINK" || true
    sleep 1
fi

pkill -f "/data/apps/dbus-autoterm/app.py" || true

if command -v svc >/dev/null 2>&1 && [ -d "$SERVICE_LINK" ]; then
    svc -u "$SERVICE_LINK" || true
fi

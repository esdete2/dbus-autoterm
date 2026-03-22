#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)
SERVICE_NAME="dbus-autoterm"
SERVICE_LINK="/service/$SERVICE_NAME"

remount_root() {
    mount -o "remount,$1" / >/dev/null 2>&1 || true
}

remount_root rw
rm -f "$SERVICE_LINK"
ln -s "$SCRIPT_DIR/service" "$SERVICE_LINK"
remount_root ro

if command -v svc >/dev/null 2>&1; then
    svc -u "$SERVICE_LINK" || true
fi

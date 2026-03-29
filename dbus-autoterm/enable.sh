#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)
SERVICE_NAME="dbus-autoterm"
SERVICE_LINK="/service/$SERVICE_NAME"

remount_root() {
    mount -o "remount,$1" / >/dev/null 2>&1 || true
}

start_service() {
    if ! command -v svc >/dev/null 2>&1 || [ ! -d "$SERVICE_LINK" ]; then
        return 0
    fi

    i=0
    while [ $i -lt 50 ]; do
        if [ -e "$SERVICE_LINK/supervise/ok" ] || [ -p "$SERVICE_LINK/supervise/ok" ]; then
            svc -u "$SERVICE_LINK" || true
            return 0
        fi
        i=$((i + 1))
        sleep 0.1
    done

    echo "Warning: runit did not detect $SERVICE_NAME yet; start it manually if needed."
}

remount_root rw
mkdir -p "$(dirname "$SERVICE_LINK")"
rm -f "$SERVICE_LINK"
ln -s "$SCRIPT_DIR/service" "$SERVICE_LINK"
remount_root ro

start_service

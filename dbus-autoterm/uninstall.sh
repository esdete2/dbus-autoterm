#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)
SERVICE_NAME="dbus-autoterm"
SERVICE_LINK="/service/$SERVICE_NAME"
RC_LOCAL="/data/rc.local"
INSTALL_LINE="bash $SCRIPT_DIR/install.sh"
SERIAL_STARTER_RULES="/etc/udev/rules.d/serial-starter.rules"
SERIAL_STARTER_RULE='ACTION=="add", SUBSYSTEM=="tty", SUBSYSTEMS=="platform|usb-serial", ENV{ID_BUS}=="usb", ENV{ID_MODEL}=="Autoterm_UART", ENV{VE_SERVICE}="ignore", SYMLINK+="ttyAUTOTERM"'

remount_root() {
    mount -o "remount,$1" / >/dev/null 2>&1 || true
}

if command -v svc >/dev/null 2>&1 && [ -d "$SERVICE_LINK" ]; then
    svc -d "$SERVICE_LINK" || true
fi

remount_root rw
rm -f "$SERVICE_LINK"

if [ -f "$RC_LOCAL" ]; then
    sed -i "\\|$INSTALL_LINE|d" "$RC_LOCAL"
fi
if [ -f "$SERIAL_STARTER_RULES" ]; then
    sed -i "\\|$SERIAL_STARTER_RULE|d" "$SERIAL_STARTER_RULES"
    udevadm control --reload || true
fi
remount_root ro

pkill -f "/data/apps/dbus-autoterm/app.py" || true

echo "Uninstalled $SERVICE_NAME service link"

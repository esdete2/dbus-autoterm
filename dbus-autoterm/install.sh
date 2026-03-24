#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)
SERVICE_NAME="dbus-autoterm"
SERVICE_LINK="/service/$SERVICE_NAME"
CONFIG_FILE="$SCRIPT_DIR/config.ini"
SAMPLE_CONFIG="$SCRIPT_DIR/config.sample.ini"
PYTHON_BIN="${PYTHON_BIN:-python3}"
RC_LOCAL="/data/rc.local"
INSTALL_LINE="bash $SCRIPT_DIR/install.sh"
SERIAL_STARTER_RULES="/etc/udev/rules.d/serial-starter.rules"
SERIAL_STARTER_RULE='ACTION=="add", SUBSYSTEM=="tty", SUBSYSTEMS=="platform|usb-serial", ENV{ID_BUS}=="usb", ENV{ID_MODEL}=="Autoterm_UART", ENV{VE_SERVICE}="ignore", SYMLINK+="ttyAUTOTERM"'

remount_root() {
    mount -o "remount,$1" / >/dev/null 2>&1 || true
}

chmod 744 "$SCRIPT_DIR/install.sh" "$SCRIPT_DIR/restart.sh" "$SCRIPT_DIR/uninstall.sh" "$SCRIPT_DIR/enable.sh" "$SCRIPT_DIR/disable.sh"
chmod 755 "$SCRIPT_DIR/service/run" "$SCRIPT_DIR/service/log/run"

if [ ! -f "$CONFIG_FILE" ]; then
    cp "$SAMPLE_CONFIG" "$CONFIG_FILE"
    echo "Created $CONFIG_FILE from config.sample.ini"
fi

if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "Missing Python runtime: $PYTHON_BIN"
    exit 1
fi

if [ ! -f "$RC_LOCAL" ]; then
    {
        echo "#!/bin/bash"
        echo
    } > "$RC_LOCAL"
    chmod 755 "$RC_LOCAL"
fi

remount_root rw
rm -f "$SERVICE_LINK"
ln -s "$SCRIPT_DIR/service" "$SERVICE_LINK"
if [ -f "$SERIAL_STARTER_RULES" ]; then
    if ! grep -qxF "$SERIAL_STARTER_RULE" "$SERIAL_STARTER_RULES"; then
        echo "$SERIAL_STARTER_RULE" >> "$SERIAL_STARTER_RULES"
        echo "Added Autoterm serial-starter ignore rule; reboot or replug the adapter if it is already attached."
    fi
    udevadm control --reload || true
fi
# Re-run install on boot so the service link is recreated after Venus OS maintenance or image changes.
grep -qxF "$INSTALL_LINE" "$RC_LOCAL" || echo "$INSTALL_LINE" >> "$RC_LOCAL"
remount_root ro

if command -v svc >/dev/null 2>&1; then
    svc -u "$SERVICE_LINK" || true
    svc -t "$SERVICE_LINK" || true
fi

echo "Installed $SERVICE_NAME"

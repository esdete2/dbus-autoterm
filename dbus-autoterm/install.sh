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

if ! "$PYTHON_BIN" -m py_compile \
    "$SCRIPT_DIR/app.py" \
    "$SCRIPT_DIR/controller.py" \
    "$SCRIPT_DIR/domain.py" \
    "$SCRIPT_DIR/gx_dbus.py" \
    "$SCRIPT_DIR/protocol.py" \
    "$SCRIPT_DIR/provider.py" \
    "$SCRIPT_DIR/transports.py" >/dev/null 2>&1; then
    echo "Python source validation failed"
    exit 1
fi

if ! "$PYTHON_BIN" -c '
import sys
from pathlib import Path

app_root = Path(sys.argv[1])
candidates = (
    app_root / "ext" / "velib_python",
    Path("/opt/victronenergy/dbus-systemcalc-py/ext/velib_python"),
    Path("/opt/victronenergy/dbus-systemcalc-py/velib_python"),
)
for candidate in candidates:
    if candidate.exists():
        candidate_str = str(candidate)
        if candidate_str not in sys.path:
            sys.path.insert(1, candidate_str)

import dbus
from gi.repository import GLib
from vedbus import VeDbusService

assert dbus is not None
assert GLib is not None
assert VeDbusService is not None
' "$SCRIPT_DIR" >/dev/null 2>&1; then
    echo "Missing runtime prerequisites. Venus OS must provide dbus, GLib, and vedbus, or velib_python must be available under $SCRIPT_DIR/ext/velib_python."
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
grep -qxF "$INSTALL_LINE" "$RC_LOCAL" || echo "$INSTALL_LINE" >> "$RC_LOCAL"
remount_root ro

if command -v svc >/dev/null 2>&1; then
    svc -u "$SERVICE_LINK" || true
    svc -t "$SERVICE_LINK" || true
fi

echo "Installed $SERVICE_NAME"

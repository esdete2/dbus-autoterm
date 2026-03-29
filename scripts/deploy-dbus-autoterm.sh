#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
GUI_VARIANT="${GUI_VARIANT:-default}"
ARCHIVE="$ROOT_DIR/dist/dbus-autoterm.tar.gz"
CERBO_HOST="${CERBO_HOST:-root@einstein}"
CERBO_APP_DIR="${CERBO_APP_DIR:-/data/apps/dbus-autoterm}"
CERBO_ARCHIVE_PATH="${CERBO_ARCHIVE_PATH:-/data/dbus-autoterm.tar.gz}"
TMP_DIR=$(mktemp -d)
CONTROL_PATH="$TMP_DIR/ssh-control"
SSH_OPTS="-o ControlMaster=auto -o ControlPersist=60 -o ControlPath=$CONTROL_PATH"

cleanup() {
    ssh $SSH_OPTS -O exit "$CERBO_HOST" >/dev/null 2>&1 || true
    rm -rf "$TMP_DIR"
}

trap cleanup EXIT

case "$GUI_VARIANT" in
    default)
        ;;
    native-gui)
        ARCHIVE="$ROOT_DIR/dist/dbus-autoterm-native-gui.tar.gz"
        ;;
    *)
        echo "Unsupported GUI_VARIANT: $GUI_VARIANT" >&2
        exit 1
        ;;
esac

if [ ! -f "$ARCHIVE" ]; then
    echo "Missing package archive: $ARCHIVE" >&2
    if [ "$GUI_VARIANT" = "native-gui" ]; then
        echo "Run make package:native-gui first." >&2
    else
        echo "Run make package first." >&2
    fi
    exit 1
fi

if ! command -v ssh >/dev/null 2>&1; then
    echo "Missing ssh runtime" >&2
    exit 1
fi

if ! command -v scp >/dev/null 2>&1; then
    echo "Missing scp runtime" >&2
    exit 1
fi

echo "Uploading $ARCHIVE to $CERBO_HOST:$CERBO_ARCHIVE_PATH"
scp $SSH_OPTS "$ARCHIVE" "$CERBO_HOST:$CERBO_ARCHIVE_PATH"

echo "Deploying package on $CERBO_HOST"
ssh $SSH_OPTS "$CERBO_HOST" \
    "ARCHIVE_PATH='$CERBO_ARCHIVE_PATH' CERBO_APP_DIR='$CERBO_APP_DIR' GUI_VARIANT='$GUI_VARIANT' /bin/sh -s" <<'REMOTE_SCRIPT'
set -eu

archive_path="${ARCHIVE_PATH}"
app_dir="${CERBO_APP_DIR}"
gui_variant="${GUI_VARIANT}"
parent_dir=$(dirname "$app_dir")
deploy_root=/tmp/dbus-autoterm-deploy
extracted_dir="$deploy_root/dbus-autoterm"
backup_config="$deploy_root/config.ini"

echo "Stopping existing service if present"
if command -v svc >/dev/null 2>&1 && [ -d /service/dbus-autoterm ]; then
    svc -d /service/dbus-autoterm || true
    sleep 1
fi
pkill -f '/data/apps/dbus-autoterm/app.py' || true

echo "Preparing deploy directory"
rm -rf "$deploy_root"
mkdir -p "$deploy_root" "$parent_dir"

if [ -f "$app_dir/config.ini" ]; then
    cp "$app_dir/config.ini" "$backup_config"
fi

echo "Unpacking archive"
tar -xzf "$archive_path" -C "$deploy_root"
rm -rf "$app_dir"
mv "$extracted_dir" "$app_dir"

if [ -f "$backup_config" ]; then
    mv "$backup_config" "$app_dir/config.ini"
fi

echo "Running install.sh"
cd "$app_dir"
GUI_VARIANT="$gui_variant" bash install.sh

echo "Cleaning up"
rm -f "$archive_path"
rm -rf "$deploy_root"
REMOTE_SCRIPT

echo "Deployment finished."

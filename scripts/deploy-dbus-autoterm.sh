#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ARCHIVE="$ROOT_DIR/dist/dbus-autoterm.tar.gz"
CERBO_HOST="${CERBO_HOST:-root@einstein}"
CERBO_APP_DIR="${CERBO_APP_DIR:-/data/apps/dbus-autoterm}"
CERBO_ARCHIVE_PATH="${CERBO_ARCHIVE_PATH:-/data/dbus-autoterm.tar.gz}"

if [ ! -f "$ARCHIVE" ]; then
    echo "Missing package archive: $ARCHIVE" >&2
    echo "Run make package first." >&2
    exit 1
fi

if ! command -v scp >/dev/null 2>&1; then
    echo "Missing scp runtime" >&2
    exit 1
fi

if ! command -v ssh >/dev/null 2>&1; then
    echo "Missing ssh runtime" >&2
    exit 1
fi

echo "Uploading $ARCHIVE to $CERBO_HOST:$CERBO_ARCHIVE_PATH"
scp "$ARCHIVE" "$CERBO_HOST:$CERBO_ARCHIVE_PATH"

echo "Deploying package on $CERBO_HOST"
ssh "$CERBO_HOST" \
    "set -eu
    archive_path='$CERBO_ARCHIVE_PATH'
    app_dir='$CERBO_APP_DIR'
    parent_dir=\$(dirname \"\$app_dir\")
    deploy_root=/tmp/dbus-autoterm-deploy
    extracted_dir=\$deploy_root/dbus-autoterm
    backup_config=\$deploy_root/config.ini

    rm -rf \"\$deploy_root\"
    mkdir -p \"\$deploy_root\" \"\$parent_dir\"
    if [ -f \"\$app_dir/config.ini\" ]; then
        cp \"\$app_dir/config.ini\" \"\$backup_config\"
    fi

    tar -xzf \"\$archive_path\" -C \"\$deploy_root\"
    rm -rf \"\$app_dir\"
    mv \"\$extracted_dir\" \"\$app_dir\"

    if [ -f \"\$backup_config\" ]; then
        mv \"\$backup_config\" \"\$app_dir/config.ini\"
    fi

    cd \"\$app_dir\"
    bash install.sh
    rm -f \"\$archive_path\"
    rm -rf \"\$deploy_root\"
    "

echo "Deployment finished."

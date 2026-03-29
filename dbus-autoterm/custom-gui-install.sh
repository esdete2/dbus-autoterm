#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)
SOURCE_ROOT="$SCRIPT_DIR/qml/gui-v2/common"
TARGET_ROOT="/opt/victronenergy/gui-v2/Victron/VenusOS"

if [ ! -d "$SOURCE_ROOT" ] || [ ! -d "$TARGET_ROOT" ]; then
    exit 0
fi

files_changed=0

while IFS= read -r source; do
    rel_path="${source#$SOURCE_ROOT/}"
    target="$TARGET_ROOT/$rel_path"
    mkdir -p "$(dirname "$target")"
    if [ ! -f "$target" ] || ! cmp -s "$source" "$target"; then
        rm -f "$target"
        cp "$source" "$target"
        files_changed=1
    fi
done < <(find "$SOURCE_ROOT" -type f \( -name '*.qml' -o -name '*.svg' -o -name '*.png' \) | sort)

if [ "$files_changed" -eq 1 ]; then
    echo "Installed custom Autoterm GUI files."

    if [ -d "/service/gui" ]; then
        service_path="/service/gui"
    else
        service_path="/service/start-gui"
    fi

    svc -d "$service_path"
    sleep 1
    svc -u "$service_path"
    echo "Restarted GUI service."
fi

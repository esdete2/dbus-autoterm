#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)
SOURCE_ROOT="$SCRIPT_DIR/qml/gui-v2/common"
TARGET_ROOT="/opt/victronenergy/gui-v2/Victron/VenusOS"

if [ ! -d "$SOURCE_ROOT" ] || [ ! -d "$TARGET_ROOT" ]; then
    exit 0
fi

while IFS= read -r source; do
    rel_path="${source#$SOURCE_ROOT/}"
    target="$TARGET_ROOT/$rel_path"
    rm -f "$target"
done < <(find "$SOURCE_ROOT" -type f -name '*.qml' | sort)

#!/bin/bash
set -euo pipefail

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)
GUI_ROOT="/opt/victronenergy/gui-v2"
TARGET_ROOT="$GUI_ROOT/Victron/VenusOS"
CMAKE_FILE="$GUI_ROOT/cmake/ModuleVenus_Sources.cmake"
BACKUP_SUFFIX=".dbus-autoterm.orig"
FILES_CHANGED=0

PATCHED_FILES=(
    "components/SwipePageModel.qml"
)

ADDED_FILES=(
    "images/heater_bottom_bar.svg"
    "pages/HeaterPage.qml"
)

RESTORE_ONLY_FILES=(
    "Global.qml"
    "data/DataManager.qml"
)

restore_backup() {
    local target=$1
    local backup="${target}${BACKUP_SUFFIX}"

    if [ -f "$backup" ]; then
        mkdir -p "$(dirname "$target")"
        if [ ! -f "$target" ] || ! cmp -s "$backup" "$target"; then
            cp "$backup" "$target"
            FILES_CHANGED=1
        fi
    fi
}

remove_file() {
    local target=$1

    if [ -f "$target" ]; then
        rm -f "$target"
        FILES_CHANGED=1
    fi
}

restart_gui() {
    local service_path

    if [ -d "/service/gui" ]; then
        service_path="/service/gui"
    else
        service_path="/service/start-gui"
    fi

    svc -d "$service_path"
    sleep 1
    svc -u "$service_path"
    echo "Restarted GUI service."
}

for rel_path in "${PATCHED_FILES[@]}"; do
    restore_backup "$TARGET_ROOT/$rel_path"
done

for rel_path in "${RESTORE_ONLY_FILES[@]}"; do
    restore_backup "$TARGET_ROOT/$rel_path"
done

for rel_path in "${ADDED_FILES[@]}"; do
    remove_file "$TARGET_ROOT/$rel_path"
done

restore_backup "$CMAKE_FILE"

if [ "$FILES_CHANGED" -eq 1 ]; then
    echo "Removed native Autoterm heater GUI scaffold."
    restart_gui
fi

#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
APP_DIR="$ROOT_DIR/dbus-autoterm"
EXT_DIR="$APP_DIR/ext"
DIST_DIR="$ROOT_DIR/dist"
ARCHIVE="$DIST_DIR/dbus-autoterm.tar.gz"
VELIB_PYTHON_REF="${VELIB_PYTHON_REF:-master}"
PYSERIAL_REF="${PYSERIAL_REF:-v3.5}"
TMP_DIR=$(mktemp -d)

cleanup() {
    rm -rf "$TMP_DIR"
}

trap cleanup EXIT

if ! command -v curl >/dev/null 2>&1; then
    echo "Missing curl runtime" >&2
    exit 1
fi

if ! command -v tar >/dev/null 2>&1; then
    echo "Missing tar runtime" >&2
    exit 1
fi

download_archive() {
    url=$1
    destination=$2
    curl -fsSL "$url" -o "$destination"
}

extract_single_root() {
    archive=$1
    destination=$2
    mkdir -p "$destination"
    tar -xzf "$archive" -C "$destination"
}

install_dependency() {
    name=$1
    url=$2
    prefix=$3
    archive="$TMP_DIR/$name.tar.gz"

    download_archive "$url" "$archive"
    extract_single_root "$archive" "$TMP_DIR"

    source_root=$(find "$TMP_DIR" -maxdepth 1 -type d -name "$prefix" | head -n 1)
    if [ -z "$source_root" ] || [ ! -d "$source_root" ]; then
        echo "Failed to extract dependency '$name' from $url" >&2
        exit 1
    fi

    mkdir -p "$EXT_DIR/$name"
    cp -R "$source_root"/. "$EXT_DIR/$name/"
}

mkdir -p "$DIST_DIR"
rm -rf "$EXT_DIR"
mkdir -p "$EXT_DIR"

install_dependency \
    "velib_python" \
    "${VELIB_PYTHON_URL:-https://codeload.github.com/victronenergy/velib_python/tar.gz/refs/heads/$VELIB_PYTHON_REF}" \
    "velib_python-*"
install_dependency \
    "pyserial" \
    "${PYSERIAL_URL:-https://codeload.github.com/pyserial/pyserial/tar.gz/refs/tags/$PYSERIAL_REF}" \
    "pyserial-*"

rm -f "$ARCHIVE"
tar -C "$ROOT_DIR" \
    --exclude='dbus-autoterm/__pycache__' \
    --exclude='dbus-autoterm/tests' \
    --exclude='dbus-autoterm/*.pyc' \
    --exclude='dbus-autoterm/.DS_Store' \
    -czf "$ARCHIVE" \
    dbus-autoterm

echo "Created $ARCHIVE"

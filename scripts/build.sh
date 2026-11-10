#!/usr/bin/env bash
# Build an optimized onefile (or onedir) Mochi executable with PyInstaller.
# Strips unnecessary Qt bloat and applies UPX compression when available.
# Usage: scripts/build.sh [--onefile|--onedir]
set -euo pipefail
cd "$(dirname "$0")/.."

MODE="--onefile"
for arg in "$@"; do
    if [ "$arg" = "--onedir" ]; then
        MODE="--onedir"
    elif [ "$arg" = "--onefile" ]; then
        MODE="--onefile"
    fi
done

VENV=.venv-build
if [ ! -x "$VENV/bin/python" ]; then
    python3 -m venv "$VENV" || true
fi

# Fallback to current python if venv couldn't be created
PYTHON="python3"
if [ -x "$VENV/bin/python" ]; then
    PYTHON="$VENV/bin/python"
    "$PYTHON" -m pip install -q "PySide6-Essentials>=6.6" "psutil>=5.9" "pyinstaller>=6.6" || true
fi

UPX_FLAGS=()
if command -v upx >/dev/null 2>&1; then
    UPX_DIR="$(dirname "$(command -v upx)")"
    UPX_FLAGS=(
        "--upx-dir=$UPX_DIR"
        "--upx-exclude=vcruntime140.dll"
        "--upx-exclude=msvcp140.dll"
        "--upx-exclude=qwindows.dll"
    )
    echo "UPX compression enabled: using $UPX_DIR"
else
    echo "UPX not found: skipping UPX compression"
fi

DATA_ARGS=(
    --add-data "mochi/platform/kwin.js:mochi/platform"
)

EXCLUDES=(
    --exclude-module tkinter
    --exclude-module matplotlib
    --exclude-module numpy
    --exclude-module scipy
    --exclude-module unittest
    --exclude-module test
    --exclude-module PySide6.QtWebEngine
    --exclude-module PySide6.QtWebEngineCore
    --exclude-module PySide6.QtWebEngineWidgets
    --exclude-module PySide6.QtWebEngineQuick
    --exclude-module PySide6.QtQml
    --exclude-module PySide6.QtQuick
    --exclude-module PySide6.QtQuickWidgets
    --exclude-module PySide6.QtSql
    --exclude-module PySide6.QtNetwork
    --exclude-module PySide6.QtMultimedia
    --exclude-module PySide6.QtMultimediaWidgets
    --exclude-module PySide6.QtPdf
    --exclude-module PySide6.QtPdfWidgets
    --exclude-module PySide6.Qt3DCore
    --exclude-module PySide6.Qt3DRender
    --exclude-module PySide6.QtCharts
    --exclude-module PySide6.QtSensors
    --exclude-module PySide6.QtSpatialAudio
    --exclude-module PySide6.QtPositioning
    --exclude-module PySide6.QtLocation
)

echo "Building Mochi ($MODE)..."
"$PYTHON" -m PyInstaller --noconfirm --clean $MODE --name mochi \
    --paths . \
    "${DATA_ARGS[@]}" \
    "${UPX_FLAGS[@]}" \
    "${EXCLUDES[@]}" \
    packaging/entry.py

if [ "$MODE" = "--onefile" ]; then
    OUT="dist/mochi"
    [ -f "dist/mochi.exe" ] && OUT="dist/mochi.exe"
    echo "Successfully built onefile executable: $OUT ($(du -sh "$OUT" | cut -f1))"
else
    echo "Successfully built directory: dist/mochi/ ($(du -sh dist/mochi | cut -f1))"
fi

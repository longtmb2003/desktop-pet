#!/usr/bin/env bash
# Build a one-directory app into dist/mochi/ (the executable is dist/mochi/mochi).
# Uses a private venv (.venv-build) with PySide6 from PyPI so the bundle never picks up the distro's system Qt.
set -euo pipefail
cd "$(dirname "$0")/.."
VENV=.venv-build
[ -x "$VENV/bin/python" ] || python3 -m venv "$VENV"
"$VENV/bin/pip" install -q "PySide6-Essentials>=6.6" "psutil>=5.9" "pyinstaller>=6.6"   # Essentials = QtCore/Gui/Widgets/DBus, all Mochi uses

"$VENV/bin/python" -m PyInstaller --noconfirm --clean --onedir --name mochi \
    --paths . \
    --add-data "mochi/platform/kwin.js:mochi/platform" \
    --exclude-module tkinter \
    packaging/entry.py
echo "built: dist/mochi/mochi ($(du -sh dist/mochi | cut -f1))"

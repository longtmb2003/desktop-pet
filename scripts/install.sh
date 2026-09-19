#!/usr/bin/env bash
# Install the built app (dist/mochi) for the current user. No root needed. Usage: scripts/install.sh [--autostart]
set -euo pipefail
cd "$(dirname "$0")/.."
[ -x dist/mochi/mochi ] || { echo "dist/mochi/mochi not found: run scripts/build.sh first" >&2; exit 1; }

APP="$HOME/.local/opt/mochi"
BIN="$HOME/.local/bin/mochi"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}"

pkill -x mochi 2>/dev/null || true                            # a running copy would keep the old files open
rm -rf "$APP" && mkdir -p "$APP" "$(dirname "$BIN")" "$DATA/applications" "$DATA/icons/hicolor/256x256/apps"
cp -a dist/mochi/. "$APP"/
ln -sf "$APP/mochi" "$BIN"
cp packaging/mochi.png "$DATA/icons/hicolor/256x256/apps/mochi.png"
sed "s|@BIN@|\"$APP/mochi\"|" packaging/mochi.desktop > "$DATA/applications/mochi.desktop"

# an autostart entry from the old `python3 pet.py` setup would start a second, unpackaged copy
if [ -f "$CONF/autostart/mochi-pet.desktop" ]; then
    mv "$CONF/autostart/mochi-pet.desktop" "$CONF/autostart/mochi-pet.desktop.disabled"
    echo "disabled the old autostart entry (kept as mochi-pet.desktop.disabled)"
fi
command -v update-desktop-database >/dev/null && update-desktop-database "$DATA/applications" 2>/dev/null || true
command -v kbuildsycoca6 >/dev/null && kbuildsycoca6 >/dev/null 2>&1 || true

[ "${1:-}" = "--autostart" ] && "$APP/mochi" autostart on
echo "installed: $BIN   (start it from the app menu, or run: mochi)"
echo "autostart at login:  mochi autostart on | off | status"

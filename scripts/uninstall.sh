#!/usr/bin/env bash
# Remove everything scripts/install.sh added, plus the autostart entry. Usage: scripts/uninstall.sh [--purge]  (--purge also deletes saved settings)
set -euo pipefail
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}"

pkill -x mochi 2>/dev/null || true
rm -rf "$HOME/.local/opt/mochi"
rm -f "$HOME/.local/bin/mochi" "$DATA/applications/mochi.desktop" "$DATA/icons/hicolor/256x256/apps/mochi.png" "$CONF/autostart/mochi.desktop"
command -v update-desktop-database >/dev/null && update-desktop-database "$DATA/applications" 2>/dev/null || true
if [ "${1:-}" = "--purge" ]; then rm -rf "$CONF/mochi-pet"; echo "removed saved settings"; fi
echo "mochi removed"

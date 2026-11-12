#!/usr/bin/env bash
# Install the built app (dist/mochi) for the current user. No root needed. Usage: scripts/install.sh [--autostart]
set -euo pipefail
cd "$(dirname "$0")/.."

# Check if already built, or if source files are newer than built binary
REBUILD=0
if [ ! -f dist/mochi ] && [ ! -x dist/mochi/mochi ]; then
    echo "dist/mochi not found. Running scripts/build.sh..."
    REBUILD=1
elif [ -f dist/mochi ]; then
    NEWEST_SRC=$(find mochi packaging -type f -name "*.py" -newer dist/mochi 2>/dev/null | head -n 1 || true)
    if [ -n "$NEWEST_SRC" ]; then
        echo ">>> Mã nguồn mới hơn dist/mochi ($NEWEST_SRC). Đang tự động build lại..."
        REBUILD=1
    fi
fi

if [ "$REBUILD" -eq 1 ]; then
    scripts/build.sh --onefile
fi

# Check for Qt6 xcb runtime dependency on Linux (libxcb-cursor0, libxkbcommon-x11-0)
check_xcb() {
    (ldconfig -p 2>/dev/null || /sbin/ldconfig -p 2>/dev/null) | grep -q "libxcb-cursor.so.0" || \
    [ -f /usr/lib/x86_64-linux-gnu/libxcb-cursor.so.0 ] || \
    [ -f /usr/lib64/libxcb-cursor.so.0 ] || \
    [ -f /usr/lib/libxcb-cursor.so.0 ] || \
    [ -f /usr/lib/aarch64-linux-gnu/libxcb-cursor.so.0 ]
}

if ! check_xcb; then
    echo ">>> [!] Thiếu thư viện hệ thống 'libxcb-cursor0' (bắt buộc cho Qt6 xcb plugin)."
    if command -v apt-get >/dev/null 2>&1; then
        echo ">>> Đang tự động cài đặt qua apt (có thể cần mật khẩu sudo):"
        if [ -c /dev/tty ]; then
            sudo </dev/tty apt-get update -qq 2>/dev/null || true
            sudo </dev/tty apt-get install -y libxcb-cursor0 libxkbcommon-x11-0 2>/dev/null || true
        else
            sudo apt-get update -qq 2>/dev/null || true
            sudo apt-get install -y libxcb-cursor0 libxkbcommon-x11-0 2>/dev/null || true
        fi
    fi
    if ! check_xcb; then
        echo ">>> Vui lòng tự cài đặt bằng lệnh: sudo apt update && sudo apt install -y libxcb-cursor0 libxkbcommon-x11-0" >&2
    fi
fi

APP="$HOME/.local/opt/mochi"
BIN="$HOME/.local/bin/mochi"
DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
CONF="${XDG_CONFIG_HOME:-$HOME/.config}"

pkill -x mochi 2>/dev/null || true                            # a running copy would keep the old files open
rm -rf "$APP" && mkdir -p "$APP" "$(dirname "$BIN")" "$DATA/applications" "$DATA/icons/hicolor/256x256/apps"

# Handle both onefile (dist/mochi file) and onedir (dist/mochi/ directory)
if [ -f dist/mochi ] && [ -x dist/mochi ]; then
    cp -a dist/mochi "$APP/mochi"
elif [ -x dist/mochi/mochi ]; then
    cp -a dist/mochi/. "$APP"/
else
    echo "Error: Could not locate built mochi binary in dist/" >&2
    exit 1
fi

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
echo "installed: $BIN   (start it from the app menu, or run in background: mochi -d)"
echo "autostart at login:  mochi autostart on | off | status"

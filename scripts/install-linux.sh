#!/usr/bin/env bash
# Linux 1-liner installer & runner for Mochi
# Usage: curl -fsSL https://raw.githubusercontent.com/longtmb2003/desktop-pet/main/scripts/install-linux.sh | bash
set -euo pipefail

APP_DIR="$HOME/.local/bin"
BIN="$APP_DIR/mochi"
URL="https://github.com/longtmb2003/desktop-pet/releases/latest/download/mochi-linux-x86_64"
FALLBACK_URL="https://github.com/longtmb2003/desktop-pet/releases/latest/download/mochi.AppImage"

echo ">>> Đang tải Mochi cho Linux từ GitHub Releases..."
pkill -x mochi 2>/dev/null || true
mkdir -p "$APP_DIR"

if ! curl -fL -o "$BIN" "$URL" 2>/dev/null && ! curl -fL -o "$BIN" "$FALLBACK_URL" 2>/dev/null; then
    echo ">>> [!] Chưa tìm thấy file release trên GitHub Releases."
    echo ">>>     (Nếu bạn vừa push tag, GitHub Actions đang chạy build tự động trên đám mây, mất khoảng 2-4 phút)."
    echo ">>>     Xem tiến trình build tại: https://github.com/longtmb2003/desktop-pet/actions"

    # Fallback to local desktop-pet if present
    for candidate in "$PWD/desktop-pet" "$HOME/IdeaProjects/desktop-pet" "$HOME/desktop-pet"; do
        if [ -d "$candidate" ]; then
            echo ">>> Tìm thấy mã nguồn tại: $candidate. Tiến hành cài đặt ngay từ máy cục bộ..."
            bash "$candidate/scripts/install.sh" --autostart
            exit 0
        fi
    done
    echo ">>> Vui lòng đợi GitHub Actions build xong hoặc tự cài từ source: cd desktop-pet && scripts/install.sh --autostart" >&2
    exit 1
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
    if command -v apt-get >/dev/null 2>&1; then
        echo ">>> [!] Đang cài đặt thư viện cần thiết 'libxcb-cursor0' (bắt buộc cho Qt6)..."
        if [ -c /dev/tty ]; then
            sudo </dev/tty apt-get update -qq 2>/dev/null || true
            sudo </dev/tty apt-get install -y libxcb-cursor0 libxkbcommon-x11-0 2>/dev/null || true
        else
            sudo apt-get update -qq 2>/dev/null || true
            sudo apt-get install -y libxcb-cursor0 libxkbcommon-x11-0 2>/dev/null || true
        fi
    fi
    if ! check_xcb; then
        echo ">>> [!] CẢNH BÁO: Chưa cài đặt được thư viện 'libxcb-cursor0'." >&2
        echo ">>>     Nếu Mochi không hiển thị, vui lòng chạy lệnh sau trên terminal:" >&2
        echo ">>>       sudo apt update && sudo apt install -y libxcb-cursor0 libxkbcommon-x11-0" >&2
    fi
fi

chmod +x "$BIN"

# Check if the binary can run on this system (detect glibc / dynamic linking errors)
if ! "$BIN" --version >/dev/null 2>&1; then
    echo ">>> [!] File nhị phân tải về không tương thích với môi trường Linux hiện tại (GLIBC/thư viện hệ thống)."
    for candidate in "$PWD/desktop-pet" "$HOME/IdeaProjects/desktop-pet" "$HOME/desktop-pet"; do
        if [ -d "$candidate" ]; then
            echo ">>> Tìm thấy mã nguồn tại: $candidate. Đang tự động build và cài đặt trực tiếp trên máy của bạn..."
            bash "$candidate/scripts/install.sh" --autostart
            echo ">>> Đang khởi chạy Mochi ngầm trong tiến trình (daemon)..."
            "$BIN" -d || nohup "$BIN" >/dev/null 2>&1 &
            exit 0
        fi
    done
    echo ">>> Bạn có thể tự clone và cài đặt từ source:" >&2
    echo ">>>   git clone https://github.com/longtmb2003/desktop-pet.git" >&2
    echo ">>>   cd desktop-pet && ./scripts/install.sh --autostart" >&2
    exit 1
fi

DATA="${XDG_DATA_HOME:-$HOME/.local/share}"
mkdir -p "$DATA/applications" "$DATA/icons/hicolor/256x256/apps"
ICON="$DATA/icons/hicolor/256x256/apps/mochi.png"
if [ ! -f "$ICON" ]; then
    curl -fsSL "https://raw.githubusercontent.com/longtmb2003/desktop-pet/main/packaging/mochi.png" -o "$ICON" 2>/dev/null || true
fi
cat << 'EOF' > "$DATA/applications/mochi.desktop"
[Desktop Entry]
Type=Application
Name=Mochi
Comment=A tiny vector desktop pet
Exec=mochi
Icon=mochi
Terminal=false
Categories=Utility;Amusement;
EOF
command -v update-desktop-database >/dev/null && update-desktop-database "$DATA/applications" 2>/dev/null || true

echo ">>> Đã cài đặt thành công tại: $BIN"
echo ">>> Đang khởi chạy Mochi ngầm trong tiến trình (daemon)..."
"$BIN" -d || nohup "$BIN" >/dev/null 2>&1 &

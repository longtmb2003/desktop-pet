#!/usr/bin/env bash
# Linux 1-liner installer & runner for Mochi
# Usage: curl -fsSL https://raw.githubusercontent.com/longtmb2003/desktop-pet/main/scripts/install-linux.sh | bash
set -euo pipefail

APP_DIR="$HOME/.local/bin"
BIN="$APP_DIR/mochi"
URL="https://github.com/longtmb2003/desktop-pet/releases/latest/download/mochi.AppImage"

echo ">>> Đang tải Mochi cho Linux từ GitHub Releases..."
mkdir -p "$APP_DIR"

if ! curl -fL -o "$BIN" "$URL" 2>/dev/null; then
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

# Check for Qt6 xcb runtime dependency on Linux (libxcb-cursor0)
if ! (ldconfig -p 2>/dev/null || /sbin/ldconfig -p 2>/dev/null) | grep -q "libxcb-cursor.so.0"; then
    if [ ! -f /usr/lib/x86_64-linux-gnu/libxcb-cursor.so.0 ] && [ ! -f /usr/lib64/libxcb-cursor.so.0 ] && [ ! -f /usr/lib/libxcb-cursor.so.0 ]; then
        if command -v apt-get >/dev/null 2>&1; then
            echo ">>> [!] Đang cài đặt thư viện cần thiết 'libxcb-cursor0'..."
            sudo apt-get update -qq && sudo apt-get install -y libxcb-cursor0 || true
        fi
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
            echo ">>> Đang khởi chạy Mochi..."
            "$BIN" &
            exit 0
        fi
    done
    echo ">>> Bạn có thể tự clone và cài đặt từ source:" >&2
    echo ">>>   git clone https://github.com/longtmb2003/desktop-pet.git" >&2
    echo ">>>   cd desktop-pet && ./scripts/install.sh --autostart" >&2
    exit 1
fi

echo ">>> Đã cài đặt thành công tại: $BIN"
echo ">>> Đang khởi chạy Mochi..."
"$BIN" &

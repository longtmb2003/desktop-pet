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

chmod +x "$BIN"
echo ">>> Đã cài đặt thành công tại: $BIN"
echo ">>> Đang khởi chạy Mochi..."
"$BIN" &

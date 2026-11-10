#!/usr/bin/env bash
# Linux 1-liner installer & runner for Mochi
# Usage: curl -fsSL https://raw.githubusercontent.com/longtmb2003/desktop-pet/main/scripts/install-linux.sh | bash
set -euo pipefail

APP_DIR="$HOME/.local/bin"
BIN="$APP_DIR/mochi"
URL="https://github.com/longtmb2003/desktop-pet/releases/latest/download/mochi.AppImage"

echo ">>> Đang tải Mochi cho Linux..."
mkdir -p "$APP_DIR"
curl -fsSL -o "$BIN" "$URL"
chmod +x "$BIN"

echo ">>> Đã cài đặt thành công tại: $BIN"
echo ">>> Đang khởi chạy Mochi..."
"$BIN" &

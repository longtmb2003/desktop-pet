#!/usr/bin/env bash
# macOS 1-liner installer & runner for Mochi
# Usage: curl -fsSL https://raw.githubusercontent.com/longtmb2003/desktop-pet/main/scripts/install-mac.sh | bash
set -euo pipefail

URL="https://github.com/longtmb2003/desktop-pet/releases/latest/download/mochi.dmg"
DMG="/tmp/mochi.dmg"

echo ">>> Đang tải Mochi cho macOS..."
curl -fsSL -o "$DMG" "$URL"

echo ">>> Đang cài đặt vào /Applications..."
MOUNT_DIR=$(hdiutil attach "$DMG" -nobrowse -readonly | grep '/Volumes/' | awk '{print $3}')
cp -R "$MOUNT_DIR/Mochi.app" /Applications/
hdiutil detach "$MOUNT_DIR" -quiet || true
rm -f "$DMG"

echo ">>> Đã cài đặt thành công tại: /Applications/Mochi.app"
echo ">>> Đang khởi chạy Mochi..."
open /Applications/Mochi.app

# Windows 1-liner installer & runner for Mochi
# Usage: irm https://raw.githubusercontent.com/longtmb2003/desktop-pet/main/scripts/install.ps1 | iex
$ErrorActionPreference = "Stop"
$InstallDir = "$env:LOCALAPPDATA\Programs\Mochi"
$Bin = "$InstallDir\mochi.exe"
$Url = "https://github.com/longtmb2003/desktop-pet/releases/latest/download/mochi.exe"

Write-Host ">>> Đang tải Mochi cho Windows từ GitHub Releases..." -ForegroundColor Cyan
Stop-Process -Name "mochi" -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null

try {
    Invoke-WebRequest -Uri $Url -OutFile $Bin
} catch {
    Write-Host ">>> [!] Chưa tìm thấy file release trên GitHub Releases." -ForegroundColor Yellow
    Write-Host ">>>     (Nếu bạn vừa push tag, GitHub Actions đang chạy build tự động trên đám mây, mất khoảng 2-4 phút)." -ForegroundColor Yellow
    Write-Host ">>>     Xem tiến trình build tại: https://github.com/longtmb2003/desktop-pet/actions" -ForegroundColor Yellow
    exit 1
}

# Setup startup shortcut (tuỳ chọn)
$StartupDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$StartupDir\Mochi.lnk")
$Shortcut.TargetPath = $Bin
$Shortcut.Save()

Write-Host ">>> Đã cài đặt thành công tại: $Bin" -ForegroundColor Green
Write-Host ">>> Đang khởi chạy Mochi..." -ForegroundColor Cyan
Start-Process -FilePath $Bin

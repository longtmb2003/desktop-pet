# Windows 1-liner installer & runner for Mochi
# Usage: irm https://raw.githubusercontent.com/longtmb2003/desktop-pet/main/scripts/install.ps1 | iex
$ErrorActionPreference = "Stop"
$InstallDir = "$env:LOCALAPPDATA\Programs\Mochi"
$Bin = "$InstallDir\mochi.exe"
$Url = "https://github.com/longtmb2003/desktop-pet/releases/latest/download/mochi.exe"

Write-Host ">>> Đang tải Mochi cho Windows..." -ForegroundColor Cyan
New-Item -ItemType Directory -Force -Path $InstallDir | Out-Null
Invoke-WebRequest -Uri $Url -OutFile $Bin

# Setup startup shortcut (tuỳ chọn)
$StartupDir = "$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup"
$WshShell = New-Object -ComObject WScript.Shell
$Shortcut = $WshShell.CreateShortcut("$StartupDir\Mochi.lnk")
$Shortcut.TargetPath = $Bin
$Shortcut.Save()

Write-Host ">>> Đã cài đặt thành công tại: $Bin" -ForegroundColor Green
Write-Host ">>> Đang khởi chạy Mochi..." -ForegroundColor Cyan
Start-Process -FilePath $Bin

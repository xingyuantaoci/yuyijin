# ============================================================
# 妖股竞价选股器 APK 构建（Windows 侧辅助脚本）
# 前提: 已安装 WSL2 + Ubuntu（见 README.md 或执行:
#        wsl --install -d Ubuntu-22.04   后重启）
# 用法:  PowerShell 运行  .\build_apk.ps1
# 产物:  .\bin\yaostock-1.0.0-arm64-v8a_debug.apk
# ============================================================
$ErrorActionPreference = "Stop"
$Project = Split-Path -Parent $MyInvocation.MyCommand.Path
$WinPath = $Project.Replace("\", "/").Replace("C:", "/mnt/c")

Write-Host "==> 检查 WSL..." -ForegroundColor Cyan
$wsl = Get-Command wsl.exe -ErrorAction SilentlyContinue
if (-not $wsl) {
    Write-Host "WSL 未安装！请以管理员 PowerShell 执行:  wsl --install -d Ubuntu-22.04  然后重启电脑，再运行本脚本。" -ForegroundColor Red
    exit 1
}

Write-Host "==> 复制工程到 WSL (~/yaostock) ..." -ForegroundColor Cyan
wsl bash -lc "mkdir -p ~/yaostock && cp -r $WinPath/* ~/yaostock/ && cd ~/yaostock && bash build_apk.sh"

Write-Host "==> 拷贝 APK 回 Windows ..." -ForegroundColor Cyan
wsl bash -lc "cp ~/yaostock/bin/*.apk /mnt/c/Users/Administrator/Doubao/chats/2026-09-12/new-chat/yaostock/bin/ 2>/dev/null || true"

if (Test-Path "$Project\bin\*.apk") {
    Write-Host "==> 构建成功！APK 位于: $Project\bin\" -ForegroundColor Green
    Get-ChildItem "$Project\bin\*.apk" | Select-Object Name, @{N="SizeMB";E={[math]::Round($_.Length/1MB,1)}}
} else {
    Write-Host "==> 未找到 APK，请查看上方 WSL 日志定位错误。" -ForegroundColor Yellow
}

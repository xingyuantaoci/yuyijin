#!/usr/bin/env bash
# ============================================================
# 妖股竞价选股器 APK 构建脚本（Linux / WSL2 Ubuntu）
# 用法:  bash build_apk.sh
# 首次运行会安装 buildozer 等工具，随后开始打包（约 40~90 分钟，
# 首次需下载 Android SDK/NDK 约 5GB）。
# 产物:  bin/yaostock-1.0.0-arm64-v8a_debug.apk
# ============================================================
set -e
cd "$(dirname "$0")"

echo "==> 检查必要系统包..."
for pkg in git zip unzip openjdk-17-jdk autoconf libtool pkg-config \
           zlib1g-dev libncurses-dev libssl-dev automake cmake \
           libffi-dev liblzma-dev build-essential; do
    dpkg -s "$pkg" >/dev/null 2>&1 || MISSING="$MISSING $pkg"
done
if [ -n "$MISSING" ]; then
    echo "==> 安装缺失系统包:$MISSING"
    sudo apt update
    sudo apt install -y $MISSING
fi

echo "==> 安装 buildozer + cython（固定版本）..."
pip3 install --user buildozer==1.5.0 cython==0.29.36 virtualenv 2>/dev/null || \
pip3 install --break-system-packages --user buildozer==1.5.0 cython==0.29.36 virtualenv

export PATH="$PATH:$HOME/.local/bin"

echo "==> 开始打包（首次下载 SDK/NDK 约 5GB，耐心等待）..."
buildozer android debug

echo "==> 完成，产物:"
ls -lh bin/*.apk

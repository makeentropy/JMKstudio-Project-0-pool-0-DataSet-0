#!/bin/bash
#
# VSCode IDE 安装脚本
#
# 此脚本用于在Debian/Ubuntu系统上安装Visual Studio Code
#

set -e

echo "=========================================="
echo "   VSCode IDE 安装脚本"
echo "=========================================="

echo ""
echo "[1/7] 更新系统软件包..."
sudo apt-get update -y

echo ""
echo "[2/7] 安装依赖工具..."
sudo apt-get install -y wget gpg

echo ""
echo "[3/7] 下载微软签名密钥..."
wget -qO- https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor > packages.microsoft.gpg

echo ""
echo "[4/7] 安装签名密钥..."
sudo install -D -o root -g root -m 644 packages.microsoft.gpg /etc/apt/keyrings/packages.microsoft.gpg

echo ""
echo "[5/7] 添加VSCode软件源..."
echo "deb [arch=amd64,arm64,armhf signed-by=/etc/apt/keyrings/packages.microsoft.gpg] https://packages.microsoft.com/repos/code stable main" | sudo tee /etc/apt/sources.list.d/vscode.list > /dev/null

echo ""
echo "[6/7] 清理临时文件..."
rm -f packages.microsoft.gpg

echo ""
echo "[7/7] 安装 VSCode..."
sudo apt-get update -y
sudo apt-get install -y code

echo ""
echo "=========================================="
echo "   VSCode IDE 安装完成!"
echo "=========================================="
echo ""
echo "可以通过以下命令验证安装:"
echo "  code --version"
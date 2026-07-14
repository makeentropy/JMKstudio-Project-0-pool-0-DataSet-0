#!/bin/bash
#
# Kali Linux Full 安装脚本
#
# 此脚本用于在Debian/Ubuntu系统上安装Kali Linux Full发行版
#

set -e

echo "=========================================="
echo "   Kali Linux Full 安装脚本"
echo "=========================================="

echo ""
echo "[1/3] 更新系统软件包..."
sudo apt-get update -y

echo ""
echo "[2/3] 升级系统..."
sudo apt-get upgrade -y

echo ""
echo "[3/3] 安装 Kali Linux Full..."
sudo apt-get install -y kali-linux-full

echo ""
echo "=========================================="
echo "   Kali Linux Full 安装完成!"
echo "=========================================="
echo ""
echo "可以通过以下命令验证安装:"
echo "  dpkg -l | grep -i kali-linux-full"
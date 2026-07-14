#!/bin/bash
#
# Jupyter Notebook/Lab 安装脚本
#
# 此脚本用于在Debian/Ubuntu系统上安装Jupyter Notebook和JupyterLab
#

set -e

# 默认配置
JUPYTER_PORT="${JUPYTER_PORT:-8888}"
JUPYTER_DIR="${JUPYTER_DIR:-~/notebooks}"
JUPYTER_PASSWORD="${JUPYTER_PASSWORD:-}"

echo "=========================================="
echo "   Jupyter Notebook/Lab 安装脚本"
echo "=========================================="

echo ""
echo "[1/4] 更新系统软件包..."
sudo apt-get update -y

echo ""
echo "[2/4] 安装Python和pip..."
sudo apt-get install -y python3-pip python3-dev

echo ""
echo "[3/4] 升级pip并安装Jupyter..."
sudo pip3 install --upgrade pip
sudo pip3 install jupyter jupyterlab

echo ""
echo "[4/4] 配置Jupyter..."

# 创建工作目录
mkdir -p "$JUPYTER_DIR"

# 生成配置文件
if [ ! -f ~/.jupyter/jupyter_notebook_config.py ]; then
    jupyter notebook --generate-config
fi

# 设置端口
echo "c.NotebookApp.port = $JUPYTER_PORT" >> ~/.jupyter/jupyter_notebook_config.py

# 设置工作目录
echo "c.NotebookApp.notebook_dir = '$JUPYTER_DIR'" >> ~/.jupyter/jupyter_notebook_config.py

# 允许远程访问
echo "c.NotebookApp.ip = '0.0.0.0'" >> ~/.jupyter/jupyter_notebook_config.py
echo "c.NotebookApp.allow_remote_access = True" >> ~/.jupyter/jupyter_notebook_config.py

# 设置密码（如果提供）
if [ -n "$JUPYTER_PASSWORD" ]; then
    HASHED_PASSWORD=$(python3 -c "from jupyter_server.auth import passwd; print(passwd('$JUPYTER_PASSWORD'))")
    echo "c.NotebookApp.password = '$HASHED_PASSWORD'" >> ~/.jupyter/jupyter_notebook_config.py
    echo "  - 密码已设置"
fi

echo ""
echo "=========================================="
echo "   Jupyter Notebook/Lab 安装完成!"
echo "=========================================="
echo ""
echo "配置信息:"
echo "  - 端口: $JUPYTER_PORT"
echo "  - 工作目录: $JUPYTER_DIR"
echo ""
echo "可以通过以下命令验证安装:"
echo "  jupyter notebook --version"
echo "  jupyter lab --version"
echo ""
echo "启动Jupyter Notebook:"
echo "  jupyter notebook"
echo ""
echo "启动JupyterLab:"
echo "  jupyter lab"
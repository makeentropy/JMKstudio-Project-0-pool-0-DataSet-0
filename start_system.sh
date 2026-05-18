#!/bin/bash
# 超弦奇点量子系统启动脚本

echo "=========================================="
echo "  超弦奇点量子系统 - Superstring Singularity"
echo "=========================================="
echo ""

# 检查Python
python3 --version > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "错误: 未找到Python 3"
    exit 1
fi

# 创建必要的目录
mkdir -p data/pool-0
mkdir -p data/certificates
mkdir -p data/visualizations
mkdir -p data/gnupg

# 检查依赖
echo "检查依赖..."
python3 -c "import flask" > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "安装依赖..."
    pip install -r requirements.txt
fi

echo ""
echo "可用的启动选项:"
echo "  1) 启动Web终端"
echo "  2) 启动Jupyter Notebook"
echo "  3) 同时启动Web终端和Jupyter"
echo "  4) 仅安装依赖"
echo ""
read -p "请选择 (1-4): " choice

case $choice in
    1)
        echo "启动Web终端..."
        python3 -m src.web_terminal.app
        ;;
    2)
        echo "启动Jupyter Notebook..."
        jupyter notebook superstring_singularity_quantum.ipynb
        ;;
    3)
        echo "同时启动Web终端和Jupyter..."
        python3 -m src.web_terminal.app &
        WEB_PID=$!
        sleep 2
        jupyter notebook superstring_singularity_quantum.ipynb &
        JUPYTER_PID=$!
        
        echo ""
        echo "Web终端: http://localhost:5000"
        echo "Jupyter: http://localhost:8888"
        echo ""
        echo "按Ctrl+C停止"
        wait $WEB_PID $JUPYTER_PID
        ;;
    4)
        echo "安装依赖..."
        pip install -r requirements.txt
        echo "依赖安装完成"
        ;;
    *)
        echo "无效选择"
        ;;
esac

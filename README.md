# 超弦奇点量子系统 - Superstring Singularity Quantum System

## 简介

这是一个集成了GPG加密、CA证书管理、Web终端、数据处理、拓扑搜索和Hugging Face集成的综合系统。

## 功能特性

1. **GPG加密与CA服务器** - 安全的密钥管理和证书颁发
2. **Web终端** - 基于Flask和XTerm的交互式终端界面
3. **数据池管理** - 数据集管理、搜索、打包
4. **数据处理** - 数据清洗、分析、特征工程
5. **数据可视化** - 图表、热力图、仪表板生成
6. **拓扑维度空间搜索** - 11维空间中的向量相似度搜索
7. **插件系统** - CA管理和Hugging Face集成插件
8. **Hugging Face集成** - 文本分类、生成、分词等NLP功能

## 项目结构

```
/workspace/
├── src/
│   ├── gpg_ca/              # GPG加密与CA服务器
│   ├── web_terminal/        # Web终端应用
│   ├── data_processing/     # 数据处理模块
│   ├── topology/            # 拓扑搜索引擎
│   └── plugins/             # 插件系统
├── data/                    # 数据存储目录
├── templates/               # HTML模板
├── static/                  # 静态文件
├── requirements.txt         # Python依赖
├── start_system.sh          # 启动脚本
└── superstring_singularity_quantum.ipynb  # 主Jupyter Notebook
```

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
```

或者使用启动脚本：

```bash
chmod +x start_system.sh
./start_system.sh  # 选择选项4安装依赖
```

### 2. 启动系统

```bash
./start_system.sh
```

选择以下选项之一：
- 1) 启动Web终端（访问 http://localhost:5000）
- 2) 启动Jupyter Notebook
- 3) 同时启动Web终端和Jupyter

### 3. 使用Jupyter Notebook

```bash
jupyter notebook superstring_singularity_quantum.ipynb
```

## 主要模块使用说明

### GPG与CA服务器

```python
from src.gpg_ca import GPGManager, CAServer

# 初始化
gpg = GPGManager()
ca = CAServer()

# 生成密钥对
result = gpg.generate_key("User", "user@example.com", "password")
```

### 数据池

```python
from src.data_processing import DataPool

pool = DataPool()
dataset = pool.create_dataset("测试数据", tags=["量子"])
pool.add_file(dataset['id'], "data.csv")
```

### 拓扑搜索

```python
from src.topology import TopologySearchEngine

engine = TopologySearchEngine(dimensions=11)
engine.add_node("node1", data, dimensions=[...])
results = engine.search_by_vector(query_vector)
```

## 要求

- Python 3.7+
- Flask
- pandas, numpy
- scikit-learn
- matplotlib, seaborn
- transformers (可选，用于Hugging Face功能)
- python-gnupg
- Flask-SocketIO

## 许可证

MIT License


# JMKstudio-Project-0-pool-0-DataSet-0

Agent训练数据收集与预处理项目。

## 项目简介

本项目提供了一套完整的工具链，用于：
- 从网页收集数据
- 清洗和处理数据
- 生成训练数据集
- 训练Agent智能体

## 目录结构

```
/workspace/
├── data/
│   ├── raw/              # 原始数据
│   ├── processed/        # 处理后的数据
│   └── datasets/         # 最终数据集
├── src/
│   ├── collector/        # 数据收集模块
│   ├── processor/        # 数据处理模块
│   └── trainer/          # 训练模块
├── scripts/              # 工具脚本
├── requirements.txt      # 依赖包
└── README.md
```

## 安装依赖

```bash
pip install -r requirements.txt
```

## 快速开始

### 方式一：运行完整流程

```bash
python scripts/full_pipeline.py
```

### 方式二：分步执行

1. 收集数据：
```bash
python scripts/collect_data.py
```

2. 处理数据：
```bash
python scripts/process_data.py
```

3. 训练Agent：
```bash
python scripts/train_agent.py
```

## 模块说明

### 数据收集模块 (src/collector)

- `WebScraper`: 网页内容抓取器
- `DataSaver`: 数据保存工具

### 数据处理模块 (src/processor)

- `DataCleaner`: 数据清洗工具
- `DataFormatter`: 数据格式化工具

### Agent训练模块 (src/trainer)

- `AgentTrainer`: Agent训练器
- `ModelManager`: 模型管理工具

## 数据来源

- 豆包: https://www.doubao.com/thread/a675c7aea46f3

## 许可证

MIT License

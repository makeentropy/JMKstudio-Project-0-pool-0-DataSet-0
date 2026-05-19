# Agent History Dataset - 使用文档

## 目录

- [项目简介](#项目简介)
- [功能特性](#功能特性)
- [核心模块](#核心模块)
- [工作流程](#工作流程)
- [配置说明](#配置说明)
- [示例代码](#示例代码)
- [常见问题](#常见问题)

## 项目简介

Agent History Dataset 是一个用于生成和管理 AI 智能体交互历史数据集的完整流水线工具。它提供了从数据收集、清洗、标注到最终数据集生成的全流程解决方案。

## 功能特性

- **数据收集**: 支持多种数据源格式（JSON、CSV），提供 SDK 和 API 接口
- **数据清洗**: 自动去重、敏感信息脱敏、文本归一化、质量评估
- **数据标注**: 支持半自动标注和人工标注，内置多种标签分类
- **数据生成**: 支持多种导出格式（JSONL、Parquet、Alpaca、LLaMA），可选数据增强
- **质量控制**: 全面的质量检查和统计功能

## 核心模块

### 1. 数据收集模块 (`collector`)

负责从各种来源收集智能体交互数据。

主要组件：
- `FileCollector`: 从文件收集数据（JSON、CSV）
- `APICollector`: 通过 API 收集数据
- `StorageManager`: 数据存储和加载管理
- `DataCollectorSDK`: 便捷的 SDK 接口

### 2. 数据清洗模块 (`cleaner`)

负责清洗和预处理收集到的数据。

主要组件：
- `Deduplicator`: 数据去重
- `Sanitizer`: 敏感信息脱敏
- `Normalizer`: 文本归一化
- `QualityChecker`: 质量评估
- `CleaningPipeline`: 清洗流水线

### 3. 数据标注模块 (`annotator`)

负责对交互数据进行标注。

主要组件：
- `SemiAutoAnnotator`: 半自动标注器
- `ManualAnnotator`: 人工标注器
- `LabelManager`: 标签管理
- `QualityChecker`: 标注质量检查
- `AnnotationStorage`: 标注数据存储

### 4. 数据生成模块 (`generator`)

负责生成最终的训练数据集。

主要组件：
- `DataFormatter`: 数据格式化
- `DataSplitter`: 数据集划分
- `TextAugmenter`: 数据增强
- `DataExporter`: 数据导出
- `DatasetGenerationPipeline`: 完整生成流水线

## 工作流程

完整的数据集生成流程如下：

```
数据收集 → 数据清洗 → 数据标注 → 数据集生成
   ↓          ↓          ↓           ↓
  源文件    清洗后    标注数据    最终数据集
```

## 配置说明

配置文件位于 `config/config.py`，主要配置项包括：

- 数据目录路径
- 数据集划分比例
- 标注标签定义
- 清洗参数设置

## 示例代码

查看 `examples/` 目录下的示例代码：

- `collector_example.py`: 数据收集示例
- `cleaning_example.py`: 数据清洗示例
- `annotation_example.py`: 数据标注示例
- `generator_example.py`: 数据生成示例
- `end_to_end.py`: 端到端完整示例

## 常见问题

### 如何添加自定义标签？

使用 `LabelManager` 的 `add_custom_label()` 方法添加自定义标签。

### 支持哪些导出格式？

支持 JSONL、Parquet、Alpaca 和 LLaMA 格式。

### 如何启用数据增强？

在 `DatasetGenerationPipeline` 初始化时设置 `enable_augmentation=True`。

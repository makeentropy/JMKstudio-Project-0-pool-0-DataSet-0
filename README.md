# Agent History Dataset

一个用于生成和管理 AI 智能体交互历史数据集的完整流水线工具。

## 功能特性

- **数据收集**: 支持从 JSON、CSV 等多种格式收集智能体交互数据
- **数据清洗**: 自动去重、敏感信息脱敏、文本归一化和质量评估
- **数据标注**: 支持半自动标注和人工标注，内置多种标签分类
- **数据生成**: 支持多种导出格式（JSONL、Parquet、Alpaca、LLaMA），可选数据增强
- **质量控制**: 全面的质量检查和统计功能

## 快速开始

### 安装

```bash
pip install -e .
```

### 5 分钟上手

```python
from src.collector import FileCollector, StorageManager
from src.cleaner import CleaningPipeline
from src.annotator import SemiAutoAnnotator, AnnotationStorage
from src.generator import DatasetGenerationPipeline, ExportFormat

# 1. 收集数据
collector = FileCollector("data.json", format_type="json")
interactions = collector.collect()

# 2. 清洗数据
cleaner = CleaningPipeline()
cleaned_data = cleaner.process(interactions)

# 3. 标注数据
annotator = SemiAutoAnnotator()
annotated_data = annotator.annotate_batch(cleaned_data)

# 4. 生成数据集
generator = DatasetGenerationPipeline(export_format=ExportFormat.JSONL)
result = generator.run()
```

### 运行端到端示例

```bash
python examples/end_to_end.py
```

## 文档

- [快速开始指南](docs/quickstart.md) - 5 分钟快速上手
- [使用文档](docs/README.md) - 详细的功能介绍和使用说明
- [API 文档](docs/api.md) - 完整的 API 接口文档

## 项目结构

```
.
├── src/                    # 源代码目录
│   ├── collector/         # 数据收集模块
│   ├── cleaner/           # 数据清洗模块
│   ├── annotator/         # 数据标注模块
│   ├── generator/         # 数据生成模块
│   └── manager/           # 数据管理模块
├── config/                # 配置文件目录
├── data/                  # 数据目录
│   ├── raw/              # 原始数据
│   ├── processed/        # 处理后数据
│   ├── annotated/        # 标注后数据
│   └── final/            # 最终数据集
├── examples/              # 示例代码目录
│   ├── end_to_end.py     # 端到端完整示例
│   ├── collector_example.py
│   ├── cleaning_example.py
│   ├── annotation_example.py
│   └── generator_example.py
└── docs/                  # 文档目录
    ├── README.md         # 使用文档
    ├── quickstart.md     # 快速开始指南
    └── api.md            # API 文档
```

## 示例代码

查看 `examples/` 目录下的示例代码：

- `end_to_end.py` - 端到端完整流程示例
- `collector_example.py` - 数据收集示例
- `cleaning_example.py` - 数据清洗示例
- `annotation_example.py` - 数据标注示例
- `generator_example.py` - 数据生成示例
- `api_client_example.py` - API 客户端示例
- `sdk_example.py` - SDK 使用示例

## 开发

安装开发依赖：

```bash
pip install -e ".[dev]"
```

## 依赖

- numpy
- pandas
- datasets
- scikit-learn
- python-dotenv
- fastapi
- uvicorn
- pydantic
- rich
- requests
- pyarrow

## 许可证

详见 [LICENSE](LICENSE) 文件。

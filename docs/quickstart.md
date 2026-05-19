# 快速开始指南

本指南将帮助你快速上手 Agent History Dataset，完成从安装到生成第一个数据集的全过程。

## 前置要求

- Python 3.9 或更高版本
- pip 包管理器

## 安装

### 1. 克隆项目

```bash
git clone <repository-url>
cd agent-history-dataset
```

### 2. 安装依赖

```bash
pip install -e .
```

### 3. 安装开发依赖（可选）

如果你需要进行开发或测试：

```bash
pip install -e ".[dev]"
```

## 5 分钟快速上手

### 步骤 1：准备数据

首先，准备一些智能体交互数据。你可以使用 JSON 或 CSV 格式。

创建 `sample_data.json`：

```json
{
  "interactions": [
    {
      "user_input": "你好，请问如何学习 Python？",
      "agent_response": "你好！学习 Python 可以从官方教程开始，然后多做练习。"
    },
    {
      "user_input": "谢谢，你的回答很有帮助！",
      "agent_response": "不客气，很高兴能帮到你。"
    }
  ]
}
```

### 步骤 2：收集数据

```python
from src.collector import FileCollector, StorageManager

# 从 JSON 文件收集数据
collector = FileCollector("sample_data.json", format_type="json")
interactions = collector.collect()

# 保存收集到的数据
storage = StorageManager()
saved_path = storage.save(interactions, filename="collected_data.jsonl")
print(f"数据已保存到: {saved_path}")
```

### 步骤 3：清洗数据

```python
from src.cleaner import CleaningPipeline

# 创建清洗流水线
pipeline = CleaningPipeline(
    deduplication_method="content",
    min_text_length=3,
)

# 处理数据
cleaned_data = pipeline.process(interactions)
print(f"清洗后数据量: {len(cleaned_data)}")
```

### 步骤 4：标注数据

```python
from src.annotator import SemiAutoAnnotator, AnnotationStorage

# 使用半自动标注器
annotator = SemiAutoAnnotator()
annotated_data = annotator.annotate_batch(cleaned_data)

# 保存标注数据
anno_storage = AnnotationStorage()
anno_storage.save_batch(annotated_data)
```

### 步骤 5：生成数据集

```python
from src.generator import DatasetGenerationPipeline, ExportFormat

# 创建数据集生成流水线
generator = DatasetGenerationPipeline(
    train_ratio=0.7,
    val_ratio=0.2,
    test_ratio=0.1,
    export_format=ExportFormat.JSONL,
)

# 生成数据集
result = generator.run()
print(f"数据集生成成功! 输出目录: {result['output_dir']}")
```

## 运行端到端示例

项目提供了完整的端到端示例：

```bash
python examples/end_to_end.py
```

## 下一步

- 查看 [API 文档](./api.md) 了解详细的接口说明
- 查看 [使用文档](./README.md) 了解更多功能
- 探索 `examples/` 目录下的更多示例代码

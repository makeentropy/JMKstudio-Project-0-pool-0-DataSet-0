# API 文档

## 目录

- [数据收集模块](#数据收集模块)
- [数据清洗模块](#数据清洗模块)
- [数据标注模块](#数据标注模块)
- [数据生成模块](#数据生成模块)

---

## 数据收集模块

### AgentInteraction

表示单个智能体交互记录。

```python
from src.collector import AgentInteraction, ToolCall

interaction = AgentInteraction(
    id="interaction-001",
    user_input="用户输入文本",
    agent_response="助手回复文本",
    tool_calls=[
        ToolCall(
            name="tool_name",
            arguments={"key": "value"},
            result="工具执行结果"
        )
    ],
    metadata={"source": "manual"}
)
```

### FileCollector

从文件中收集数据。

```python
from src.collector import FileCollector

# 从 JSON 文件收集
json_collector = FileCollector("data.json", format_type="json")
interactions = json_collector.collect()

# 从 CSV 文件收集
csv_collector = FileCollector("data.csv", format_type="csv")
interactions = csv_collector.collect()
```

### StorageManager

管理数据的存储和加载。

```python
from src.collector import StorageManager

storage = StorageManager()

# 保存数据
saved_path = storage.save(interactions, filename="data.jsonl")

# 加载所有数据
all_data = storage.load_all()

# 加载指定文件
data = storage.load(saved_path)
```

### DataCollectorSDK

便捷的 SDK 接口。

```python
from src.collector import DataCollectorSDK

sdk = DataCollectorSDK()

# 收集并保存
interactions = sdk.collect_from_file("data.json")
sdk.save(interactions)
```

---

## 数据清洗模块

### CleaningPipeline

完整的数据清洗流水线。

```python
from src.cleaner import CleaningPipeline

pipeline = CleaningPipeline(
    deduplication_method="content",  # 去重方法: content, hash
    min_text_length=3,               # 最小文本长度
    sanitize_sensitive=True,         # 是否脱敏敏感信息
    normalize_text=True              # 是否归一化文本
)

# 处理数据
cleaned_data = pipeline.process(interactions)

# 从目录处理
output_path = pipeline.run_from_directory(
    input_dir="data/raw",
    output_dir="data/processed"
)

# 评估数据质量
metrics = pipeline.evaluate(cleaned_data)
print(f"质量分数: {metrics.overall_score}")
```

### Deduplicator

数据去重器。

```python
from src.cleaner import Deduplicator

deduplicator = Deduplicator(method="content")
unique_data = deduplicator.deduplicate(interactions)
```

### Sanitizer

敏感信息脱敏器。

```python
from src.cleaner import Sanitizer

sanitizer = Sanitizer()
sanitized = sanitizer.sanitize(interaction)
```

### QualityChecker

质量检查器。

```python
from src.cleaner import QualityChecker

checker = QualityChecker()
metrics = checker.check(interactions)
```

---

## 数据标注模块

### AnnotationLabel

标注标签枚举。

```python
from src.annotator import AnnotationLabel

# 可用标签
labels = [
    AnnotationLabel.HELPFUL,
    AnnotationLabel.UNHELPFUL,
    AnnotationLabel.POSITIVE,
    AnnotationLabel.NEGATIVE,
    AnnotationLabel.NEUTRAL,
    AnnotationLabel.RELEVANT,
    AnnotationLabel.IRRELEVANT,
    AnnotationLabel.COMPLETE,
    AnnotationLabel.INCOMPLETE
]
```

### SemiAutoAnnotator

半自动标注器。

```python
from src.annotator import SemiAutoAnnotator

annotator = SemiAutoAnnotator()

# 批量标注
annotated_list = annotator.annotate_batch(interactions)

# 单条标注
annotated = annotator.annotate(interaction)

# 获取标签建议
suggestions = annotator.suggest_labels(interaction)
```

### ManualAnnotator

人工标注器。

```python
from src.annotator import ManualAnnotator, Annotation

annotator = ManualAnnotator(annotator_id="human_001")

# 创建标注
annotation = annotator.create_annotation(
    label=AnnotationLabel.HELPFUL,
    confidence=1.0,
    notes="用户明确表示有帮助"
)

# 标注数据
annotated_data = annotator.annotate(
    interaction,
    annotations=[annotation]
)
```

### LabelManager

标签管理器。

```python
from src.annotator import LabelManager

manager = LabelManager()

# 获取所有标签
all_labels = manager.get_all_labels()

# 按类别获取
labels = manager.get_labels_by_category("quality")

# 添加自定义标签
manager.add_custom_label("urgent")
```

### QualityChecker

标注质量检查器。

```python
from src.annotator import QualityChecker

checker = QualityChecker(low_confidence_threshold=0.5)

# 批量评估
metrics = checker.assess_batch(annotated_data_list)

# 单条评估
score, issues = checker.assess_single(annotated_data)

# 筛选高质量数据
high_quality = checker.filter_low_quality(annotated_data_list, min_score=0.6)
```

### AnnotationStorage

标注数据存储。

```python
from src.annotator import AnnotationStorage

storage = AnnotationStorage()

# 保存
saved_path = storage.save_batch(annotated_data_list)

# 加载
loaded = storage.load_batch(saved_path)

# 获取统计
stats = storage.get_statistics()
```

---

## 数据生成模块

### DatasetGenerationPipeline

完整的数据集生成流水线。

```python
from src.generator import DatasetGenerationPipeline, ExportFormat

pipeline = DatasetGenerationPipeline(
    input_dir="data/annotated",
    output_dir="data/final",
    train_ratio=0.7,
    val_ratio=0.2,
    test_ratio=0.1,
    enable_augmentation=False,
    export_format=ExportFormat.JSONL
)

# 运行流水线
result = pipeline.run()

print(result["output_dir"])
print(result["split_info"])
print(result["export_paths"])
```

### ExportFormat

导出格式枚举。

```python
from src.generator import ExportFormat

formats = [
    ExportFormat.JSONL,      # JSON Lines 格式
    ExportFormat.PARQUET,    # Parquet 格式
    ExportFormat.ALPACA,     # Alpaca 格式
    ExportFormat.LLAMA       # LLaMA 格式
]
```

### DataSplitter

数据集划分器。

```python
from src.generator import DataSplitter

splitter = DataSplitter(train_ratio=0.7, val_ratio=0.2, test_ratio=0.1)
split_data = splitter.split(data)
```

### DataFormatter

数据格式化器。

```python
from src.generator import DataFormatter, FormatType

formatter = DataFormatter(format_type=FormatType.ALPACA)
formatted = formatter.format(annotated_data)
```

### DataExporter

数据导出器。

```python
from src.generator import DataExporter, ExportFormat

exporter = DataExporter(export_format=ExportFormat.JSONL)
export_path = exporter.export(data, output_dir="output")
```

### TextAugmenter

文本增强器。

```python
from src.generator import TextAugmenter

augmenter = TextAugmenter()
augmented = augmenter.augment(data)
```

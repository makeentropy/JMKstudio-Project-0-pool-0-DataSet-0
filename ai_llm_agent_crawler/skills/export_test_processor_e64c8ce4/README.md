
# export_test_processor Skill

## 描述


## 来源数据集
- 名称: export_test
- 版本: 1.0.0
- 类型: DatasetType.TRAINING
- 数据类型: DataType.TEXT

## 字段
- `id` (str): 

## 标签

## 使用方法
```python
from ai_llm_agent_crawler.skills import {class_name}

skill = {class_name}()
result = skill.process(data)
```

## 配置
{
  "schema_name": "export_test",
  "schema_version": "1.0.0",
  "fields": [
    "id"
  ],
  "labels": [],
  "data_type": "text",
  "dataset_type": "training"
}
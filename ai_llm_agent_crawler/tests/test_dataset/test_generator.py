"""
数据集生成器单元测试
"""

import pytest
from pathlib import Path

from ai_llm_agent_crawler.dataset.generator import DatasetGenerator, JSONDatasetGenerator
from ai_llm_agent_crawler.dataset.processor import DataProcessor


class TestJSONDatasetGenerator:
    """JSONDatasetGenerator类测试"""
    
    def test_generate_from_dict(self, test_output_dir):
        """测试从字典生成数据集"""
        generator = JSONDatasetGenerator()
        generator.config.output_dir = test_output_dir / "datasets"
        
        data = {"name": "Alice", "age": 30, "city": "Beijing"}
        
        df = generator.generate(data)
        
        assert len(df) == 1
        assert "name" in df.columns
        assert df["name"][0] == "Alice"
    
    def test_generate_from_list(self, test_output_dir):
        """测试从列表生成数据集"""
        generator = JSONDatasetGenerator()
        generator.config.output_dir = test_output_dir / "datasets"
        
        data = [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25},
        ]
        
        df = generator.generate(data)
        
        assert len(df) == 2
        assert "name" in df.columns
        assert "age" in df.columns
    
    def test_save_parquet(self, test_output_dir):
        """测试保存为Parquet格式"""
        generator = JSONDatasetGenerator()
        generator.config.output_dir = test_output_dir / "datasets"
        generator.config.output_dir.mkdir(parents=True, exist_ok=True)
        
        data = [{"id": 1, "value": "test"}]
        df = generator.generate(data)
        
        filepath = generator.save(df, "test_dataset", format="parquet")
        
        assert filepath.exists()
        assert filepath.suffix == ".parquet"
    
    def test_save_csv(self, test_output_dir):
        """测试保存为CSV格式"""
        generator = JSONDatasetGenerator()
        generator.config.output_dir = test_output_dir / "datasets"
        generator.config.output_dir.mkdir(parents=True, exist_ok=True)
        
        data = [{"id": 1, "value": "test"}]
        df = generator.generate(data)
        
        filepath = generator.save(df, "test_dataset", format="csv")
        
        assert filepath.exists()
        assert filepath.suffix == ".csv"
    
    def test_load_dataset(self, test_output_dir):
        """测试加载数据集"""
        generator = JSONDatasetGenerator()
        generator.config.output_dir = test_output_dir / "datasets"
        generator.config.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 先保存一个数据集
        data = [{"id": 1, "value": "test"}]
        df = generator.generate(data)
        filepath = generator.save(df, "test_load", format="parquet")
        
        # 然后加载
        loaded_df = generator.load(filepath)
        
        assert len(loaded_df) == 1
        assert loaded_df["id"][0] == 1


class TestDataProcessor:
    """DataProcessor类测试"""
    
    def test_drop_duplicates(self):
        """测试删除重复行"""
        import pandas as pd
        
        data = pd.DataFrame([
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
            {"id": 1, "name": "Alice"},  # 重复
        ])
        
        processor = DataProcessor(data)
        result = processor.drop_duplicates().get_result()
        
        assert len(result) == 2
    
    def test_drop_na(self):
        """测试删除缺失值"""
        import pandas as pd
        import numpy as np
        
        data = pd.DataFrame([
            {"id": 1, "value": 10},
            {"id": 2, "value": np.nan},
            {"id": 3, "value": 30},
        ])
        
        processor = DataProcessor(data)
        result = processor.drop_na(subset=["value"]).get_result()
        
        assert len(result) == 2
    
    def test_fill_na(self):
        """测试填充缺失值"""
        import pandas as pd
        import numpy as np
        
        data = pd.DataFrame([
            {"id": 1, "value": np.nan},
            {"id": 2, "value": np.nan},
        ])
        
        processor = DataProcessor(data)
        result = processor.fill_na(value=0, columns=["value"]).get_result()
        
        assert result["value"][0] == 0
        assert result["value"][1] == 0
    
    def test_rename_columns(self):
        """测试重命名列"""
        import pandas as pd
        
        data = pd.DataFrame({"old_name": [1, 2, 3]})
        
        processor = DataProcessor(data)
        result = processor.rename_columns({"old_name": "new_name"}).get_result()
        
        assert "new_name" in result.columns
        assert "old_name" not in result.columns
    
    def test_filter(self):
        """测试过滤"""
        import pandas as pd
        
        data = pd.DataFrame([
            {"id": 1, "value": 10},
            {"id": 2, "value": 20},
            {"id": 3, "value": 30},
        ])
        
        processor = DataProcessor(data)
        result = processor.filter(lambda row: row["value"] > 15).get_result()
        
        assert len(result) == 2
        assert result["id"].tolist() == [2, 3]
    
    def test_sort(self):
        """测试排序"""
        import pandas as pd
        
        data = pd.DataFrame([
            {"id": 3, "value": 30},
            {"id": 1, "value": 10},
            {"id": 2, "value": 20},
        ])
        
        processor = DataProcessor(data)
        result = processor.sort(by="id", ascending=True).get_result()
        
        assert result["id"].tolist() == [1, 2, 3]
    
    def test_chain_operations(self):
        """测试链式操作"""
        import pandas as pd
        
        data = pd.DataFrame([
            {"id": 1, "name": "Alice", "age": 30},
            {"id": 2, "name": "Bob", "age": 25},
            {"id": 1, "name": "Alice", "age": 30},  # 重复
        ])
        
        processor = DataProcessor(data)
        result = processor.drop_duplicates().sort(by="id").get_result()
        
        assert len(result) == 2
        assert result["id"].tolist() == [1, 2]
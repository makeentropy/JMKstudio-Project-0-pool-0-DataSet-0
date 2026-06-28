"""
pytest配置文件

配置测试环境和共享fixtures。
"""

import os
import sys
from pathlib import Path

import pytest

# 将src目录添加到Python路径
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))


@pytest.fixture(scope="session")
def test_data_dir():
    """测试数据目录"""
    data_dir = Path(__file__).parent / "data"
    data_dir.mkdir(exist_ok=True)
    return data_dir


@pytest.fixture(scope="session")
def test_output_dir():
    """测试输出目录"""
    output_dir = Path(__file__).parent / "output"
    output_dir.mkdir(exist_ok=True)
    return output_dir


@pytest.fixture(scope="session")
def test_config():
    """测试配置"""
    from ai_llm_agent_crawler.utils.config import Settings
    
    return Settings(
        debug=True,
        environment="testing",
        log_level="DEBUG",
        dataset_output_dir=Path("tests/output/datasets"),
    )


@pytest.fixture(scope="function")
def temp_file(test_output_dir):
    """临时文件fixture"""
    import tempfile
    
    with tempfile.NamedTemporaryFile(mode="w", delete=False, dir=test_output_dir) as f:
        filepath = Path(f.name)
    
    yield filepath
    
    # 清理
    if filepath.exists():
        filepath.unlink()
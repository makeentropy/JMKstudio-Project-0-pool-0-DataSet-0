# AI LLM Agent Crawler

智能爬虫与数据集生成系统

## 项目简介

AI LLM Agent Crawler 是一个功能强大的智能爬虫系统，集成了数据集生成、维度空间质能质量子奇点系统、安全加密、NAS存储管理和版本管理等模块。

## 主要功能

- **智能爬虫**: 支持同步/异步HTTP爬虫、浏览器爬虫、Scrapy框架等
- **数据集生成**: 提供多种格式的数据集生成和处理功能
- **安全加密**: AES加密、多种哈希算法支持
- **存储管理**: NAS存储、对象存储、数据库支持
- **版本管理**: 数据版本控制和变更追踪

## 项目结构

```
ai_llm_agent_crawler/
├── src/                    # 源代码目录
│   └── ai_llm_agent_crawler/
│       ├── crawler/        # 爬虫模块
│       ├── dataset/        # 数据集生成模块
│       ├── dimension/      # 维度空间模块
│       ├── security/       # 安全加密模块
│       ├── storage/        # 存储管理模块
│       ├── versioning/     # 版本管理模块
│       └── utils/          # 工具模块
├── tests/                  # 测试目录
├── config/                 # 配置文件目录
├── logs/                   # 日志目录
├── data/                   # 数据目录
├── docs/                   # 文档目录
├── pyproject.toml          # 项目配置
├── requirements.txt        # 依赖列表
└── README.md               # 项目说明
```

## 安装

```bash
# 克隆项目
git clone https://github.com/yourusername/ai_llm_agent_crawler.git
cd ai_llm_agent_crawler

# 安装依赖
pip install -r requirements.txt

# 或使用pip安装
pip install -e .
```

## 配置

1. 复制环境变量模板:
```bash
cp .env.example .env
```

2. 编辑 `.env` 文件，填写必要的配置值

3. 或使用 `config/settings.yaml` 进行详细配置

## 使用示例

### 基础爬虫使用

```python
from ai_llm_agent_crawler import setup_logging, get_logger
from ai_llm_agent_crawler.crawler import AsyncHTTPCrawler

# 初始化日志
setup_logging(log_level="INFO")

# 创建爬虫
crawler = AsyncHTTPCrawler()
crawler.start()

# 爬取数据
import asyncio
result = asyncio.run(crawler.fetch("https://example.com"))
print(result.content)

crawler.stop()
```

### 数据集生成

```python
from ai_llm_agent_crawler.dataset import JSONDatasetGenerator, DataProcessor

# 创建生成器
generator = JSONDatasetGenerator()

# 从JSON生成数据集
data = [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}]
df = generator.generate(data)

# 处理数据
processor = DataProcessor(df)
result = processor.drop_duplicates().sort(by="id").get_result()

# 保存数据集
generator.save(result, "output_dataset", format="parquet")
```

### 加密功能

```python
from ai_llm_agent_crawler.security import AESCipher, HashCalculator

# 加密数据
cipher = AESCipher("my_password")
encrypted = cipher.encrypt("敏感数据")
decrypted = cipher.decrypt(encrypted)

# 计算哈希
hash_calc = HashCalculator("sha256")
hash_value = hash_calc.calculate("数据内容")
```

## 开发指南

### 运行测试

```bash
# 运行所有测试
pytest

# 运行带覆盖率的测试
pytest --cov=ai_llm_agent_crawler
```

### 代码质量检查

```bash
# 格式化代码
black src tests

# 检查代码风格
flake8 src tests

# 类型检查
mypy src
```

## 许可证

MIT License

## 贡献

欢迎提交Issue和Pull Request！
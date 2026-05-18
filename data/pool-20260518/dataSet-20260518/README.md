# JMKstudio-Project-0-pool-0-DataSet-0

数据收集和处理自动化系统

## 功能

- 从 GitHub 或本地读取 DataCollectsList.csv 配置
- 根据配置收集文件和目录
- 数据集蒸馏（去重、索引、分类）
- GPG 加密
- 数据压缩
- 字典数据库存储
- Git 自动推送

## 安装

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本使用

```bash
# 从 GitHub 读取配置并收集数据
python main.py

# 使用本地 CSV 文件
python main.py --csv-local /path/to/DataCollectsList.csv

# 完整流程（收集、处理、压缩、加密、推送）
python main.py --compress --encrypt --git-push --create-db
```

### 命令行选项

- `--csv-url URL`: 指定 DataCollectsList.csv 的 URL
- `--csv-local PATH`: 使用本地的 CSV 文件
- `--compress`: 压缩收集的数据
- `--encrypt`: 加密收集的数据
- `--gpg-key ID`: 指定 GPG 密钥 ID 用于加密
- `--gpg-passphrase PASSWORD`: 使用对称加密的密码
- `--git-push`: 推送到 Git 仓库
- `--git-url URL`: 指定 Git 仓库 URL
- `--git-branch BRANCH`: 指定 Git 分支（默认 main）
- `--no-process`: 跳过数据处理和蒸馏步骤
- `--create-db`: 创建字典数据库

## DataCollectsList.csv 格式

```csv
path,rule,infomation,more,[logs]
/path/to/directory,important,Description,Additional info,timestamp1:action1|timestamp2:action2
```

## 项目结构

```
.
├── src/
│   ├── collector/          # 数据收集模块
│   ├── processor/          # 数据处理模块
│   ├── encryptor/          # 加密和压缩模块
│   ├── git_manager/        # Git 管理模块
│   └── utils/              # 工具模块
├── data/                   # 收集的数据存储
├── logs/                   # 日志文件
└── config/                 # 配置文件
```

# 神誓工具链 (Oath Toolchain)

> 一个功能强大的密码学与安全工具链，提供从底层密码原语到高层业务编排的完整解决方案。

[![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-1710-brightgreen)]()
[![Coverage](https://img.shields.io/badge/coverage-89.6%25-brightgreen)]()

## 项目简介

神誓工具链（Oath Toolchain）是一个模块化的密码学与安全工具开发框架，集成了对称加密、非对称加密、KARMACA空间加密、几何证明、零知识证明、CA证书体系、隐写技术、NLP密钥生成、奇点验证、数据集管理、乾坤管道编排等多种安全工具。

项目采用四层架构设计，提供统一的 SDK 和 CLI 接口，帮助开发者快速构建安全可靠的应用程序。

## 项目架构

神誓工具链采用四层架构设计，各层职责清晰，耦合度低：

```
┌─────────────────────────────────────────────────────────┐
│                     接口层 (Interface)                   │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐     │
│  │  SDK API    │  │  CLI 命令   │  │  REST API    │     │
│  └─────────────┘  └─────────────┘  └──────────────┘     │
├─────────────────────────────────────────────────────────┤
│                     编排层 (Orchestration)               │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐     │
│  │ 乾坤引擎    │  │ 管道系统    │  │ 工作流执行器 │     │
│  └─────────────┘  └─────────────┘  └──────────────┘     │
├─────────────────────────────────────────────────────────┤
│                     工具层 (Tools)                       │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ KARMACA  │ │ 几何证明 │ │ CA证书   │ │ 隐写术   │    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐    │
│  │ NLP密钥  │ │ 奇点验证 │ │ 数据集池 │ │ Karma标签│    │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘    │
├─────────────────────────────────────────────────────────┤
│                     核心层 (Core)                        │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐     │
│  │ 密码原语    │  │ 数据结构    │  │ 数学基础     │     │
│  └─────────────┘  └─────────────┘  └──────────────┘     │
│  ┌─────────────┐  ┌─────────────┐  ┌──────────────┐     │
│  │ 工具基类    │  │ 配置管理    │  │ 异常体系     │     │
│  └─────────────┘  └─────────────┘  └──────────────┘     │
└─────────────────────────────────────────────────────────┘
```

### 架构说明

- **接口层**：提供 SDK 和 CLI 两种访问方式，支持多种编程范式
- **编排层**：乾坤引擎统一管理工具注册、管道执行、工作流编排
- **工具层**：8大功能模块，涵盖密码学、隐写、证书、数据管理等领域
- **核心层**：提供基础密码原语、数据结构、数学工具和通用基础设施

## 主要特性

### 🔐 密码学功能
- **对称加密**：AES-GCM 加密，支持 128/192/256 位密钥
- **非对称加密**：RSA-OAEP 加密与签名验证
- **KARMACA 空间加密**：基于空间字典的多维加密算法
- **几何证明加密**：结合几何哈希的完整性证明加密
- **哈希算法**：SHA-256/512、SHA-3、BLAKE2、MD5 等
- **密钥派生**：PBKDF2、HKDF 等标准 KDF

### 📜 CA 证书体系
- 根 CA 初始化与管理
- 中间 CA 创建与证书链
- 终端实体证书签发
- 证书验证与吊销
- 证书生命周期管理

### 🔒 隐写技术
- **XOR 隐写**：基于异或的二进制隐写
- **文本隐写**：Unicode 零宽字符、空格编码
- **证书隐写**：将数据嵌入 X.509 证书扩展字段
- **容量分析**：载体隐写容量评估
- **安全性分析**：隐写安全性检测

### 📐 几何证明
- 几何哈希算法
- 几何证明生成与验证
- 零知识证明（ZKP）
- 可验证随机函数（VRF）
- 范围证明与成员证明

### 🗝️ 密钥生成
- 标准随机密钥生成
- **NLP 语义密钥**：从自然语言文本生成密钥
- KARMACA 空间密钥生成
- 组合密钥生成
- 密钥强度评估

### ⚡ 奇点验证
- 密钥奇点检测
- 数据质能分析
- 异常模式识别
- 多维度质量评估

### 📊 数据集管理
- 数据集创建与版本控制
- Karma 标签系统
- 元数据管理
- 标签索引与检索
- 数据导入导出

### 🔧 编排系统
- **乾坤管道**：预置加密管道
- 自定义管道定义
- 工作流编排
- 安全配置文件

## 快速开始

### 安装

使用 pip 安装：

```bash
pip install oath-toolchain
```

或从源码安装：

```bash
git clone https://github.com/oath-toolchain/oath-toolchain.git
cd oath-toolchain
pip install -e .
```

### 快速示例

#### 使用 SDK

```python
from oath_toolchain.sdk import OathSDK

# 初始化SDK
sdk = OathSDK()

# 生成AES密钥
key = sdk.keys.generate_aes_key(256)

# AES加密
data = b"Hello, Oath Toolchain!"
encrypted = sdk.crypto.encrypt_aes(data, key)
decrypted = sdk.crypto.decrypt_aes(encrypted, key)

print(f"原始数据: {data.decode()}")
print(f"解密后: {decrypted.decode()}")
```

#### 使用 CLI

```bash
# 生成密钥
oath keygen aes --bits 256 --output key.bin

# 加密文件
oath encrypt aes --key key.bin --input plain.txt --output encrypted.bin

# 解密文件
oath decrypt aes --key key.bin --input encrypted.bin --output decrypted.txt
```

## 模块介绍

### 1. KARMACA 空间字典
基于多维空间映射的加密系统，将数据映射到高维空间进行加密存储。

### 2. NLP 密钥生成
利用自然语言处理技术从文本中提取特征生成密钥，支持语义模式、熵值模式和混合模式。

### 3. CA 证书体系
完整的公钥基础设施（PKI）实现，支持多级CA证书链管理。

### 4. 隐写工具集
多种隐写技术的实现，提供数据隐藏与提取能力。

### 5. 几何证明
基于几何哈希的证明系统，支持零知识证明和可验证随机函数。

### 6. 奇点验证器
基于质能模型的奇点检测算法，用于评估密钥和数据的质量。

### 7. 乾坤管道
可视化的加密工作流编排系统，支持自定义管道和安全配置文件。

### 8. 数据集池
带版本控制和标签系统的数据集管理工具，支持Karma标签索引。

## 项目结构

```
oath_toolchain/
├── src/oath_toolchain/
│   ├── api/                    # API层
│   ├── cli/                    # CLI命令行
│   │   └── commands/           # 各子命令
│   ├── core/                   # 核心层
│   │   ├── crypto/             # 密码原语
│   │   ├── data_structures/    # 数据结构
│   │   └── math/               # 数学基础
│   ├── orchestration/          # 编排层
│   │   ├── qiankun_engine.py   # 乾坤引擎
│   │   ├── pipeline.py         # 管道系统
│   │   └── workflow_executor.py # 工作流执行器
│   ├── sdk/                    # SDK接口
│   └── tools/                  # 工具层
│       ├── karmaca/            # KARMACA空间加密
│       ├── nlptcmodel/         # NLP密钥生成
│       ├── ca_system/          # CA证书系统
│       ├── steganography/      # 隐写术
│       ├── geometric_proof/    # 几何证明
│       ├── singularity/        # 奇点验证
│       ├── dataset_pool/       # 数据集池
│       └── karma_tags/         # Karma标签
├── tests/                      # 测试代码
├── examples/                   # 示例脚本
├── docs/                       # 文档
└── pyproject.toml              # 项目配置
```

## 开发指南

### 安装开发依赖

```bash
pip install -e ".[dev]"
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行单元测试
pytest -m unit

# 运行集成测试
pytest -m integration

# 查看覆盖率
pytest --cov=oath_toolchain --cov-report=html
```

### 代码规范

项目使用以下工具保证代码质量：
- **black**：代码格式化
- **isort**：导入排序
- **ruff**：代码 linting
- **mypy**：类型检查

```bash
# 格式化代码
black src/ tests/

# 排序导入
isort src/ tests/

# 类型检查
mypy src/
```

## 贡献指南

我们欢迎社区贡献！请参阅 [贡献指南](docs/contributing.md) 了解详细流程。

### 如何贡献

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

### 报告问题

如果发现 bug 或有功能建议，请在 [Issues](https://github.com/oath-toolchain/oath-toolchain/issues) 中提交。

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件。

## 相关链接

- [项目主页](https://github.com/oath-toolchain/oath-toolchain)
- [文档](https://oath-toolchain.readthedocs.io)
- [问题反馈](https://github.com/oath-toolchain/oath-toolchain/issues)

---

*神誓工具链 - 让安全开发更简单* ⚔️

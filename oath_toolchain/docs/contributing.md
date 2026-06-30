# 贡献指南

感谢您对神誓工具链项目的关注！我们欢迎各种形式的贡献，包括但不限于代码提交、bug 报告、功能建议和文档改进。

## 目录

- [行为准则](#行为准则)
- [开发环境搭建](#开发环境搭建)
- [代码规范](#代码规范)
- [测试规范](#测试规范)
- [提交流程](#提交流程)
- [贡献类型](#贡献类型)

---

## 行为准则

参与本项目时，请遵守以下行为准则：

- 尊重他人，保持友善和专业
- 接受不同的观点和经验
- 专注于对社区最有利的事情
- 对其他成员有同理心

 unacceptable 的行为包括：
- 使用性化的语言或图像，以及不受欢迎的性关注或性骚扰
- 恶意评论、侮辱/贬损性评论以及个人或政治攻击
- 公开或私下的骚扰
- 未经明确许可发布他人的私人信息，如物理地址或电子邮件地址
- 在专业环境中可能被合理视为不恰当的其他行为

---

## 开发环境搭建

### 1. 克隆仓库

```bash
git clone https://github.com/oath-toolchain/oath-toolchain.git
cd oath-toolchain
```

### 2. 创建虚拟环境（推荐）

```bash
# 使用 venv
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate  # Windows

# 或使用 conda
conda create -n oath python=3.10
conda activate oath
```

### 3. 安装开发依赖

```bash
pip install -e ".[dev]"
```

这将安装：
- 项目本身（可编辑模式）
- pytest、pytest-cov、pytest-mock（测试）
- black、isort（代码格式化）
- ruff（代码 linting）
- mypy（类型检查）

### 4. 验证安装

```bash
# 运行测试
pytest

# 查看版本
oath --version
```

### 5. 项目结构

```
oath_toolchain/
├── src/oath_toolchain/       # 源代码
│   ├── api/                  # API层
│   ├── cli/                  # CLI命令行
│   ├── core/                 # 核心层
│   ├── orchestration/        # 编排层
│   ├── sdk/                  # SDK接口
│   └── tools/                # 工具层
├── tests/                    # 测试代码
│   ├── test_core/            # 核心层测试
│   ├── test_tools/           # 工具层测试
│   ├── test_sdk/             # SDK测试
│   ├── test_cli/             # CLI测试
│   ├── test_orchestration/   # 编排层测试
│   ├── integration/          # 集成测试
│   ├── performance/          # 性能测试
│   └── security/             # 安全测试
├── examples/                 # 示例脚本
├── docs/                     # 文档
└── pyproject.toml            # 项目配置
```

---

## 代码规范

### Python 版本

- 最低支持 Python 3.10
- 利用新的类型提示特性

### 代码格式化

使用 **black** 进行代码格式化：

```bash
# 格式化所有代码
black src/ tests/ examples/

# 检查格式问题（不修改）
black --check src/ tests/
```

配置（在 pyproject.toml 中）：
- 行长度：88 字符
- 目标版本：Python 3.10

### 导入排序

使用 **isort** 排序导入：

```bash
# 排序导入
isort src/ tests/ examples/

# 检查导入顺序
isort --check src/ tests/
```

配置：
- 使用 black 配置文件
- 行长度：88 字符

### 导入顺序规则

1. 标准库导入
2. 第三方库导入
3. 本地项目导入
4. 空行分隔各组

```python
import os
import sys
from typing import List, Optional

import numpy as np
from cryptography.hazmat.primitives import hashes

from ..core.base import OathTool
from ..core.exceptions import ValidationError
```

### Linting

使用 **ruff** 进行代码 linting：

```bash
# 运行 linting
ruff check src/ tests/

# 自动修复可修复的问题
ruff check --fix src/ tests/
```

启用的规则：
- E：错误
- F：流程控制
- W：警告
- I：导入排序
- N：PEP 8 命名
- UP：pyupgrade 升级提示

### 类型检查

使用 **mypy** 进行静态类型检查：

```bash
# 类型检查
mypy src/
```

配置：
- Python 版本：3.10
- 禁止无类型定义（`disallow_untyped_defs = true`）
- 检查无类型定义（`check_untyped_defs = true`）

### 类型提示规范

所有公共 API 必须有完整的类型注解：

```python
# ✅ 好的做法
def encrypt_aes(self, data: bytes, key: bytes) -> bytes:
    """使用AES加密数据。"""
    ...

# ❌ 不好的做法
def encrypt_aes(self, data, key):
    """使用AES加密数据。"""
    ...
```

### 文档字符串

使用 Google 风格的文档字符串：

```python
def generate_key(self, bits: int = 256) -> bytes:
    """生成AES密钥。

    Args:
        bits: 密钥位数，支持128、192、256，默认为256

    Returns:
        AES密钥字节

    Raises:
        ValueError: 当密钥大小无效时

    Examples:
        >>> key = generate_key(256)
        >>> len(key)
        32
    """
    ...
```

### 命名规范

| 类型 | 规范 | 示例 |
|------|------|------|
| 变量 | snake_case | `user_name`, `max_length` |
| 函数 | snake_case | `calculate_hash()`, `get_user()` |
| 类 | PascalCase | `AESCipher`, `KeyGenerator` |
| 常量 | UPPER_SNAKE_CASE | `MAX_RETRIES`, `DEFAULT_PORT` |
| 私有变量 | _snake_case | `_internal_state`, `_cache` |
| 私有方法 | _snake_case | `_validate_input()`, `_process_data()` |

---

## 测试规范

### 测试框架

使用 **pytest** 作为测试框架。

### 运行测试

```bash
# 运行所有测试
pytest

# 运行特定测试文件
pytest tests/test_core/test_crypto_primitives.py

# 运行特定测试函数
pytest tests/test_core/test_crypto_primitives.py::test_aes_encrypt

# 运行带标记的测试
pytest -m unit
pytest -m integration
pytest -m slow

# 显示详细输出
pytest -v

# 显示覆盖率
pytest --cov=oath_toolchain --cov-report=html
```

### 测试标记

项目使用以下 pytest 标记：

- `unit`：单元测试
- `integration`：集成测试
- `performance`：性能测试
- `security`：安全测试
- `slow`：慢速测试
- `crypto`：密码学相关测试
- `steganography`：隐写相关测试
- `certificate`：证书/CA 相关测试
- `dataset`：数据集相关测试
- `sdk`：SDK 相关测试
- `cli`：CLI 相关测试

### 测试覆盖率要求

- 整体覆盖率不低于 85%
- 新代码的覆盖率应达到 90% 以上
- 核心加密模块的覆盖率应达到 95% 以上

### 编写测试的最佳实践

1. **测试命名清晰**

```python
# ✅ 好的做法
def test_encrypt_with_valid_key_returns_bytes():
    ...

def test_decrypt_with_wrong_key_raises_error():
    ...

# ❌ 不好的做法
def test_encrypt1():
    ...
```

2. **每个测试只测一个功能点**

```python
# ✅ 好的做法
def test_encrypt_returns_correct_length():
    ...

def test_decrypt_restores_original_data():
    ...

# ❌ 不好的做法
def test_everything():
    # 测试太多东西
    ...
```

3. **使用 fixture 共享设置**

```python
import pytest

@pytest.fixture
def sdk():
    return OathSDK()

@pytest.fixture
def aes_key():
    return os.urandom(32)

def test_encrypt_decrypt(sdk, aes_key):
    data = b"test"
    encrypted = sdk.crypto.encrypt_aes(data, aes_key)
    decrypted = sdk.crypto.decrypt_aes(encrypted, aes_key)
    assert decrypted == data
```

4. **测试异常情况**

```python
import pytest

def test_encrypt_with_invalid_key_length():
    with pytest.raises(ValueError, match="无效的密钥长度"):
        sdk.crypto.encrypt_aes(b"data", b"too_short")
```

### 测试目录结构

```
tests/
├── conftest.py           # 全局 fixture 配置
├── test_core/            # 核心层测试
│   ├── test_base.py
│   ├── test_config.py
│   ├── test_crypto_primitives.py
│   └── ...
├── test_tools/           # 工具层测试
│   ├── test_ca_tool.py
│   ├── test_stego_tool.py
│   └── ...
├── test_sdk/             # SDK 测试
│   ├── test_oath_sdk.py
│   ├── test_crypto_api.py
│   └── ...
├── test_cli/             # CLI 测试
│   ├── test_cli_main.py
│   ├── test_cli_encrypt.py
│   └── ...
├── test_orchestration/   # 编排层测试
├── integration/          # 集成测试
├── performance/          # 性能测试
└── security/             # 安全测试
```

---

## 提交流程

### 1. Fork 仓库

在 GitHub 上 Fork 本仓库到您的账号。

### 2. 创建分支

```bash
# 从 main 分支创建新分支
git checkout -b feature/your-feature-name

# 或修复 bug
git checkout -b fix/bug-description
```

分支命名约定：
- `feature/xxx`：新功能
- `fix/xxx`：Bug 修复
- `docs/xxx`：文档更新
- `refactor/xxx`：代码重构
- `test/xxx`：测试相关

### 3. 编写代码

- 遵循代码规范
- 添加或更新测试
- 更新文档

### 4. 运行检查

提交前确保所有检查通过：

```bash
# 1. 代码格式化
black src/ tests/ examples/
isort src/ tests/ examples/

# 2. Linting
ruff check src/ tests/

# 3. 类型检查
mypy src/

# 4. 运行测试
pytest

# 5. 检查覆盖率
pytest --cov=oath_toolchain
```

### 5. 提交更改

```bash
# 添加更改
git add .

# 提交
git commit -m "简短描述提交内容"
```

提交信息规范：
- 使用祈使语气（"添加" 而不是 "添加了"）
- 第一行不超过 72 字符
- 详细描述可以换行
- 关联 Issue 编号

```
feat: 添加新的加密算法支持

- 添加 XChaCha20-Poly1305 加密算法
- 添加相应的测试用例
- 更新文档

Closes #123
```

提交类型前缀：
- `feat:`：新功能
- `fix:`：Bug 修复
- `docs:`：文档更新
- `style:`：代码格式调整
- `refactor:`：代码重构
- `perf:`：性能优化
- `test:`：测试相关
- `chore:`：构建/工具链相关

### 6. 推送到您的 Fork

```bash
git push origin feature/your-feature-name
```

### 7. 创建 Pull Request

在 GitHub 上创建 Pull Request：

- 标题清晰描述更改
- 提供详细的描述
- 关联相关的 Issue
- 勾选 PR 模板中的检查项

### 8. 代码审查

- 等待维护者审查
- 根据反馈进行修改
- 修改后推送到同一分支

### 9. 合并

PR 通过审查后，维护者会将其合并到主分支。

---

## 贡献类型

### 1. Bug 报告

发现了 bug？请提交 Issue：

- 使用清晰的描述性标题
- 提供复现步骤
- 描述预期行为和实际行为
- 提供环境信息（Python 版本、操作系统等）
- 如果可能，提供最小复现代码

### 2. 功能建议

有新功能的想法？请提交 Issue：

- 描述功能和解决的问题
- 说明为什么这个功能对大多数用户有用
- 提供使用示例
- 如果可能，提出实现方案

### 3. 代码贡献

- 修复已知的 bug
- 实现新功能
- 改进性能
- 改进代码质量
- 添加测试用例

### 4. 文档贡献

- 修复拼写错误
- 改进文档清晰度
- 添加新文档
- 翻译文档
- 添加示例代码

### 5. 其他贡献

- 回答社区问题
- 分享使用经验
- 推广项目
- 提出改进建议

---

## 常见问题

### Q: 我需要什么级别的 Python 知识才能贡献？

A: 这取决于您想做什么。修复拼写错误或小 bug 只需要基础 Python 知识。添加新的加密工具需要对密码学有一定了解。

### Q: 第一次贡献应该做什么？

A: 建议从以下开始：
1. 查看 "good first issue" 标签的问题
2. 修复文档中的错误
3. 添加测试用例
4. 改进代码注释

### Q: 如何获取帮助？

A: 可以通过以下方式：
- 在 GitHub Discussions 中提问
- 提交 Issue 并标记为 question
- 查看现有文档和示例

### Q: 我的贡献多久会被审查？

A: 我们会尽快审查所有 PR，通常在 1-3 个工作日内。如果您的 PR 一周内没有得到回复，可以 @ 维护者提醒。

---

再次感谢您的贡献！每一份贡献都让神誓工具链变得更好。

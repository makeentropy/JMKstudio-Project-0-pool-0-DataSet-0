# API 参考

本文档提供神誓工具链 SDK 的 API 参考，包括主要类和方法的索引。

## 目录

- [SDK 概述](#sdk-概述)
- [OathSDK 主类](#oathsdk-主类)
- [CryptoAPI 加密 API](#cryptoapi-加密-api)
- [KeyAPI 密钥 API](#keyapi-密钥-api)
- [CAAPI 证书 API](#caapi-证书-api)
- [StegoAPI 隐写 API](#stegoapi-隐写-api)
- [DatasetAPI 数据集 API](#datasetapi-数据集-api)
- [PipelineAPI 管道 API](#pipelineapi-管道-api)

## SDK 概述

神誓工具链 SDK 提供统一的高层编程接口，通过 `OathSDK` 类访问所有功能。

### 快速开始

```python
from oath_toolchain.sdk import OathSDK

# 初始化 SDK
sdk = OathSDK()

# 使用各功能模块
key = sdk.keys.generate_aes_key(256)
encrypted = sdk.crypto.encrypt_aes(b"Hello", key)
decrypted = sdk.crypto.decrypt_aes(encrypted, key)
```

### 模块对应关系

| SDK 属性 | 类 | 功能 |
|----------|-----|------|
| `sdk.crypto` | `CryptoAPI` | 加密、解密、签名、哈希 |
| `sdk.keys` | `KeyAPI` | 密钥生成、派生、强度评估 |
| `sdk.ca` | `CAAPI` | CA 证书管理 |
| `sdk.stego` | `StegoAPI` | 隐写术 |
| `sdk.datasets` | `DatasetAPI` | 数据集管理 |
| `sdk.pipelines` | `PipelineAPI` | 管道编排 |

---

## OathSDK 主类

**模块**: `oath_toolchain.sdk.oath_sdk`

### 构造函数

```python
OathSDK(config: Optional[Dict[str, Any]] = None)
```

**参数**:
- `config`：配置字典，可选
  - `auto_register_tools`：是否自动注册工具，默认 False
  - `default_security_profile`：默认安全配置文件

### 属性

| 属性 | 类型 | 描述 |
|------|------|------|
| `crypto` | `CryptoAPI` | 加密 API 实例 |
| `keys` | `KeyAPI` | 密钥 API 实例 |
| `ca` | `CAAPI` | CA 证书 API 实例 |
| `stego` | `StegoAPI` | 隐写 API 实例 |
| `datasets` | `DatasetAPI` | 数据集 API 实例 |
| `pipelines` | `PipelineAPI` | 管道 API 实例 |
| `engine` | `QiankunEngine` | 乾坤引擎实例 |

### 方法

#### `list_tools() -> List[Dict[str, Any]]`

列出所有已注册的工具。

**返回**: 工具元数据列表，每个元素包含工具的名称、描述、版本等信息

---

#### `execute_tool(tool_name: str, action: str, params: Dict[str, Any]) -> Dict[str, Any]`

执行指定工具的指定操作。

**参数**:
- `tool_name`：工具名称
- `action`：操作名称
- `params`：参数字典

**返回**: 执行结果字典

**异常**:
- `ToolNotFoundError`：当工具不存在时
- `ValidationError`：当参数验证失败时

---

#### `version() -> str`

获取 SDK 版本号。

**返回**: 版本号字符串

---

## CryptoAPI 加密 API

**模块**: `oath_toolchain.sdk.crypto_api`

### 对称加密

#### `encrypt_aes(data: bytes, key: bytes) -> bytes`

使用 AES-GCM 加密数据。

**参数**:
- `data`：待加密的明文数据
- `key`：加密密钥（16、24 或 32 字节）

**返回**: 加密后的数据，格式: `nonce(12) + tag(16) + ciphertext`

---

#### `decrypt_aes(data: bytes, key: bytes) -> bytes`

使用 AES-GCM 解密数据。

**参数**:
- `data`：加密数据，格式: `nonce(12) + tag(16) + ciphertext`
- `key`：解密密钥

**返回**: 解密后的明文数据

---

### 非对称加密

#### `encrypt_rsa(data: bytes, public_key: bytes) -> bytes`

使用 RSA-OAEP 加密数据。

**参数**:
- `data`：待加密的明文数据
- `public_key`：PEM 格式的公钥字节

**返回**: 加密后的密文数据

---

#### `decrypt_rsa(data: bytes, private_key: bytes) -> bytes`

使用 RSA-OAEP 解密数据。

**参数**:
- `data`：密文数据
- `private_key`：PEM 格式的私钥字节

**返回**: 解密后的明文数据

---

### KARMACA 空间加密

#### `encrypt_karmaca(data: bytes, space_key: bytes, dimensions: int = 3) -> bytes`

使用 KARMACA 空间字典加密数据。

**参数**:
- `data`：待加密的明文数据
- `space_key`：空间密钥（用于生成空间坐标）
- `dimensions`：空间维度数，默认为 3

**返回**: 加密后的数据

---

#### `decrypt_karmaca(data: bytes, space_key: bytes, dimensions: int = 3) -> bytes`

使用 KARMACA 空间字典解密数据。

**参数**:
- `data`：加密数据
- `space_key`：空间密钥
- `dimensions`：空间维度数，默认为 3

**返回**: 解密后的明文数据

---

### 几何证明加密

#### `encrypt_geometric(data: bytes, key: bytes) -> Dict[str, Any]`

使用几何证明加密数据。先用 AES 加密数据，再生成几何证明。

**参数**:
- `data`：待加密的明文数据
- `key`：加密密钥

**返回**: 包含加密数据和证明的字典: `{"data": bytes, "proof": dict}`

---

#### `decrypt_geometric(data: bytes, proof: Dict[str, Any], key: bytes) -> bytes`

使用几何证明解密数据。先验证几何证明，再用 AES 解密数据。

**参数**:
- `data`：加密数据
- `proof`：几何证明字典
- `key`：解密密钥

**返回**: 解密后的明文数据

**异常**:
- `ValidationError`：当证明验证失败时

---

### 多层加密

#### `encrypt_full(data: bytes, config: Dict[str, Any]) -> Dict[str, Any]`

完整多层加密。按照配置进行多层加密，包括 AES、RSA、KARMACA 等。

**参数**:
- `data`：待加密的明文数据
- `config`：加密配置字典，可包含：
  - `aes_key`：AES 密钥
  - `rsa_public_key`：RSA 公钥
  - `space_key`：KARMACA 空间密钥
  - `karmaca_dimensions`：KARMACA 维度数
  - `use_geometric_proof`：是否使用几何证明

**返回**: 包含各层加密结果的字典

---

#### `decrypt_full(encrypted: Dict[str, Any], config: Dict[str, Any]) -> bytes`

完整多层解密。按照加密的逆序进行多层解密。

**参数**:
- `encrypted`：加密结果字典
- `config`：解密配置字典

**返回**: 解密后的明文数据

---

### 签名验证

#### `sign(data: bytes, key: bytes, method: str = 'rsa') -> bytes`

对数据进行签名。

**参数**:
- `data`：待签名的数据
- `key`：签名私钥（PEM 格式）
- `method`：签名方法，支持 `'rsa'`、`'ec'`，默认为 `'rsa'`

**返回**: 签名数据

---

#### `verify(data: bytes, signature: bytes, key: bytes, method: str = 'rsa') -> bool`

验证签名。

**参数**:
- `data`：原始数据
- `signature`：签名数据
- `key`：验证公钥（PEM 格式）
- `method`：签名方法，支持 `'rsa'`、`'ec'`，默认为 `'rsa'`

**返回**: 验证通过返回 True，否则返回 False

---

### 哈希和 HMAC

#### `hash(data: bytes, algorithm: str = 'sha256') -> bytes`

计算哈希值。

**参数**:
- `data`：输入数据
- `algorithm`：哈希算法，支持 `sha256`、`sha512`、`sha3_256`、`sha3_512`、`blake2b`、`blake2s`、`md5`

**返回**: 哈希值字节

---

#### `hmac(data: bytes, key: bytes, algorithm: str = 'sha256') -> bytes`

计算 HMAC 消息认证码。

**参数**:
- `data`：输入数据
- `key`：密钥
- `algorithm`：哈希算法，默认为 `sha256`

**返回**: HMAC 值字节

---

## KeyAPI 密钥 API

**模块**: `oath_toolchain.sdk.key_api`

### 密钥生成

#### `generate_aes_key(bits: int = 256) -> bytes`

生成 AES 密钥。

**参数**:
- `bits`：密钥位数，支持 128、192、256，默认为 256

**返回**: AES 密钥字节

---

#### `generate_rsa_key(bits: int = 2048) -> Tuple[bytes, bytes]`

生成 RSA 密钥对。

**参数**:
- `bits`：密钥位数，默认为 2048

**返回**: `(私钥 PEM 字节, 公钥 PEM 字节)` 元组

---

#### `generate_nlp_key(text: str, mode: str = 'hybrid', key_length: int = 32) -> bytes`

从自然语言文本生成密钥。

**参数**:
- `text`：输入文本
- `mode`：密钥生成模式，支持 `'semantic'`、`'entropy'`、`'hybrid'`
- `key_length`：密钥长度（字节），默认为 32

**返回**: 生成的密钥字节

---

#### `generate_karmaca_key(seed: bytes = None, dimensions: int = 3) -> bytes`

生成 KARMACA 空间密钥。

**参数**:
- `seed`：种子字节，不提供则随机生成
- `dimensions`：空间维度数，默认为 3

**返回**: KARMACA 空间密钥字节

---

#### `generate_combined_key(sources: List[Dict[str, Any]], key_length: int = 32) -> bytes`

生成组合密钥。从多个密钥源组合生成一个密钥。

**参数**:
- `sources`：密钥源列表，每个源是一个字典，包含：
  - `type`：源类型 (`'bytes'`, `'text'`, `'password'`)
  - `value`：源值
  - `weight`：权重（可选，默认为 1）
- `key_length`：输出密钥长度（字节），默认为 32

**返回**: 组合后的密钥字节

---

### 密钥派生

#### `derive_key(password: str, salt: bytes = None, iterations: int = 100000) -> bytes`

从密码派生密钥。使用 PBKDF2-HMAC-SHA256。

**参数**:
- `password`：密码字符串
- `salt`：盐值，不提供则随机生成
- `iterations`：迭代次数，默认为 100000

**返回**: 派生的密钥字节（32 字节）

---

### 密钥转换

#### `key_to_base64(key: bytes) -> str`

将密钥转换为 Base64 编码字符串。

**参数**:
- `key`：密钥字节

**返回**: Base64 编码的密钥字符串

---

#### `key_from_base64(b64: str) -> bytes`

从 Base64 编码字符串解析密钥。

**参数**:
- `b64`：Base64 编码的密钥字符串

**返回**: 密钥字节

---

### 密钥强度评估

#### `assess_key_strength(key: bytes) -> Dict[str, Any]`

评估密钥强度。

**参数**:
- `key`：待评估的密钥字节

**返回**: 强度评估结果字典，包含：
- `score`：强度分数（0-100）
- `entropy`：熵值（位/字节）
- `length`：密钥长度（字节）
- `strength`：强度等级 (`'weak'`, `'medium'`, `'strong'`, `'very_strong'`)
- `details`：详细评估信息

---

## CAAPI 证书 API

**模块**: `oath_toolchain.sdk.ca_api`

### CA 管理

#### `init_root_ca(name: str = "JMKstudio Root CA") -> Dict[str, Any]`

初始化根 CA。

**参数**:
- `name`：根 CA 名称，默认为 "JMKstudio Root CA"

**返回**: 根 CA 信息字典，包含：
- `success`：是否成功
- `ca_name`：CA 名称
- `certificate`：根证书 PEM 字符串
- `private_key`：根私钥 PEM 字符串

---

#### `create_intermediate_ca(name: str, ca_type: str = "intermediate_ca") -> Dict[str, Any]`

创建中间 CA。

**参数**:
- `name`：中间 CA 名称
- `ca_type`：CA 类型，默认为 "intermediate_ca"

**返回**: 中间 CA 信息字典

---

### 证书操作

#### `issue_certificate(subject: str, cert_type: str = 'end_entity', issuer: str = 'root') -> Dict[str, Any]`

签发证书。

**参数**:
- `subject`：证书主题（通用名称）
- `cert_type`：证书类型，默认为 `'end_entity'`
- `issuer`：签发者，默认为 `'root'`

**返回**: 证书信息字典

---

#### `verify_certificate(cert_pem: bytes) -> Dict[str, Any]`

验证证书。

**参数**:
- `cert_pem`：PEM 格式的证书字节

**返回**: 验证结果字典，包含：
- `success`：是否成功
- `valid`：证书是否有效
- `message`：验证消息

---

#### `revoke_certificate(serial_number: str, reason: str = "unspecified") -> bool`

吊销证书。

**参数**:
- `serial_number`：证书序列号
- `reason`：吊销原因，默认为 "unspecified"

**返回**: 吊销成功返回 True，否则返回 False

---

#### `list_certificates(status: str = None) -> List[Dict[str, Any]]`

列出证书。

**参数**:
- `status`：证书状态过滤，可选

**返回**: 证书列表

---

#### `get_cert_info(cert_pem: bytes) -> Dict[str, Any]`

获取证书信息。

**参数**:
- `cert_pem`：PEM 格式的证书字节

**返回**: 证书信息字典

---

## StegoAPI 隐写 API

**模块**: `oath_toolchain.sdk.stego_api`

### XOR 隐写

#### `embed_xor(secret: bytes, carrier: bytes, key: bytes = None) -> bytes`

使用 XOR 隐写嵌入秘密数据。

**参数**:
- `secret`：秘密数据
- `carrier`：载体数据
- `key`：加密密钥（可选）

**返回**: 隐写后的数据

---

#### `extract_xor(stego: bytes, length: int = 0, key: bytes = None) -> bytes`

从 XOR 隐写数据中提取秘密。

**参数**:
- `stego`：隐写数据
- `length`：秘密长度（不提供则从数据中读取长度前缀）
- `key`：加密密钥（可选）

**返回**: 提取的秘密数据

---

### 文本隐写

#### `embed_text_unicode(secret: bytes, text: str) -> str`

使用 Unicode 隐写将秘密嵌入文本。

**参数**:
- `secret`：秘密数据
- `text`：载体文本

**返回**: 隐写后的文本

---

#### `extract_text_unicode(stego_text: str) -> bytes`

从 Unicode 隐写文本中提取秘密。

**参数**:
- `stego_text`：隐写文本

**返回**: 提取的秘密数据

---

#### `embed_text_whitespace(secret: bytes, text: str) -> str`

使用空格隐写将秘密嵌入文本。

**参数**:
- `secret`：秘密数据
- `text`：载体文本

**返回**: 隐写后的文本

---

#### `extract_text_whitespace(stego_text: str) -> bytes`

从空格隐写文本中提取秘密。

**参数**:
- `stego_text`：隐写文本

**返回**: 提取的秘密数据

---

### 证书隐写

#### `embed_in_cert(secret: bytes, cert_pem: bytes) -> bytes`

将秘密数据嵌入证书扩展字段。

**参数**:
- `secret`：秘密数据
- `cert_pem`：PEM 格式的证书字节

**返回**: 隐写后的证书 PEM 字节

---

#### `extract_from_cert(cert_pem: bytes) -> bytes`

从证书扩展字段中提取秘密数据。

**参数**:
- `cert_pem`：PEM 格式的证书字节

**返回**: 提取的秘密数据

---

### 安全性分析

#### `analyze_carrier(carrier: bytes, carrier_type: str = "binary") -> Dict[str, Any]`

分析载体的隐写容量。

**参数**:
- `carrier`：载体数据
- `carrier_type`：载体类型，默认为 "binary"

**返回**: 分析结果字典

---

#### `estimate_security(original: bytes, stego: bytes) -> Dict[str, Any]`

评估隐写的安全性。

**参数**:
- `original`：原始载体数据
- `stego`：隐写后的数据

**返回**: 安全性评估结果字典

---

## DatasetAPI 数据集 API

**模块**: `oath_toolchain.sdk.dataset_api`

### 数据集管理

#### `create(name: str, data: Any = None, format: str = 'json') -> Dict[str, Any]`

创建数据集。

**参数**:
- `name`：数据集名称
- `data`：数据集内容，可选
- `format`：数据格式，默认为 `'json'`

**返回**: 数据集信息字典，包含：
- `success`：是否成功
- `dataset_id`：数据集 ID
- `dataset`：数据集完整信息

---

#### `delete(dataset_id: str) -> bool`

删除数据集。

**参数**:
- `dataset_id`：数据集 ID

**返回**: 删除成功返回 True，否则返回 False

---

#### `get(dataset_id: str) -> Dict[str, Any]`

获取数据集信息。

**参数**:
- `dataset_id`：数据集 ID

**返回**: 数据集信息字典

---

#### `update(dataset_id: str, data: Any = None, metadata: Dict[str, Any] = None) -> Dict[str, Any]`

更新数据集。

**参数**:
- `dataset_id`：数据集 ID
- `data`：新的数据内容，可选
- `metadata`：新的元数据，可选

**返回**: 更新后的数据集信息字典

---

#### `list_datasets(filters: Dict[str, Any] = None) -> List[Dict[str, Any]]`

列出数据集。

**参数**:
- `filters`：过滤条件字典，可选

**返回**: 数据集列表

---

### 标签管理

#### `search_by_tags(tag_filters: Dict[str, Any]) -> List[Dict[str, Any]]`

按标签搜索数据集。

**参数**:
- `tag_filters`：标签过滤条件字典

**返回**: 匹配的数据集列表

---

#### `add_tag(dataset_id: str, tag: Dict[str, Any]) -> bool`

添加标签到数据集。

**参数**:
- `dataset_id`：数据集 ID
- `tag`：标签字典

**返回**: 添加成功返回 True，否则返回 False

---

#### `remove_tag(dataset_id: str, tag_id: str) -> bool`

从数据集移除标签。

**参数**:
- `dataset_id`：数据集 ID
- `tag_id`：标签 ID

**返回**: 移除成功返回 True，否则返回 False

---

### 版本控制

#### `commit_version(dataset_id: str, message: str = None) -> str`

提交数据集版本。

**参数**:
- `dataset_id`：数据集 ID
- `message`：版本消息，可选

**返回**: 版本号

---

#### `list_versions(dataset_id: str) -> List[Dict[str, Any]]`

列出数据集的所有版本。

**参数**:
- `dataset_id`：数据集 ID

**返回**: 版本列表

---

#### `revert_version(dataset_id: str, version: str) -> Dict[str, Any]`

回滚到指定版本。

**参数**:
- `dataset_id`：数据集 ID
- `version`：目标版本号

**返回**: 回滚后的数据集信息字典

---

## PipelineAPI 管道 API

**模块**: `oath_toolchain.sdk.pipeline_api`

### 管道管理

#### `list_pipelines() -> List[Dict[str, Any]]`

列出所有已注册的管道。

**返回**: 管道信息列表

---

#### `run_pipeline(name: str, input_data: Any) -> Dict[str, Any]`

执行指定的管道。

**参数**:
- `name`：管道名称
- `input_data`：输入数据

**返回**: 管道执行结果字典

---

#### `create_pipeline(name: str, steps: List[Dict[str, Any]]) -> Dict[str, Any]`

创建新的加密管道。

**参数**:
- `name`：管道名称
- `steps`：步骤定义列表，每个步骤包含：
  - `name`：步骤名称
  - `tool`：工具名称
  - `action`：操作类型
  - `params`：参数字典（可选）
  - `input_mapping`：输入映射（可选）
  - `output_key`：输出键名（可选）

**返回**: 管道信息字典

---

### 工作流

#### `create_workflow(name: str, definition: Dict[str, Any]) -> Dict[str, Any]`

创建工作流。

**参数**:
- `name`：工作流名称
- `definition`：工作流定义

**返回**: 工作流信息字典

---

#### `run_workflow(name: str, input_data: Any) -> Dict[str, Any]`

执行工作流。

**参数**:
- `name`：工作流名称
- `input_data`：输入数据

**返回**: 工作流执行结果字典

---

### 安全配置文件

#### `register_profile(profile_name: str, config: Dict[str, Any]) -> None`

注册加密配置文件。

**参数**:
- `profile_name`：配置文件名称
- `config`：加密配置字典

---

#### `encrypt_with_profile(profile_name: str, data: bytes) -> Dict[str, Any]`

使用配置文件加密数据。

**参数**:
- `profile_name`：配置文件名称
- `data`：待加密的数据

**返回**: 加密结果字典

---

#### `decrypt_with_profile(profile_name: str, data: Dict[str, Any]) -> bytes`

使用配置文件解密数据。

**参数**:
- `profile_name`：配置文件名称
- `data`：加密数据字典

**返回**: 解密后的明文数据

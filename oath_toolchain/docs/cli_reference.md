# CLI 参考

本文档提供神誓工具链 CLI 的完整命令参考。

## 目录

- [概述](#概述)
- [全局选项](#全局选项)
- [keygen - 密钥生成](#keygen---密钥生成)
- [encrypt - 加密](#encrypt---加密)
- [decrypt - 解密](#decrypt---解密)
- [sign - 签名](#sign---签名)
- [verify - 验证](#verify---验证)
- [ca - CA证书管理](#ca---ca证书管理)
- [stego - 隐写术](#stego---隐写术)
- [pipeline - 管道编排](#pipeline---管道编排)
- [dataset - 数据集管理](#dataset---数据集管理)
- [tool - 工具管理](#tool---工具管理)

## 概述

神誓工具链提供了丰富的命令行接口，通过 `oath` 命令访问所有功能。

### 基本用法

```bash
oath [OPTIONS] COMMAND [ARGS]...
```

### 查看帮助

```bash
# 查看总帮助
oath --help

# 查看子命令帮助
oath keygen --help
oath encrypt --help
```

### 查看版本

```bash
oath --version
```

---

## 全局选项

| 选项 | 描述 |
|------|------|
| `--help` | 显示帮助信息 |
| `--version` | 显示版本号 |
| `-v, --verbose` | 详细输出模式 |
| `-q, --quiet` | 静默模式，只输出错误 |
| `--config PATH` | 指定配置文件路径 |
| `--output-format TEXT` | 输出格式 (text/json/yaml) |

---

## keygen - 密钥生成

生成各种类型的密钥。

### 用法

```bash
oath keygen [OPTIONS] COMMAND [ARGS]...
```

### 子命令

#### `aes` - 生成 AES 密钥

```bash
oath keygen aes [OPTIONS]
```

**选项**:
- `--bits INTEGER`：密钥位数，可选值：128, 192, 256，默认 256
- `--output PATH`：输出文件路径，不指定则输出到标准输出
- `--base64`：以 Base64 格式输出

**示例**:
```bash
# 生成 256 位 AES 密钥并保存到文件
oath keygen aes --bits 256 --output aes_key.bin

# 生成并以 Base64 输出
oath keygen aes --base64
```

---

#### `rsa` - 生成 RSA 密钥对

```bash
oath keygen rsa [OPTIONS]
```

**选项**:
- `--bits INTEGER`：密钥位数，默认 2048
- `--private-key PATH`：私钥输出文件路径
- `--public-key PATH`：公钥输出文件路径
- `--output PATH`：输出目录（同时保存私钥和公钥）

**示例**:
```bash
# 生成 RSA 密钥对
oath keygen rsa --bits 2048 --private-key rsa_priv.pem --public-key rsa_pub.pem
```

---

#### `nlp` - 从自然语言生成密钥

```bash
oath keygen nlp [OPTIONS]
```

**选项**:
- `--text TEXT`：输入文本（必需）
- `--mode TEXT`：生成模式，可选值：semantic, entropy, hybrid，默认 hybrid
- `--key-length INTEGER`：密钥长度（字节），默认 32
- `--output PATH`：输出文件路径
- `--base64`：以 Base64 格式输出

**示例**:
```bash
# 从文本生成密钥
oath keygen nlp --text "这是一段测试文本" --mode hybrid --output nlp_key.bin
```

---

#### `karmaca` - 生成 KARMACA 空间密钥

```bash
oath keygen karmaca [OPTIONS]
```

**选项**:
- `--dimensions INTEGER`：空间维度数，默认 3
- `--seed TEXT`：种子值（十六进制），不指定则随机生成
- `--output PATH`：输出文件路径
- `--base64`：以 Base64 格式输出

**示例**:
```bash
# 生成 3 维空间密钥
oath keygen karmaca --dimensions 3 --output space_key.bin
```

---

#### `assess` - 评估密钥强度

```bash
oath keygen assess [OPTIONS]
```

**选项**:
- `--key PATH`：密钥文件路径（必需）
- `--base64`：输入为 Base64 编码
- `--output-format TEXT`：输出格式，可选 text/json，默认 text

**示例**:
```bash
# 评估密钥强度
oath keygen assess --key aes_key.bin
```

---

## encrypt - 加密

使用各种算法加密数据。

### 用法

```bash
oath encrypt [OPTIONS] COMMAND [ARGS]...
```

### 子命令

#### `aes` - AES 加密

```bash
oath encrypt aes [OPTIONS]
```

**选项**:
- `--key PATH`：密钥文件路径（必需）
- `--input PATH`：输入文件路径（必需）
- `--output PATH`：输出文件路径，不指定则输出到标准输出
- `--base64-key`：密钥为 Base64 编码

**示例**:
```bash
# 使用 AES 加密文件
oath encrypt aes --key aes_key.bin --input plain.txt --output encrypted.bin
```

---

#### `rsa` - RSA 加密

```bash
oath encrypt rsa [OPTIONS]
```

**选项**:
- `--public-key PATH`：公钥文件路径（必需）
- `--input PATH`：输入文件路径（必需）
- `--output PATH`：输出文件路径

**示例**:
```bash
# 使用 RSA 加密
oath encrypt rsa --public-key rsa_pub.pem --input plain.txt --output encrypted.bin
```

---

#### `karmaca` - KARMACA 空间加密

```bash
oath encrypt karmaca [OPTIONS]
```

**选项**:
- `--key PATH`：空间密钥文件路径（必需）
- `--dimensions INTEGER`：空间维度数，默认 3
- `--input PATH`：输入文件路径（必需）
- `--output PATH`：输出文件路径

**示例**:
```bash
# 使用 KARMACA 加密
oath encrypt karmaca --key space_key.bin --dimensions 3 --input plain.txt --output encrypted.bin
```

---

## decrypt - 解密

解密加密的数据。

### 用法

```bash
oath decrypt [OPTIONS] COMMAND [ARGS]...
```

### 子命令

#### `aes` - AES 解密

```bash
oath decrypt aes [OPTIONS]
```

**选项**:
- `--key PATH`：密钥文件路径（必需）
- `--input PATH`：输入文件路径（必需）
- `--output PATH`：输出文件路径
- `--base64-key`：密钥为 Base64 编码

**示例**:
```bash
# AES 解密
oath decrypt aes --key aes_key.bin --input encrypted.bin --output decrypted.txt
```

---

#### `rsa` - RSA 解密

```bash
oath decrypt rsa [OPTIONS]
```

**选项**:
- `--private-key PATH`：私钥文件路径（必需）
- `--input PATH`：输入文件路径（必需）
- `--output PATH`：输出文件路径

**示例**:
```bash
# RSA 解密
oath decrypt rsa --private-key rsa_priv.pem --input encrypted.bin --output decrypted.txt
```

---

#### `karmaca` - KARMACA 空间解密

```bash
oath decrypt karmaca [OPTIONS]
```

**选项**:
- `--key PATH`：空间密钥文件路径（必需）
- `--dimensions INTEGER`：空间维度数，默认 3
- `--input PATH`：输入文件路径（必需）
- `--output PATH`：输出文件路径

**示例**:
```bash
# KARMACA 解密
oath decrypt karmaca --key space_key.bin --dimensions 3 --input encrypted.bin --output decrypted.txt
```

---

## sign - 签名

对数据进行数字签名。

### 用法

```bash
oath sign [OPTIONS]
```

**选项**:
- `--key PATH`：私钥文件路径（必需）
- `--input PATH`：输入文件路径（必需）
- `--output PATH`：签名输出文件路径，默认 input.sig
- `--method TEXT`：签名方法，可选值：rsa, ec，默认 rsa

**示例**:
```bash
# 对文件进行 RSA 签名
oath sign --key rsa_priv.pem --input document.txt --output signature.bin

# 使用 EC 签名
oath sign --key ec_priv.pem --method ec --input data.txt
```

---

## verify - 验证

验证签名或证书。

### 用法

```bash
oath verify [OPTIONS] COMMAND [ARGS]...
```

### 子命令

#### `signature` - 验证签名

```bash
oath verify signature [OPTIONS]
```

**选项**:
- `--public-key PATH`：公钥文件路径（必需）
- `--signature PATH`：签名文件路径（必需）
- `--input PATH`：原始数据文件路径（必需）
- `--method TEXT`：签名方法，可选值：rsa, ec，默认 rsa

**示例**:
```bash
# 验证签名
oath verify signature --public-key rsa_pub.pem --signature signature.bin --input document.txt
```

---

#### `cert` - 验证证书

```bash
oath verify cert [OPTIONS]
```

**选项**:
- `--cert PATH`：证书文件路径（必需）
- `--ca-cert PATH`：CA 证书文件路径（可选）
- `--output-format TEXT`：输出格式，可选 text/json，默认 text

**示例**:
```bash
# 验证证书
oath verify cert --cert certificate.pem

# 验证证书链
oath verify cert --cert certificate.pem --ca-cert root_ca.pem
```

---

## ca - CA证书管理

管理 CA 证书体系。

### 用法

```bash
oath ca [OPTIONS] COMMAND [ARGS]...
```

### 子命令

#### `init-root` - 初始化根 CA

```bash
oath ca init-root [OPTIONS]
```

**选项**:
- `--name TEXT`：根 CA 名称，默认 "Root CA"
- `--key-bits INTEGER`：密钥位数，默认 2048
- `--validity-days INTEGER`：有效期（天），默认 3650
- `--cert-output PATH`：证书输出路径
- `--key-output PATH`：私钥输出路径

**示例**:
```bash
# 初始化根 CA
oath ca init-root --name "My Root CA" --cert-output root_ca.pem --key-output root_key.pem
```

---

#### `create-intermediate` - 创建中间 CA

```bash
oath ca create-intermediate [OPTIONS]
```

**选项**:
- `--name TEXT`：中间 CA 名称（必需）
- `--parent-ca PATH`：父 CA 证书路径
- `--parent-key PATH`：父 CA 私钥路径
- `--cert-output PATH`：证书输出路径
- `--key-output PATH`：私钥输出路径

**示例**:
```bash
# 创建中间 CA
oath ca create-intermediate --name "Intermediate CA" --parent-ca root_ca.pem --parent-key root_key.pem
```

---

#### `issue` - 签发证书

```bash
oath ca issue [OPTIONS]
```

**选项**:
- `--subject TEXT`：证书主题/通用名称（必需）
- `--type TEXT`：证书类型，可选 end_entity, server, client，默认 end_entity
- `--issuer TEXT`：签发 CA，默认 root
- `--validity-days INTEGER`：有效期（天），默认 365
- `--cert-output PATH`：证书输出路径
- `--key-output PATH`：私钥输出路径

**示例**:
```bash
# 签发服务器证书
oath ca issue --subject "www.example.com" --type server --cert-output server.pem --key-output server_key.pem
```

---

#### `revoke` - 吊销证书

```bash
oath ca revoke [OPTIONS]
```

**选项**:
- `--serial-number TEXT`：证书序列号（必需）
- `--reason TEXT`：吊销原因，默认 unspecified
  - 可选值：unspecified, key_compromise, ca_compromise, affiliation_changed, superseded, cessation_of_operation, certificate_hold, privilege_withdrawn, aa_compromise

**示例**:
```bash
# 吊销证书
oath ca revoke --serial-number 123456 --reason key_compromise
```

---

#### `list` - 列出证书

```bash
oath ca list [OPTIONS]
```

**选项**:
- `--status TEXT`：按状态过滤，可选 valid, revoked, expired
- `--output-format TEXT`：输出格式，可选 text/json，默认 text

**示例**:
```bash
# 列出所有有效证书
oath ca list --status valid

# 以 JSON 格式输出
oath ca list --output-format json
```

---

#### `info` - 显示证书信息

```bash
oath ca info [OPTIONS]
```

**选项**:
- `--cert PATH`：证书文件路径（必需）
- `--output-format TEXT`：输出格式，可选 text/json，默认 text

**示例**:
```bash
# 显示证书信息
oath ca info --cert certificate.pem
```

---

## stego - 隐写术

隐写术相关操作。

### 用法

```bash
oath stego [OPTIONS] COMMAND [ARGS]...
```

### 子命令

#### `embed-xor` - XOR 隐写嵌入

```bash
oath stego embed-xor [OPTIONS]
```

**选项**:
- `--secret PATH`：秘密数据文件路径（必需）
- `--carrier PATH`：载体文件路径（必需）
- `--output PATH`：输出文件路径
- `--key PATH`：加密密钥文件（可选）

**示例**:
```bash
# XOR 隐写
oath stego embed-xor --secret secret.txt --carrier image.png --output stego.png
```

---

#### `extract-xor` - XOR 隐写提取

```bash
oath stego extract-xor [OPTIONS]
```

**选项**:
- `--input PATH`：隐写文件路径（必需）
- `--output PATH`：提取的秘密数据输出路径
- `--length INTEGER`：秘密数据长度（可选）
- `--key PATH`：加密密钥文件（可选）

**示例**:
```bash
# 提取隐写数据
oath stego extract-xor --input stego.png --output extracted_secret.txt
```

---

#### `embed-text` - 文本隐写嵌入

```bash
oath stego embed-text [OPTIONS]
```

**选项**:
- `--secret PATH`：秘密数据文件路径（必需）
- `--text PATH`：载体文本文件路径（必需）
- `--mode TEXT`：隐写模式，可选 unicode, whitespace，默认 unicode
- `--output PATH`：输出文件路径

**示例**:
```bash
# Unicode 零宽字符隐写
oath stego embed-text --secret secret.txt --text cover.txt --mode unicode --output stego.txt
```

---

#### `extract-text` - 文本隐写提取

```bash
oath stego extract-text [OPTIONS]
```

**选项**:
- `--input PATH`：隐写文本文件路径（必需）
- `--mode TEXT`：隐写模式，可选 unicode, whitespace，默认 unicode
- `--output PATH`：提取的秘密数据输出路径

**示例**:
```bash
# 提取文本隐写
oath stego extract-text --input stego.txt --mode unicode --output extracted.txt
```

---

#### `embed-cert` - 证书隐写嵌入

```bash
oath stego embed-cert [OPTIONS]
```

**选项**:
- `--secret PATH`：秘密数据文件路径（必需）
- `--cert PATH`：证书文件路径（必需）
- `--output PATH`：输出证书路径

**示例**:
```bash
# 将数据嵌入证书
oath stego embed-cert --secret secret.txt --cert cert.pem --output stego_cert.pem
```

---

#### `extract-cert` - 证书隐写提取

```bash
oath stego extract-cert [OPTIONS]
```

**选项**:
- `--input PATH`：隐写证书文件路径（必需）
- `--output PATH`：提取的秘密数据输出路径

**示例**:
```bash
# 从证书提取数据
oath stego extract-cert --input stego_cert.pem --output extracted.txt
```

---

#### `analyze` - 分析载体容量

```bash
oath stego analyze [OPTIONS]
```

**选项**:
- `--input PATH`：载体文件路径（必需）
- `--carrier-type TEXT`：载体类型，可选 binary, text, image, audio，默认 binary
- `--output-format TEXT`：输出格式，可选 text/json，默认 text

**示例**:
```bash
# 分析载体容量
oath stego analyze --input image.png --carrier-type image
```

---

## pipeline - 管道编排

管道和工作流管理。

### 用法

```bash
oath pipeline [OPTIONS] COMMAND [ARGS]...
```

### 子命令

#### `list` - 列出管道

```bash
oath pipeline list
```

**示例**:
```bash
# 列出所有管道
oath pipeline list
```

---

#### `run` - 执行管道

```bash
oath pipeline run [OPTIONS]
```

**选项**:
- `--name TEXT`：管道名称（必需）
- `--input PATH`：输入文件路径
- `--output PATH`：输出文件路径
- `--params TEXT`：额外参数（JSON 格式）

**示例**:
```bash
# 执行管道
oath pipeline run --name encrypt_pipeline --input data.bin --output result.bin
```

---

#### `encrypt` - 使用配置文件加密

```bash
oath pipeline encrypt [OPTIONS]
```

**选项**:
- `--profile TEXT`：配置文件名称（必需）
- `--input PATH`：输入文件路径（必需）
- `--output PATH`：输出文件路径
- `--config PATH`：配置文件路径

**示例**:
```bash
# 使用高安全配置加密
oath pipeline encrypt --profile high_security --input data.bin --output encrypted.bin
```

---

#### `decrypt` - 使用配置文件解密

```bash
oath pipeline decrypt [OPTIONS]
```

**选项**:
- `--profile TEXT`：配置文件名称（必需）
- `--input PATH`：输入文件路径（必需）
- `--output PATH`：输出文件路径
- `--config PATH`：配置文件路径

**示例**:
```bash
# 使用配置文件解密
oath pipeline decrypt --profile high_security --input encrypted.bin --output data.bin
```

---

## dataset - 数据集管理

数据集池管理命令。

### 用法

```bash
oath dataset [OPTIONS] COMMAND [ARGS]...
```

### 子命令

#### `create` - 创建数据集

```bash
oath dataset create [OPTIONS]
```

**选项**:
- `--name TEXT`：数据集名称（必需）
- `--data PATH`：数据文件路径
- `--format TEXT`：数据格式，默认 json
- `--output-format TEXT`：输出格式，可选 text/json，默认 text

**示例**:
```bash
# 创建数据集
oath dataset create --name my_dataset --data data.json --format json
```

---

#### `list` - 列出数据集

```bash
oath dataset list [OPTIONS]
```

**选项**:
- `--output-format TEXT`：输出格式，可选 text/json，默认 text

**示例**:
```bash
# 列出所有数据集
oath dataset list
```

---

#### `get` - 获取数据集信息

```bash
oath dataset get [OPTIONS]
```

**选项**:
- `--id TEXT`：数据集 ID（必需）
- `--output-format TEXT`：输出格式，可选 text/json，默认 text

**示例**:
```bash
# 获取数据集信息
oath dataset get --id dataset_123
```

---

#### `delete` - 删除数据集

```bash
oath dataset delete [OPTIONS]
```

**选项**:
- `--id TEXT`：数据集 ID（必需）
- `--force`：强制删除，不确认

**示例**:
```bash
# 删除数据集
oath dataset delete --id dataset_123 --force
```

---

#### `commit` - 提交版本

```bash
oath dataset commit [OPTIONS]
```

**选项**:
- `--id TEXT`：数据集 ID（必需）
- `--message TEXT`：版本消息
- `--output-format TEXT`：输出格式，可选 text/json，默认 text

**示例**:
```bash
# 提交版本
oath dataset commit --id dataset_123 --message "更新数据"
```

---

#### `versions` - 列出版本

```bash
oath dataset versions [OPTIONS]
```

**选项**:
- `--id TEXT`：数据集 ID（必需）
- `--output-format TEXT`：输出格式，可选 text/json，默认 text

**示例**:
```bash
# 列出版本历史
oath dataset versions --id dataset_123
```

---

#### `revert` - 回滚版本

```bash
oath dataset revert [OPTIONS]
```

**选项**:
- `--id TEXT`：数据集 ID（必需）
- `--version TEXT`：目标版本号（必需）
- `--output-format TEXT`：输出格式，可选 text/json，默认 text

**示例**:
```bash
# 回滚到指定版本
oath dataset revert --id dataset_123 --version v1
```

---

#### `search` - 搜索数据集

```bash
oath dataset search [OPTIONS]
```

**选项**:
- `--tag-type TEXT`：标签类型
- `--tag-value TEXT`：标签值
- `--output-format TEXT`：输出格式，可选 text/json，默认 text

**示例**:
```bash
# 按标签搜索
oath dataset search --tag-type 类型 --tag-value 用户数据
```

---

## tool - 工具管理

工具管理相关命令。

### 用法

```bash
oath tool [OPTIONS] COMMAND [ARGS]...
```

### 子命令

#### `list` - 列出工具

```bash
oath tool list [OPTIONS]
```

**选项**:
- `--category TEXT`：按分类过滤
- `--tag TEXT`：按标签过滤
- `--output-format TEXT`：输出格式，可选 text/json，默认 text

**示例**:
```bash
# 列出所有工具
oath tool list

# 按分类列出
oath tool list --category crypto
```

---

#### `info` - 显示工具信息

```bash
oath tool info [OPTIONS] NAME
```

**参数**:
- `NAME`：工具名称（必需）

**选项**:
- `--output-format TEXT`：输出格式，可选 text/json，默认 text

**示例**:
```bash
# 显示工具信息
oath tool info geometric_proof
```

---

#### `execute` - 执行工具

```bash
oath tool execute [OPTIONS] NAME ACTION
```

**参数**:
- `NAME`：工具名称（必需）
- `ACTION`：操作名称（必需）

**选项**:
- `--params TEXT`：参数（JSON 格式）
- `--output-format TEXT`：输出格式，可选 text/json，默认 text

**示例**:
```bash
# 执行工具操作
oath tool execute geometric_proof hash --params '{"data": "test"}'
```

---

## 退出状态码

| 状态码 | 描述 |
|--------|------|
| 0 | 成功 |
| 1 | 通用错误 |
| 2 | 无效参数 |
| 3 | 文件不存在 |
| 4 | 权限错误 |
| 5 | 加密/解密错误 |
| 6 | 签名验证失败 |
| 7 | 证书错误 |

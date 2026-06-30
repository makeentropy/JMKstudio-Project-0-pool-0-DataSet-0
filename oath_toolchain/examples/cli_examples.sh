#!/bin/bash
# CLI 使用示例脚本
# 展示神誓工具链各种 CLI 命令的使用方法

set -e

echo "=============================================="
echo "神誓工具链 - CLI 使用示例"
echo "=============================================="

# 创建临时目录
TMP_DIR=$(mktemp -d)
cd "$TMP_DIR"

echo ""
echo "临时目录: $TMP_DIR"

# 1. 密钥生成命令
echo ""
echo "[1/10] 密钥生成命令"
echo "----------------------------------------------"

echo "生成 AES-256 密钥:"
oath keygen aes --bits 256 --output aes_key.bin || echo "  (示例命令 - 实际使用请确保已安装)"

echo ""
echo "生成 RSA-2048 密钥对:"
oath keygen rsa --bits 2048 --private-key rsa_priv.pem --public-key rsa_pub.pem || echo "  (示例命令)"

echo ""
echo "生成 NLP 密钥:"
oath keygen nlp --text "这是用于生成密钥的文本" --mode hybrid --output nlp_key.bin || echo "  (示例命令)"

echo ""
echo "生成 KARMACA 空间密钥:"
oath keygen karmaca --dimensions 3 --output space_key.bin || echo "  (示例命令)"

# 2. 加密命令
echo ""
echo "[2/10] 加密命令"
echo "----------------------------------------------"

# 创建测试文件
echo "这是测试文件的内容，用于加密演示。" > plain.txt

echo "AES 加密文件:"
oath encrypt aes --key aes_key.bin --input plain.txt --output encrypted_aes.bin || echo "  (示例命令)"

echo ""
echo "KARMACA 空间加密:"
oath encrypt karmaca --key space_key.bin --dimensions 3 --input plain.txt --output encrypted_karmaca.bin || echo "  (示例命令)"

echo ""
echo "RSA 加密:"
oath encrypt rsa --public-key rsa_pub.pem --input plain.txt --output encrypted_rsa.bin || echo "  (示例命令)"

# 3. 解密命令
echo ""
echo "[3/10] 解密命令"
echo "----------------------------------------------"

echo "AES 解密文件:"
oath decrypt aes --key aes_key.bin --input encrypted_aes.bin --output decrypted_aes.txt || echo "  (示例命令)"

echo ""
echo "KARMACA 空间解密:"
oath decrypt karmaca --key space_key.bin --dimensions 3 --input encrypted_karmaca.bin --output decrypted_karmaca.txt || echo "  (示例命令)"

echo ""
echo "RSA 解密:"
oath decrypt rsa --private-key rsa_priv.pem --input encrypted_rsa.bin --output decrypted_rsa.txt || echo "  (示例命令)"

# 4. 签名命令
echo ""
echo "[4/10] 签名命令"
echo "----------------------------------------------"

echo "对文件进行签名:"
oath sign --key rsa_priv.pem --input plain.txt --output signature.bin || echo "  (示例命令)"

echo ""
echo "使用特定算法签名:"
oath sign --key rsa_priv.pem --method rsa --input plain.txt --output signature.bin || echo "  (示例命令)"

# 5. 验证命令
echo ""
echo "[5/10] 验证命令"
echo "----------------------------------------------"

echo "验证签名:"
oath verify --public-key rsa_pub.pem --signature signature.bin --input plain.txt || echo "  (示例命令)"

echo ""
echo "验证证书:"
oath verify cert --cert certificate.pem || echo "  (示例命令)"

# 6. CA 证书命令
echo ""
echo "[6/10] CA 证书命令"
echo "----------------------------------------------"

echo "初始化根 CA:"
oath ca init-root --name "My Root CA" || echo "  (示例命令)"

echo ""
echo "创建中间 CA:"
oath ca create-intermediate --name "Intermediate CA" || echo "  (示例命令)"

echo ""
echo "签发证书:"
oath ca issue --subject "www.example.com" --type end_entity || echo "  (示例命令)"

echo ""
echo "吊销证书:"
oath ca revoke --serial-number 123456 --reason key_compromise || echo "  (示例命令)"

echo ""
echo "列出证书:"
oath ca list --status valid || echo "  (示例命令)"

# 7. 隐写命令
echo ""
echo "[7/10] 隐写命令"
echo "----------------------------------------------"

echo "XOR 隐写嵌入:"
oath stego embed-xor --secret secret.txt --carrier carrier.bin --output stego.bin || echo "  (示例命令)"

echo ""
echo "XOR 隐写提取:"
oath stego extract-xor --input stego.bin --output extracted_secret.txt || echo "  (示例命令)"

echo ""
echo "文本隐写嵌入 (Unicode):"
oath stego embed-text --secret secret.txt --text cover.txt --mode unicode --output stego.txt || echo "  (示例命令)"

echo ""
echo "文本隐写提取:"
oath stego extract-text --input stego.txt --mode unicode --output extracted.txt || echo "  (示例命令)"

echo ""
echo "证书隐写嵌入:"
oath stego embed-cert --secret secret.txt --cert cert.pem --output stego_cert.pem || echo "  (示例命令)"

# 8. 管道命令
echo ""
echo "[8/10] 管道命令"
echo "----------------------------------------------"

echo "列出管道:"
oath pipeline list || echo "  (示例命令)"

echo ""
echo "执行管道:"
oath pipeline run --name encrypt_pipeline --input data.bin --output result.bin || echo "  (示例命令)"

echo ""
echo "使用配置文件加密:"
oath pipeline encrypt --profile high_security --input data.bin --output encrypted.bin || echo "  (示例命令)"

# 9. 数据集命令
echo ""
echo "[9/10] 数据集命令"
echo "----------------------------------------------"

echo "创建数据集:"
oath dataset create --name my_dataset --data data.json --format json || echo "  (示例命令)"

echo ""
echo "列出数据集:"
oath dataset list || echo "  (示例命令)"

echo ""
echo "提交版本:"
oath dataset commit --id dataset_id --message "更新数据" || echo "  (示例命令)"

echo ""
echo "搜索数据集 (按标签):"
oath dataset search --tag-type=类型 --tag-value=用户数据 || echo "  (示例命令)"

# 10. 工具管理命令
echo ""
echo "[10/10] 工具管理命令"
echo "----------------------------------------------"

echo "列出所有工具:"
oath tool list || echo "  (示例命令)"

echo ""
echo "显示工具信息:"
oath tool info geometric_proof || echo "  (示例命令)"

echo ""
echo "显示版本:"
oath --version || echo "  (示例命令)"

echo ""
echo "显示帮助:"
oath --help || echo "  (示例命令)"

# 清理
cd /
rm -rf "$TMP_DIR"

echo ""
echo "=============================================="
echo "CLI 使用示例完成！"
echo "=============================================="
echo ""
echo "提示: 实际使用时，请确保已安装 oath-toolchain:"
echo "  pip install oath-toolchain"
echo ""
echo "更多帮助请查看: oath --help"

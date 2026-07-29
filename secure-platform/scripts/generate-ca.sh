#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
CERTS_DIR="${PROJECT_DIR}/certs"

# shellcheck source=./utils.sh
source "${SCRIPT_DIR}/utils.sh"

CA_SUBJ="/C=CN/ST=Beijing/L=Beijing/O=SecurePlatform/OU=CA/CN=SecurePlatform Root CA"
SERVER_SUBJ="/C=CN/ST=Beijing/L=Beijing/O=SecurePlatform/OU=Server/CN=localhost"
CLIENT_SUBJ="/C=CN/ST=Beijing/L=Beijing/O=SecurePlatform/OU=Client/CN=test-client"
CA_VALIDITY_DAYS=3650
SERVER_VALIDITY_DAYS=825
CLIENT_VALIDITY_DAYS=825

ensure_certs_dir() {
  mkdir -p "${CERTS_DIR}"
  log_info "证书目录: ${CERTS_DIR}"
}

show_cert_fingerprint() {
  local cert_file="$1"
  if [ -f "$cert_file" ]; then
    local fp
    fp=$(openssl x509 -in "$cert_file" -noout -fingerprint -sha256 2>/dev/null || echo "N/A")
    log_info "$(basename "$cert_file") 指纹(SHA256): ${fp}"
  fi
}

set_key_permissions() {
  local key_file="$1"
  if [ -f "$key_file" ]; then
    chmod 600 "$key_file"
    log_info "已设置私钥权限 600: $(basename "$key_file")"
  fi
}

generate_root_ca() {
  local ca_key="${CERTS_DIR}/root-ca.key"
  local ca_crt="${CERTS_DIR}/root-ca.crt"

  if [ -f "$ca_key" ] && [ -f "$ca_crt" ]; then
    log_info "Root CA 已存在，跳过生成"
    show_cert_fingerprint "$ca_crt"
    return 0
  fi

  log_info "生成 Root CA 私钥 (RSA 4096)..."
  openssl genrsa -out "$ca_key" 4096

  log_info "生成自签名 Root CA 证书 (有效期 ${CA_VALIDITY_DAYS} 天)..."
  openssl req -new -x509 \
    -key "$ca_key" \
    -out "$ca_crt" \
    -days "$CA_VALIDITY_DAYS" \
    -sha256 \
    -subj "$CA_SUBJ" \
    -extensions v3_ca \
    -config <(cat <<'EOF'
[req]
distinguished_name = req_distinguished_name
x509_extensions = v3_ca
prompt = no
[req_distinguished_name]
[v3_ca]
subjectKeyIdentifier = hash
authorityKeyIdentifier = keyid:always,issuer
basicConstraints = critical, CA:true, pathlen:2
keyUsage = critical, digitalSignature, cRLSign, keyCertSign
EOF
)

  set_key_permissions "$ca_key"
  show_cert_fingerprint "$ca_crt"
  log_success "Root CA 生成完成"
}

generate_server_cert() {
  local ca_key="${CERTS_DIR}/root-ca.key"
  local ca_crt="${CERTS_DIR}/root-ca.crt"
  local server_key="${CERTS_DIR}/server.key"
  local server_csr="${CERTS_DIR}/server.csr"
  local server_crt="${CERTS_DIR}/server.crt"
  local server_ext="${CERTS_DIR}/.server.ext"

  if [ -f "$server_key" ] && [ -f "$server_crt" ]; then
    log_info "Server 证书已存在，跳过生成"
    show_cert_fingerprint "$server_crt"
    return 0
  fi

  log_info "生成 Server 私钥 (RSA 4096)..."
  openssl genrsa -out "$server_key" 4096

  log_info "生成 Server CSR..."
  openssl req -new \
    -key "$server_key" \
    -out "$server_csr" \
    -subj "$SERVER_SUBJ"

  cat > "$server_ext" <<'EOF'
authorityKeyIdentifier = keyid,issuer
basicConstraints = CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment, dataEncipherment
extendedKeyUsage = serverAuth
subjectAltName = @alt_names
[alt_names]
DNS.1 = localhost
DNS.2 = *.local
IP.1 = 127.0.0.1
EOF

  log_info "CA 签发 Server 证书 (有效期 ${SERVER_VALIDITY_DAYS} 天)..."
  openssl x509 -req \
    -in "$server_csr" \
    -CA "$ca_crt" \
    -CAkey "$ca_key" \
    -CAcreateserial \
    -out "$server_crt" \
    -days "$SERVER_VALIDITY_DAYS" \
    -sha256 \
    -extfile "$server_ext"

  rm -f "$server_csr" "$server_ext" "${CERTS_DIR}/root-ca.srl"

  set_key_permissions "$server_key"
  show_cert_fingerprint "$server_crt"
  log_success "Server 证书生成完成"
}

generate_client_cert() {
  local ca_key="${CERTS_DIR}/root-ca.key"
  local ca_crt="${CERTS_DIR}/root-ca.crt"
  local client_key="${CERTS_DIR}/client.key"
  local client_csr="${CERTS_DIR}/client.csr"
  local client_crt="${CERTS_DIR}/client.crt"
  local client_ext="${CERTS_DIR}/.client.ext"

  if [ -f "$client_key" ] && [ -f "$client_crt" ]; then
    log_info "Client 证书已存在，跳过生成"
    show_cert_fingerprint "$client_crt"
    return 0
  fi

  log_info "生成 Client 私钥 (RSA 4096)..."
  openssl genrsa -out "$client_key" 4096

  log_info "生成 Client CSR..."
  openssl req -new \
    -key "$client_key" \
    -out "$client_csr" \
    -subj "$CLIENT_SUBJ"

  cat > "$client_ext" <<'EOF'
authorityKeyIdentifier = keyid,issuer
basicConstraints = CA:FALSE
keyUsage = critical, digitalSignature, keyEncipherment
extendedKeyUsage = clientAuth
EOF

  log_info "CA 签发 Client 证书 (有效期 ${CLIENT_VALIDITY_DAYS} 天)..."
  openssl x509 -req \
    -in "$client_csr" \
    -CA "$ca_crt" \
    -CAkey "$ca_key" \
    -CAcreateserial \
    -out "$client_crt" \
    -days "$CLIENT_VALIDITY_DAYS" \
    -sha256 \
    -extfile "$client_ext"

  rm -f "$client_csr" "$client_ext" "${CERTS_DIR}/root-ca.srl"

  set_key_permissions "$client_key"
  show_cert_fingerprint "$client_crt"
  log_success "Client 证书生成完成"
}

generate_dhparam() {
  local dhparam="${CERTS_DIR}/dhparam.pem"

  if [ -f "$dhparam" ]; then
    local size
    size=$(wc -c < "$dhparam")
    log_info "DH 参数已存在 ($(file_size_human "$size"))，跳过生成"
    return 0
  fi

  log_info "生成 DH 参数 (2048位)，这可能需要几分钟..."
  openssl dhparam -out "$dhparam" 2048 2>/dev/null

  chmod 600 "$dhparam"
  log_success "DH 参数生成完成"
}

verify_chain() {
  local ca_crt="${CERTS_DIR}/root-ca.crt"
  local server_crt="${CERTS_DIR}/server.crt"
  local client_crt="${CERTS_DIR}/client.crt"

  log_info "验证证书链..."

  if openssl verify -CAfile "$ca_crt" "$server_crt" >/dev/null 2>&1; then
    log_success "Server 证书链验证通过"
  else
    log_error "Server 证书链验证失败"
    return 1
  fi

  if openssl verify -CAfile "$ca_crt" "$client_crt" >/dev/null 2>&1; then
    log_success "Client 证书链验证通过"
  else
    log_error "Client 证书链验证失败"
    return 1
  fi
}

list_certs() {
  log_info "=========================================="
  log_info "  已生成的证书文件"
  log_info "=========================================="
  ls -lh "${CERTS_DIR}"/
  log_info "=========================================="
}

main() {
  log_info "=========================================="
  log_info "  Secure Platform 证书生成脚本"
  log_info "=========================================="

  ensure_certs_dir
  generate_root_ca
  generate_server_cert
  generate_client_cert
  generate_dhparam
  verify_chain
  list_certs

  log_success "证书生成全部完成！"
}

main "$@"

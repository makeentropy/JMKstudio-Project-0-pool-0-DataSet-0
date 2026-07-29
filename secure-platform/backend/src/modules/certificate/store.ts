import { X509Certificate, createCipheriv, createDecipheriv, scryptSync, randomBytes } from 'node:crypto';
import { CertificateInfo, CertificateStatus, CertificateType, CertificateStoreError } from './types';

interface StoreEntry {
  certPem: string;
  privateKeyPem?: string;
  metadata?: Record<string, unknown>;
  createdAt: Date;
}

interface ExportedEntry {
  certPem: string;
  privateKeyB64?: string;
  encrypted?: boolean;
  iv?: string;
  salt?: string;
  metadata?: Record<string, unknown>;
  createdAt: string;
}

interface ExportedStore {
  version: number;
  encrypted: boolean;
  entries: Record<string, ExportedEntry>;
  createdAt: string;
}

export class CertificateStore {
  private entries: Map<string, StoreEntry> = new Map();
  private x509Cache: Map<string, X509Certificate> = new Map();

  public storeCertificate(
    alias: string,
    certPem: string,
    privateKeyPem?: string,
    metadata?: Record<string, unknown>
  ): void {
    if (!alias || alias.trim().length === 0) {
      throw new CertificateStoreError('证书别名不能为空');
    }

    try {
      new X509Certificate(Buffer.from(certPem));
    } catch (cause) {
      throw new CertificateStoreError('无效的证书PEM数据', 'INVALID_CERT_PEM', cause);
    }

    if (this.entries.has(alias)) {
      throw new CertificateStoreError(`证书别名已存在: ${alias}`, 'ALIAS_EXISTS');
    }

    this.entries.set(alias, {
      certPem,
      privateKeyPem,
      metadata,
      createdAt: new Date(),
    });

    this.x509Cache.delete(alias);
  }

  public getCertificate(alias: string): { pem: string; x509: X509Certificate } | null {
    const entry = this.entries.get(alias);
    if (!entry) return null;

    if (!this.x509Cache.has(alias)) {
      try {
        this.x509Cache.set(alias, new X509Certificate(Buffer.from(entry.certPem)));
      } catch (cause) {
        throw new CertificateStoreError(`证书解析失败: ${alias}`, 'CERT_PARSE_ERROR', cause);
      }
    }

    return {
      pem: entry.certPem,
      x509: this.x509Cache.get(alias)!,
    };
  }

  public getPrivateKey(alias: string): string | null {
    const entry = this.entries.get(alias);
    return entry?.privateKeyPem ?? null;
  }

  public getCertificateInfo(alias: string): CertificateInfo | null {
    const cert = this.getCertificate(alias);
    if (!cert) return null;

    const { x509 } = cert;
    const now = new Date();
    let status = CertificateStatus.VALID;

    if (now < new Date(x509.validFrom)) {
      status = CertificateStatus.UNKNOWN;
    } else if (now > new Date(x509.validTo)) {
      status = CertificateStatus.EXPIRED;
    }

    return {
      serialNumber: x509.serialNumber,
      subject: x509.subject,
      issuer: x509.issuer,
      notBefore: new Date(x509.validFrom),
      notAfter: new Date(x509.validTo),
      certificateType: this.inferCertificateType(x509),
      publicKeyFingerprint: this.formatFingerprint(x509.fingerprint256),
      status,
      pemData: cert.pem,
    };
  }

  public deleteCertificate(alias: string): void {
    if (!this.entries.has(alias)) {
      throw new CertificateStoreError(`证书不存在: ${alias}`, 'NOT_FOUND');
    }
    this.entries.delete(alias);
    this.x509Cache.delete(alias);
  }

  public listCertificates(): string[] {
    return Array.from(this.entries.keys());
  }

  public hasCertificate(alias: string): boolean {
    return this.entries.has(alias);
  }

  public updateMetadata(alias: string, metadata: Record<string, unknown>): void {
    const entry = this.entries.get(alias);
    if (!entry) {
      throw new CertificateStoreError(`证书不存在: ${alias}`, 'NOT_FOUND');
    }
    entry.metadata = { ...entry.metadata, ...metadata };
  }

  public getMetadata(alias: string): Record<string, unknown> | null {
    const entry = this.entries.get(alias);
    return entry?.metadata ?? null;
  }

  public exportStore(password?: string): string {
    const entries: Record<string, ExportedEntry> = {};
    const isEncrypted = !!password;

    for (const [alias, entry] of this.entries.entries()) {
      const exported: ExportedEntry = {
        certPem: entry.certPem,
        metadata: entry.metadata,
        createdAt: entry.createdAt.toISOString(),
      };

      if (entry.privateKeyPem) {
        if (isEncrypted && password) {
          const { encrypted, iv, salt } = this.encryptPrivateKey(entry.privateKeyPem, password);
          exported.privateKeyB64 = encrypted;
          exported.encrypted = true;
          exported.iv = iv;
          exported.salt = salt;
        } else {
          exported.privateKeyB64 = Buffer.from(entry.privateKeyPem, 'utf8').toString('base64');
        }
      }

      entries[alias] = exported;
    }

    const store: ExportedStore = {
      version: 1,
      encrypted: isEncrypted,
      entries,
      createdAt: new Date().toISOString(),
    };

    return JSON.stringify(store);
  }

  public importStore(jsonData: string, password?: string): void {
    let store: ExportedStore;
    try {
      store = JSON.parse(jsonData) as ExportedStore;
    } catch (cause) {
      throw new CertificateStoreError('无效的存储数据格式', 'INVALID_FORMAT', cause);
    }

    if (store.version !== 1) {
      throw new CertificateStoreError(`不支持的存储版本: ${store.version}`, 'UNSUPPORTED_VERSION');
    }

    Object.entries(store.entries).forEach(([alias, entry]) => {
      let privateKeyPem: string | undefined;

      if (entry.privateKeyB64) {
        if (entry.encrypted) {
          if (!password) {
            throw new CertificateStoreError(`证书${alias} 的私钥已加密，需要提供密码`);
          }
          if (!entry.iv || !entry.salt) {
            throw new CertificateStoreError(`证书${alias} 缺少加密参数`);
          }
          privateKeyPem = this.decryptPrivateKey(entry.privateKeyB64, entry.iv, entry.salt, password);
        } else {
          privateKeyPem = Buffer.from(entry.privateKeyB64, 'base64').toString('utf8');
        }
      }

      if (this.entries.has(alias)) {
        throw new CertificateStoreError(`导入失败，别名已存在: ${alias}`, 'ALIAS_EXISTS');
      }

      this.entries.set(alias, {
        certPem: entry.certPem,
        privateKeyPem,
        metadata: entry.metadata,
        createdAt: new Date(entry.createdAt),
      });
    });
  }

  public clear(): void {
    this.entries.clear();
    this.x509Cache.clear();
  }

  public get size(): number {
    return this.entries.size;
  }

  private inferCertificateType(x509: X509Certificate): CertificateType {
    try {
      if (x509.ca) {
        return x509.subject === x509.issuer ? CertificateType.ROOT_CA : CertificateType.INTERMEDIATE_CA;
      }

      const keyUsage = x509.keyUsage || [];
      if (keyUsage.length > 0) {
        if (x509.subject.includes('CN=') && (x509.subject.includes('Server') || x509.subject.includes('server'))) {
          return CertificateType.SERVER;
        }
        if (x509.subject.includes('CN=') && (x509.subject.includes('Client') || x509.subject.includes('client'))) {
          return CertificateType.CLIENT;
        }
      }

      return CertificateType.END_ENTITY;
    } catch {
      return CertificateType.END_ENTITY;
    }
  }

  private formatFingerprint(fp: string): string {
    return fp.toUpperCase();
  }

  private encryptPrivateKey(privateKeyPem: string, password: string): { encrypted: string; iv: string; salt: string } {
    const salt = randomBytes(16).toString('hex');
    const iv = randomBytes(16).toString('hex');
    const key = scryptSync(password, salt, 32) as unknown as Buffer;

    const cipher = createCipheriv('aes-256-gcm', key, Buffer.from(iv, 'hex') as Buffer);
    let encrypted = cipher.update(privateKeyPem, 'utf8', 'base64');
    encrypted += cipher.final('base64');

    const authTag = cipher.getAuthTag().toString('base64');
    return {
      encrypted: encrypted + '.' + authTag,
      iv,
      salt,
    };
  }

  private decryptPrivateKey(encryptedB64: string, ivHex: string, saltHex: string, password: string): string {
    const [data, authTagB64] = encryptedB64.split('.');
    if (!data || !authTagB64) {
      throw new CertificateStoreError('无效的加密私钥格式');
    }

    const key = scryptSync(password, saltHex, 32) as unknown as Buffer;
    const decipher = createDecipheriv('aes-256-gcm', key, Buffer.from(ivHex, 'hex') as Buffer);
    decipher.setAuthTag(Buffer.from(authTagB64, 'base64'));

    let decrypted = decipher.update(data, 'base64', 'utf8');
    decrypted += decipher.final('utf8');
    return decrypted;
  }
}

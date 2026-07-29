import { X509Certificate, createVerify, createHash, KeyObject } from 'node:crypto';
import { CertificateInfo, CertificateStatus, CertificateType, CertificateValidationError } from './types';

export class CertificateVerifier {
  private trustedCAs: X509Certificate[] = [];
  private trustedCaInfos: Map<string, CertificateInfo> = new Map();

  public addTrustedCa(certPem: string): void {
    try {
      const x509 = new X509Certificate(Buffer.from(certPem));
      this.trustedCAs.push(x509);
      this.trustedCaInfos.set(x509.serialNumber, this.buildCertInfo(x509));
    } catch (cause) {
      throw new CertificateValidationError(`添加信任CA失败: ${cause instanceof Error ? cause.message : String(cause)}`, cause);
    }
  }

  public removeTrustedCa(serialNumber: string): boolean {
    const index = this.trustedCAs.findIndex(ca => ca.serialNumber === serialNumber);
    if (index >= 0) {
      this.trustedCAs.splice(index, 1);
      this.trustedCaInfos.delete(serialNumber);
      return true;
    }
    return false;
  }

  public listTrustedCAs(): CertificateInfo[] {
    return Array.from(this.trustedCaInfos.values());
  }

  public clearTrustedCAs(): void {
    this.trustedCAs = [];
    this.trustedCaInfos.clear();
  }

  public verifyChain(
    certPem: string,
    intermediateCerts: string[] = []
  ): [boolean, string] {
    try {
      const endCert = this.parsePem(certPem);
      const intermediates = intermediateCerts.map(p => this.parsePem(p));
      const chain: X509Certificate[] = [endCert];

      let current = endCert;
      let foundTrusted = false;

      for (const trusted of this.trustedCAs) {
        if (current.checkIssued(trusted)) {
          if (current.verify(trusted.publicKey)) {
            chain.push(trusted);
            foundTrusted = true;
            break;
          }
        }
      }

      if (!foundTrusted) {
        for (const intermediate of intermediates) {
          if (current.checkIssued(intermediate)) {
            if (current.verify(intermediate.publicKey)) {
              chain.push(intermediate);
              current = intermediate;

              for (const trusted of this.trustedCAs) {
                if (current.checkIssued(trusted)) {
                  if (current.verify(trusted.publicKey)) {
                    chain.push(trusted);
                    foundTrusted = true;
                    break;
                  }
                }
              }
              if (foundTrusted) break;
            }
          }
        }
      }

      if (!foundTrusted) {
        return [false, '证书链无法追溯到受信任的根CA'];
      }

      const now = new Date();
      for (let i = 0; i < chain.length; i++) {
        const cert = chain[i];
        const validFrom = new Date(cert.validFrom);
        const validTo = new Date(cert.validTo);

        if (now < validFrom) {
          return [false, `证书链第${i + 1}层证书尚未生效`];
        }
        if (now > validTo) {
          return [false, `证书链第${i + 1}层证书已过期`];
        }
      }

      return [true, `证书链验证通过，共${chain.length}层`];
    } catch (cause) {
      return [false, `证书链验证异常: ${cause instanceof Error ? cause.message : String(cause)}`];
    }
  }

  public verifySignature(
    data: Buffer | string,
    signature: Buffer | string,
    certPem: string,
    hashAlgo: string = 'sha256'
  ): boolean {
    try {
      const x509 = this.parsePem(certPem);
      const publicKey = x509.publicKey;

      const verify = createVerify(hashAlgo);
      verify.update(typeof data === 'string' ? Buffer.from(data) : data);
      verify.end();

      return verify.verify(publicKey, typeof signature === 'string' ? Buffer.from(signature, 'base64') : signature);
    } catch {
      return false;
    }
  }

  public parsePem(pem: string): X509Certificate {
    try {
      return new X509Certificate(Buffer.from(pem));
    } catch (cause) {
      throw new CertificateValidationError(`PEM解析失败: ${cause instanceof Error ? cause.message : String(cause)}`, cause);
    }
  }

  public getFingerprint(certPem: string, algo: string = 'sha256'): string {
    const x509 = this.parsePem(certPem);

    if (algo.toLowerCase() === 'sha256') {
      return x509.fingerprint256.toUpperCase();
    }
    if (algo.toLowerCase() === 'sha1') {
      return x509.fingerprint.toUpperCase();
    }

    const hash = createHash(algo);
    hash.update(x509.raw);
    const digest = hash.digest('hex');
    return digest.match(/.{2}/g)!.join(':').toUpperCase();
  }

  public getCertificateInfo(certPem: string): CertificateInfo {
    const x509 = this.parsePem(certPem);
    return this.buildCertInfo(x509, certPem);
  }

  public isSelfSigned(certPem: string): boolean {
    const x509 = this.parsePem(certPem);
    return x509.subject === x509.issuer && x509.verify(x509.publicKey);
  }

  public checkValidity(certPem: string): { valid: boolean; reason?: string } {
    const x509 = this.parsePem(certPem);
    const now = new Date();
    const validFrom = new Date(x509.validFrom);
    const validTo = new Date(x509.validTo);

    if (now < validFrom) {
      return { valid: false, reason: '证书尚未生效' };
    }
    if (now > validTo) {
      return { valid: false, reason: '证书已过期' };
    }
    return { valid: true };
  }

  private buildCertInfo(x509: X509Certificate, pemData?: string): CertificateInfo {
    const now = new Date();
    const validFrom = new Date(x509.validFrom);
    const validTo = new Date(x509.validTo);

    let status = CertificateStatus.VALID;
    if (now < validFrom) {
      status = CertificateStatus.UNKNOWN;
    } else if (now > validTo) {
      status = CertificateStatus.EXPIRED;
    }

    let certificateType = CertificateType.END_ENTITY;
    try {
      if (x509.ca) {
        certificateType = x509.subject === x509.issuer ? CertificateType.ROOT_CA : CertificateType.INTERMEDIATE_CA;
      } else {
        const keyUsage = x509.keyUsage || [];
        if (keyUsage.length > 0) {
          if (x509.subject.includes('CN=') && (x509.subject.includes('Server') || x509.subject.includes('server'))) {
            certificateType = CertificateType.SERVER;
          } else if (x509.subject.includes('CN=') && (x509.subject.includes('Client') || x509.subject.includes('client'))) {
            certificateType = CertificateType.CLIENT;
          }
        }
      }
    } catch {
      // ignore
    }

    return {
      serialNumber: x509.serialNumber,
      subject: x509.subject,
      issuer: x509.issuer,
      notBefore: validFrom,
      notAfter: validTo,
      certificateType,
      publicKeyFingerprint: x509.fingerprint256.toUpperCase(),
      status,
      pemData,
    };
  }

  public getPublicKey(certPem: string): KeyObject {
    const x509 = this.parsePem(certPem);
    return x509.publicKey;
  }

  public getPublicKeyAsPem(certPem: string): string {
    const x509 = this.parsePem(certPem);
    return x509.publicKey.export({ type: 'spki', format: 'pem' }) as string;
  }
}

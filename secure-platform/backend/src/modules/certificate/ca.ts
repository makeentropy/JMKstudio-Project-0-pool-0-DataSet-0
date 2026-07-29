import { generateKeyPairSync, createSign, createVerify, X509Certificate, randomBytes } from 'node:crypto';
import {
  CertificateStatus,
  CertificateType,
  CertificateInfo,
  RevocationReason,
  CertificateError,
  CertificateSigningError,
  CertificateValidationError,
  CertificateRevocationError,
} from './types';

interface RevocationEntry {
  serialNumber: string;
  reason: RevocationReason;
  date: Date;
}

interface IssuedCertificate {
  pem: string;
  info: CertificateInfo;
  x509: X509Certificate;
}

export class CertificateAuthority {
  private privateKeyPem: string | null = null;
  private caCertificatePem: string | null = null;
  private caX509: X509Certificate | null = null;
  private issuedCertificates: Map<string, IssuedCertificate> = new Map();
  private revocationList: Map<string, RevocationEntry> = new Map();
  private caName: string = '';
  private initialized: boolean = false;

  public initialize(name: string, keySize: number = 4096, validityDays: number = 3650): void {
    if (this.initialized) {
      throw new CertificateError('CA已初始化，如需重新初始化请先reset');
    }

    try {
      const { privateKey, publicKey } = generateKeyPairSync('rsa', {
        modulusLength: keySize,
        publicKeyEncoding: {
          type: 'spki',
          format: 'pem',
        },
        privateKeyEncoding: {
          type: 'pkcs8',
          format: 'pem',
        },
      });

      this.privateKeyPem = privateKey;
      this.caName = name;

      const subject = `CN=${name}, O=SecurePlatform, OU=Certificate Authority`;
      const issuer = subject;
      const serialNumber = this.generateSerialNumber();
      const notBefore = new Date();
      const notAfter = new Date(notBefore.getTime() + validityDays * 24 * 60 * 60 * 1000);

      this.caCertificatePem = this.createSelfSignedCert(
        serialNumber,
        subject,
        issuer,
        notBefore,
        notAfter,
        publicKey,
        CertificateType.ROOT_CA,
        [],
        []
      );

      this.caX509 = new X509Certificate(Buffer.from(this.caCertificatePem));
      this.initialized = true;
    } catch (cause) {
      throw new CertificateError(`CA初始化失败: ${cause instanceof Error ? cause.message : String(cause)}`, 'CA_INIT_ERROR', cause);
    }
  }

  public reset(): void {
    this.privateKeyPem = null;
    this.caCertificatePem = null;
    this.caX509 = null;
    this.issuedCertificates.clear();
    this.revocationList.clear();
    this.caName = '';
    this.initialized = false;
  }

  public get isInitialized(): boolean {
    return this.initialized;
  }

  public get caName_(): string {
    return this.caName;
  }

  public issueCertificate(
    subjectName: string,
    type: CertificateType,
    validityDays: number = 365,
    sanDns: string[] = [],
    sanIps: string[] = []
  ): { certificatePem: string; privateKeyPem: string; info: CertificateInfo } {
    this.ensureInitialized();

    try {
      const { privateKey, publicKey } = generateKeyPairSync('rsa', {
        modulusLength: 2048,
        publicKeyEncoding: {
          type: 'spki',
          format: 'pem',
        },
        privateKeyEncoding: {
          type: 'pkcs8',
          format: 'pem',
        },
      });

      const serialNumber = this.generateSerialNumber();
      const subject = this.buildSubjectDN(subjectName, type);
      const issuer = this.caX509!.subject;
      const notBefore = new Date();
      const notAfter = new Date(notBefore.getTime() + validityDays * 24 * 60 * 60 * 1000);

      const certPem = this.signCertificate(
        serialNumber,
        subject,
        issuer,
        notBefore,
        notAfter,
        publicKey,
        type,
        sanDns,
        sanIps
      );

      const x509 = new X509Certificate(Buffer.from(certPem));
      const fingerprint = this.getFingerprint(x509);

      const info: CertificateInfo = {
        serialNumber,
        subject,
        issuer,
        notBefore,
        notAfter,
        certificateType: type,
        publicKeyFingerprint: fingerprint,
        status: CertificateStatus.VALID,
        pemData: certPem,
      };

      this.issuedCertificates.set(serialNumber, { pem: certPem, info, x509 });

      return {
        certificatePem: certPem,
        privateKeyPem: privateKey,
        info,
      };
    } catch (cause) {
      if (cause instanceof CertificateError) throw cause;
      throw new CertificateSigningError(`证书签发失败: ${cause instanceof Error ? cause.message : String(cause)}`, cause);
    }
  }

  public verifyCertificate(certPem: string, checkRevocation: boolean = true): [boolean, string] {
    this.ensureInitialized();

    try {
      const x509 = new X509Certificate(Buffer.from(certPem));

      if (!x509.checkIssued(this.caX509!)) {
        return [false, '证书不是由此CA签发'];
      }

      if (!x509.verify(this.caX509!.publicKey)) {
        return [false, '证书签名验证失败'];
      }

      const now = new Date();
      if (now < new Date(x509.validFrom)) {
        return [false, '证书尚未生效'];
      }
      if (now > new Date(x509.validTo)) {
        return [false, '证书已过期'];
      }

      if (checkRevocation) {
        const serialNumber = x509.serialNumber;
        const revocation = this.revocationList.get(serialNumber);
        if (revocation) {
          return [false, `证书已吊销: 原因代码=${revocation.reason}, 吊销时间=${revocation.date.toISOString()}`];
        }
      }

      return [true, '证书验证通过'];
    } catch (cause) {
      return [false, `证书验证异常: ${cause instanceof Error ? cause.message : String(cause)}`];
    }
  }

  public revokeCertificate(serialNumber: string, reason: RevocationReason = RevocationReason.UNSPECIFIED): void {
    this.ensureInitialized();

    const cert = this.issuedCertificates.get(serialNumber);
    if (!cert) {
      throw new CertificateRevocationError(`证书不存在: 序列号=${serialNumber}`);
    }

    if (this.revocationList.has(serialNumber)) {
      throw new CertificateRevocationError(`证书已吊销: 序列号=${serialNumber}`);
    }

    this.revocationList.set(serialNumber, {
      serialNumber,
      reason,
      date: new Date(),
    });

    cert.info.status = CertificateStatus.REVOKED;
    cert.info.revocationReason = reason;
    cert.info.revocationDate = new Date();
  }

  public listCertificates(status?: CertificateStatus, type?: CertificateType): CertificateInfo[] {
    const results: CertificateInfo[] = [];

    for (const cert of this.issuedCertificates.values()) {
      let info = { ...cert.info };

      const x509 = cert.x509;
      if (info.status === CertificateStatus.VALID) {
        const now = new Date();
        if (now > new Date(x509.validTo)) {
          info.status = CertificateStatus.EXPIRED;
          cert.info.status = CertificateStatus.EXPIRED;
        }
      }

      if (status && info.status !== status) continue;
      if (type && info.certificateType !== type) continue;

      results.push(info);
    }

    return results.sort((a, b) => a.notAfter.getTime() - b.notAfter.getTime());
  }

  public getCertificateInfo(serialNumber: string): CertificateInfo | null {
    const cert = this.issuedCertificates.get(serialNumber);
    if (!cert) return null;

    const info = { ...cert.info };
    const now = new Date();
    if (info.status === CertificateStatus.VALID && now > new Date(cert.x509.validTo)) {
      info.status = CertificateStatus.EXPIRED;
    }

    return info;
  }

  public exportCaCertificate(pem: boolean = true): Buffer {
    this.ensureInitialized();

    if (pem) {
      return Buffer.from(this.caCertificatePem!);
    }

    return this.caX509!.raw;
  }

  public exportCaPrivateKey(password?: string): Buffer {
    this.ensureInitialized();

    if (password) {
      const { privateKey } = generateKeyPairSync('rsa', {
        modulusLength: 2048,
        publicKeyEncoding: { type: 'spki', format: 'pem' },
        privateKeyEncoding: {
          type: 'pkcs8',
          format: 'pem',
          cipher: 'aes-256-cbc',
          passphrase: password,
        },
      });
      void privateKey;
      throw new CertificateError('带密码导出私钥需使用加密PKCS#8格式，请使用专业加密库实现');
    }

    return Buffer.from(this.privateKeyPem!);
  }

  public getCaInfo(): CertificateInfo | null {
    if (!this.caX509) return null;

    return {
      serialNumber: this.caX509.serialNumber,
      subject: this.caX509.subject,
      issuer: this.caX509.issuer,
      notBefore: new Date(this.caX509.validFrom),
      notAfter: new Date(this.caX509.validTo),
      certificateType: CertificateType.ROOT_CA,
      publicKeyFingerprint: this.getFingerprint(this.caX509),
      status: new Date() > new Date(this.caX509.validTo) ? CertificateStatus.EXPIRED : CertificateStatus.VALID,
      pemData: this.caCertificatePem!,
    };
  }

  public getRevocationList(): Array<{ serialNumber: string; reason: RevocationReason; date: Date }> {
    return Array.from(this.revocationList.values());
  }

  private ensureInitialized(): void {
    if (!this.initialized || !this.privateKeyPem || !this.caX509) {
      throw new CertificateError('CA尚未初始化，请先调用initialize()', 'CA_NOT_INITIALIZED');
    }
  }

  private generateSerialNumber(): string {
    const bytes = randomBytes(16);
    return bytes.toString('hex').toUpperCase();
  }

  private buildSubjectDN(commonName: string, type: CertificateType): string {
    const ouMap: Record<CertificateType, string> = {
      [CertificateType.ROOT_CA]: 'Certificate Authority',
      [CertificateType.INTERMEDIATE_CA]: 'Intermediate CA',
      [CertificateType.END_ENTITY]: 'End Entity',
      [CertificateType.SERVER]: 'Server Authentication',
      [CertificateType.CLIENT]: 'Client Authentication',
      [CertificateType.CODE_SIGNING]: 'Code Signing',
    };
    return `CN=${commonName}, O=SecurePlatform, OU=${ouMap[type] || 'General'}`;
  }

  private getFingerprint(x509: X509Certificate, algo: string = 'sha256'): string {
    return x509.fingerprint256.split(':').join(':').toUpperCase();
  }

  private buildDistinguishedName(dn: string): Map<string, string> {
    const result = new Map<string, string>();
    const parts = dn.split(', ');
    for (const part of parts) {
      const [key, ...rest] = part.split('=');
      if (key && rest.length > 0) {
        result.set(key.trim(), rest.join('=').trim());
      }
    }
    return result;
  }

  private createSelfSignedCert(
    serialNumber: string,
    subject: string,
    issuer: string,
    notBefore: Date,
    notAfter: Date,
    publicKeyPem: string,
    type: CertificateType,
    sanDns: string[],
    sanIps: string[]
  ): string {
    const tbsCert = this.buildTBSCertificate(
      serialNumber,
      subject,
      issuer,
      notBefore,
      notAfter,
      publicKeyPem,
      type,
      sanDns,
      sanIps,
      true
    );

    const sign = createSign('sha256');
    sign.update(tbsCert);
    const signature = sign.sign(this.privateKeyPem!);

    return this.buildPemCertificate(tbsCert, signature, 'sha256');
  }

  private signCertificate(
    serialNumber: string,
    subject: string,
    issuer: string,
    notBefore: Date,
    notAfter: Date,
    publicKeyPem: string,
    type: CertificateType,
    sanDns: string[],
    sanIps: string[]
  ): string {
    const tbsCert = this.buildTBSCertificate(
      serialNumber,
      subject,
      issuer,
      notBefore,
      notAfter,
      publicKeyPem,
      type,
      sanDns,
      sanIps,
      type === CertificateType.INTERMEDIATE_CA
    );

    const sign = createSign('sha256');
    sign.update(tbsCert);
    const signature = sign.sign(this.privateKeyPem!);

    return this.buildPemCertificate(tbsCert, signature, 'sha256');
  }

  private buildTBSCertificate(
    serialNumberHex: string,
    subject: string,
    issuer: string,
    notBefore: Date,
    notAfter: Date,
    publicKeyPem: string,
    type: CertificateType,
    sanDns: string[],
    sanIps: string[],
    isCA: boolean
  ): Buffer {
    const serialBytes = Buffer.from(serialNumberHex, 'hex');
    const subjectMap = this.buildDistinguishedName(subject);
    const issuerMap = this.buildDistinguishedName(issuer);

    const subjectDN = this.encodeDN(subjectMap);
    const issuerDN = this.encodeDN(issuerMap);
    const validity = this.encodeValidity(notBefore, notAfter);
    const spki = this.extractSPKI(publicKeyPem);
    const extensions = this.buildExtensions(type, sanDns, sanIps, isCA, spki);

    const tbsParts: Buffer[] = [];

    tbsParts.push(Buffer.from([0xa0, 0x03, 0x02, 0x01, 0x02]));

    tbsParts.push(this.encodeTag(0x02, serialBytes));

    tbsParts.push(this.encodeTag(0x0a, Buffer.from([0x00])));

    tbsParts.push(issuerDN);

    tbsParts.push(validity);

    tbsParts.push(subjectDN);

    tbsParts.push(spki);

    if (extensions.length > 0) {
      tbsParts.push(this.encodeTag(0xa3, this.encodeSequence(extensions)));
    }

    return this.encodeTag(0x30, Buffer.concat(tbsParts));
  }

  private buildPemCertificate(tbsCert: Buffer, signature: Buffer, _hashAlgo: string): string {
    const algorithmIdentifier = this.encodeSequence([
      this.encodeOID([1, 2, 840, 113549, 1, 1, 11]),
      Buffer.from([0x05, 0x00]),
    ]);

    const certDER = this.encodeSequence([
      tbsCert,
      algorithmIdentifier,
      this.encodeBitString(signature),
    ]);

    const base64 = certDER.toString('base64');
    const lines: string[] = ['-----BEGIN CERTIFICATE-----'];
    for (let i = 0; i < base64.length; i += 64) {
      lines.push(base64.slice(i, i + 64));
    }
    lines.push('-----END CERTIFICATE-----');
    return lines.join('\n') + '\n';
  }

  private buildExtensions(
    type: CertificateType,
    sanDns: string[],
    sanIps: string[],
    isCA: boolean,
    spki: Buffer
  ): Buffer[] {
    const extensions: Buffer[] = [];

    const basicConstraints = this.buildBasicConstraints(isCA);
    extensions.push(this.buildExtension([2, 5, 29, 19], true, basicConstraints));

    const keyUsage = this.buildKeyUsage(type, isCA);
    extensions.push(this.buildExtension([2, 5, 29, 15], true, keyUsage));

    if (!isCA) {
      const extKeyUsage = this.buildExtendedKeyUsage(type);
      if (extKeyUsage) {
        extensions.push(this.buildExtension([2, 5, 29, 37], false, extKeyUsage));
      }
    }

    if (sanDns.length > 0 || sanIps.length > 0) {
      const san = this.buildSubjectAltName(sanDns, sanIps);
      extensions.push(this.buildExtension([2, 5, 29, 17], false, san));
    }

    const ski = this.buildSubjectKeyIdentifier(spki);
    extensions.push(this.buildExtension([2, 5, 29, 14], false, ski));

    return extensions;
  }

  private buildExtension(oid: number[], critical: boolean, value: Buffer): Buffer {
    const extParts: Buffer[] = [];
    extParts.push(this.encodeOID(oid));
    if (critical) {
      extParts.push(Buffer.from([0x01, 0x01, 0xff]));
    }
    extParts.push(this.encodeTag(0x04, value));
    return this.encodeSequence(extParts);
  }

  private buildBasicConstraints(isCA: boolean): Buffer {
    const content: Buffer[] = [];
    if (isCA) {
      content.push(Buffer.from([0x01, 0x01, 0xff]));
    }
    return this.encodeSequence(content);
  }

  private buildKeyUsage(type: CertificateType, isCA: boolean): Buffer {
    let bits = 0;
    if (isCA) {
      bits |= (1 << 7);
      bits |= (1 << 6);
      bits |= (1 << 5);
    } else {
      bits |= (1 << 0);
      bits |= (1 << 1);
      if (type === CertificateType.CODE_SIGNING) {
        bits |= (1 << 5);
      }
    }

    const byteValue = bits & 0xff;
    const unusedBits = byteValue === 0 ? 0 : (8 - Math.ceil(Math.log2(byteValue + 1)));
    return this.encodeBitString(Buffer.from([byteValue]), unusedBits);
  }

  private buildExtendedKeyUsage(type: CertificateType): Buffer | null {
    const oids: number[][] = [];

    switch (type) {
      case CertificateType.SERVER:
        oids.push([1, 3, 6, 1, 5, 5, 7, 3, 1]);
        break;
      case CertificateType.CLIENT:
        oids.push([1, 3, 6, 1, 5, 5, 7, 3, 2]);
        break;
      case CertificateType.CODE_SIGNING:
        oids.push([1, 3, 6, 1, 5, 5, 7, 3, 3]);
        break;
      default:
        return null;
    }

    const parts = oids.map(oid => this.encodeOID(oid));
    return this.encodeSequence(parts);
  }

  private buildSubjectAltName(dnsNames: string[], ipAddrs: string[]): Buffer {
    const names: Buffer[] = [];

    for (const dns of dnsNames) {
      names.push(this.encodeTag(0x82, Buffer.from(dns, 'utf8')));
    }

    for (const ip of ipAddrs) {
      const ipParts = ip.split('.').map(p => parseInt(p, 10));
      if (ipParts.length === 4 && ipParts.every(p => p >= 0 && p <= 255)) {
        names.push(this.encodeTag(0x87, Buffer.from(ipParts)));
      }
    }

    return this.encodeSequence(names);
  }

  private buildSubjectKeyIdentifier(spki: Buffer): Buffer {
    void spki;
    const ski = randomBytes(20);
    return this.encodeTag(0x04, ski);
  }

  private encodeDN(dnMap: Map<string, string>): Buffer {
    const rdns: Buffer[] = [];
    const oidMap: Record<string, number[]> = {
      CN: [2, 5, 4, 3],
      O: [2, 5, 4, 10],
      OU: [2, 5, 4, 11],
      C: [2, 5, 4, 6],
      ST: [2, 5, 4, 8],
      L: [2, 5, 4, 7],
      E: [1, 2, 840, 113549, 1, 9, 1],
    };

    for (const [key, value] of dnMap) {
      const oid = oidMap[key] || [2, 5, 4, 3];
      const atv = this.encodeSequence([
        this.encodeOID(oid),
        this.encodeTag(0x0c, Buffer.from(value, 'utf8')),
      ]);
      rdns.push(this.encodeSet([atv]));
    }

    return this.encodeSequence(rdns);
  }

  private encodeValidity(notBefore: Date, notAfter: Date): Buffer {
    const encodeUTCTime = (date: Date): Buffer => {
      const yy = date.getUTCFullYear() % 100;
      const mo = date.getUTCMonth() + 1;
      const dd = date.getUTCDate();
      const hh = date.getUTCHours();
      const mm = date.getUTCMinutes();
      const ss = date.getUTCSeconds();
      const str = `${yy.toString().padStart(2, '0')}${mo.toString().padStart(2, '0')}${dd.toString().padStart(2, '0')}${hh.toString().padStart(2, '0')}${mm.toString().padStart(2, '0')}${ss.toString().padStart(2, '0')}Z`;
      return this.encodeTag(0x17, Buffer.from(str, 'ascii'));
    };

    return this.encodeSequence([encodeUTCTime(notBefore), encodeUTCTime(notAfter)]);
  }

  private extractSPKI(publicKeyPem: string): Buffer {
    const lines = publicKeyPem.split('\n');
    const base64 = lines
      .filter(line => !line.startsWith('-----'))
      .join('');
    return Buffer.from(base64, 'base64');
  }

  private encodeLength(length: number): Buffer {
    if (length < 0x80) {
      return Buffer.from([length]);
    }
    const bytes: number[] = [];
    let value = length;
    while (value > 0) {
      bytes.unshift(value & 0xff);
      value >>= 8;
    }
    return Buffer.from([0x80 | bytes.length, ...bytes]);
  }

  private encodeTag(tag: number, content: Buffer): Buffer {
    return Buffer.concat([Buffer.from([tag]), this.encodeLength(content.length), content]);
  }

  private encodeSequence(parts: Buffer[]): Buffer {
    const content = Buffer.concat(parts);
    return this.encodeTag(0x30, content);
  }

  private encodeSet(parts: Buffer[]): Buffer {
    const content = Buffer.concat(parts);
    return this.encodeTag(0x31, content);
  }

  private encodeOID(oid: number[]): Buffer {
    const bytes: number[] = [];
    const firstByte = oid[0] * 40 + oid[1];
    bytes.push(firstByte);

    for (let i = 2; i < oid.length; i++) {
      let value = oid[i];
      if (value < 0x80) {
        bytes.push(value);
      } else {
        const temp: number[] = [];
        temp.push(value & 0x7f);
        value >>= 7;
        while (value > 0) {
          temp.unshift(0x80 | (value & 0x7f));
          value >>= 7;
        }
        bytes.push(...temp);
      }
    }

    return this.encodeTag(0x06, Buffer.from(bytes));
  }

  private encodeBitString(data: Buffer, unusedBits: number = 0): Buffer {
    const content = Buffer.concat([Buffer.from([unusedBits]), data]);
    return this.encodeTag(0x03, content);
  }
}

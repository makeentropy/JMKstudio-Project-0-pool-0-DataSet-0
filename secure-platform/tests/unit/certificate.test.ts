import * as crypto from 'crypto';

type VerifyResult = 'VALID' | 'EXPIRED' | 'REVOKED' | 'INVALID_SIGNATURE' | 'UNKNOWN_CA';

interface Certificate {
  serial: string;
  subject: { CN: string; O?: string; OU?: string };
  issuer: { CN: string };
  publicKey: string;
  privateKey?: string;
  notBefore: Date;
  notAfter: Date;
  signature: string;
  tbsData: string;
  isCA: boolean;
  pathLen?: number;
  parentSerial?: string;
}

interface CAState {
  root: Certificate | null;
  intermediate: Certificate | null;
  revokedSerials: Set<string>;
  issuedCertificates: Map<string, Certificate>;
}

const globalCA: CAState = {
  root: null,
  intermediate: null,
  revokedSerials: new Set(),
  issuedCertificates: new Map(),
};

const sha256Hex = (data: string): string =>
  crypto.createHash('sha256').update(data).digest('hex');

const genSerial = (): string => crypto.randomBytes(16).toString('hex');

const signData = (data: string, privateKeyPem: string): string =>
  crypto
    .createSign('sha256WithRSAEncryption')
    .update(data)
    .sign(privateKeyPem, 'base64');

const verifySignature = (
  data: string,
  signature: string,
  publicKeyPem: string
): boolean => {
  try {
    return crypto
      .createVerify('sha256WithRSAEncryption')
      .update(data)
      .verify(publicKeyPem, signature, 'base64');
  } catch {
    return false;
  }
};

const buildTBS = (cert: Omit<Certificate, 'signature' | 'tbsData'>): string =>
  JSON.stringify({
    serial: cert.serial,
    subject: cert.subject,
    issuer: cert.issuer,
    publicKeyFingerprint: sha256Hex(cert.publicKey),
    notBefore: cert.notBefore.toISOString(),
    notAfter: cert.notAfter.toISOString(),
    isCA: cert.isCA,
    pathLen: cert.pathLen,
    parentSerial: cert.parentSerial,
  });

const issueCertificate = (
  subject: { CN: string; O?: string; OU?: string },
  issuerCert: Certificate,
  issuerPrivateKey: string,
  options: {
    validityDays?: number;
    isCA?: boolean;
    pathLen?: number;
    keySize?: number;
  } = {}
): Certificate => {
  const validityDays = options.validityDays ?? 365;
  const keySize = options.keySize ?? 2048;

  const { publicKey, privateKey } = crypto.generateKeyPairSync('rsa', {
    modulusLength: keySize,
    publicKeyEncoding: { type: 'spki', format: 'pem' },
    privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
  });

  const now = new Date();
  const notBefore = new Date(now.getTime());
  const notAfter = new Date(now.getTime() + validityDays * 24 * 60 * 60 * 1000);

  const partial: Omit<Certificate, 'signature' | 'tbsData'> = {
    serial: genSerial(),
    subject,
    issuer: { CN: issuerCert.subject.CN },
    publicKey,
    privateKey,
    notBefore,
    notAfter,
    isCA: options.isCA ?? false,
    pathLen: options.pathLen,
    parentSerial: issuerCert.serial,
  };

  const tbsData = buildTBS(partial);
  const signature = signData(tbsData, issuerPrivateKey);

  const cert: Certificate = { ...partial, tbsData, signature };
  globalCA.issuedCertificates.set(cert.serial, cert);
  return cert;
};

const initRootCA = (): Certificate => {
  const keySize = 4096;
  const { publicKey, privateKey } = crypto.generateKeyPairSync('rsa', {
    modulusLength: keySize,
    publicKeyEncoding: { type: 'spki', format: 'pem' },
    privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
  });

  const now = new Date();
  const validityDays = 3650;

  const subject = { CN: 'SecurePlatform Root CA', O: 'SecurePlatform', OU: 'Root CA' };

  const partial: Omit<Certificate, 'signature' | 'tbsData'> = {
    serial: genSerial(),
    subject,
    issuer: { CN: subject.CN },
    publicKey,
    privateKey,
    notBefore: now,
    notAfter: new Date(now.getTime() + validityDays * 24 * 60 * 60 * 1000),
    isCA: true,
    pathLen: 2,
  };

  const tbsData = buildTBS(partial);
  const signature = signData(tbsData, privateKey);

  const cert: Certificate = { ...partial, tbsData, signature };
  globalCA.root = cert;
  globalCA.issuedCertificates.set(cert.serial, cert);
  return cert;
};

const getIssuerPublicKey = (cert: Certificate): string | null => {
  if (cert.parentSerial) {
    const parent = globalCA.issuedCertificates.get(cert.parentSerial);
    return parent?.publicKey ?? null;
  }
  if (globalCA.root && cert.issuer.CN === globalCA.root.subject.CN) {
    return globalCA.root.publicKey;
  }
  return null;
};

const verifyCertificate = (
  cert: Certificate,
  trustAnchors: Certificate[] = []
): VerifyResult => {
  const anchors = trustAnchors.length ? trustAnchors : (globalCA.root ? [globalCA.root] : []);
  if (!anchors.length) return 'UNKNOWN_CA';

  if (globalCA.revokedSerials.has(cert.serial)) return 'REVOKED';

  const now = new Date();
  if (now < cert.notBefore || now > cert.notAfter) return 'EXPIRED';

  let issuerKey: string | null = null;

  for (const anchor of anchors) {
    if (anchor.serial === cert.serial) {
      issuerKey = anchor.publicKey;
      break;
    }
    if (cert.issuer.CN === anchor.subject.CN) {
      issuerKey = anchor.publicKey;
      break;
    }
  }

  if (!issuerKey && cert.parentSerial) {
    const parent = globalCA.issuedCertificates.get(cert.parentSerial);
    if (parent) {
      const parentVerify = verifyCertificate(parent, anchors);
      if (parentVerify !== 'VALID') return parentVerify;
      issuerKey = parent.publicKey;
    }
  }

  if (!issuerKey) return 'UNKNOWN_CA';

  const sigOk = verifySignature(cert.tbsData, cert.signature, issuerKey);
  if (!sigOk) return 'INVALID_SIGNATURE';

  return 'VALID';
};

const revokeCertificate = (cert: Certificate): void => {
  globalCA.revokedSerials.add(cert.serial);
};

const resetCA = (): void => {
  globalCA.root = null;
  globalCA.intermediate = null;
  globalCA.revokedSerials.clear();
  globalCA.issuedCertificates.clear();
};

describe('Certificate Authority', () => {
  beforeEach(() => {
    resetCA();
  });

  describe('CA initialization & Root certificate', () => {
    it('should initialize CA with self-signed root certificate', () => {
      const root = initRootCA();
      expect(root).toBeTruthy();
      expect(root.isCA).toBe(true);
      expect(root.issuer.CN).toBe(root.subject.CN);
      expect(root.privateKey).toBeTruthy();
      expect(root.serial).toHaveLength(32);
      expect(root.notAfter.getTime() - root.notBefore.getTime())
        .toBeGreaterThanOrEqual(364 * 24 * 60 * 60 * 1000);
    });

    it('root certificate signature should verify against itself (self-signed)', () => {
      const root = initRootCA();
      const result = verifySignature(root.tbsData, root.signature, root.publicKey);
      expect(result).toBe(true);
    });

    it('verify should return VALID for trusted root', () => {
      const root = initRootCA();
      const result = verifyCertificate(root);
      expect(result).toBe('VALID');
    });

    it('tampered root should return INVALID_SIGNATURE', () => {
      const root = initRootCA();
      const tampered: Certificate = {
        ...root,
        subject: { ...root.subject, CN: 'Fake Root CA' },
      };
      tampered.tbsData = buildTBS({
        serial: tampered.serial,
        subject: tampered.subject,
        issuer: tampered.issuer,
        publicKey: tampered.publicKey,
        notBefore: tampered.notBefore,
        notAfter: tampered.notAfter,
        isCA: tampered.isCA,
        pathLen: tampered.pathLen,
        parentSerial: tampered.parentSerial,
      });
      const result = verifyCertificate(tampered);
      expect(result).toBe('INVALID_SIGNATURE');
    });
  });

  describe('Server certificate issuing & verification', () => {
    it('should issue server certificate signed by root CA', () => {
      const root = initRootCA();
      const serverCert = issueCertificate(
        { CN: 'localhost', O: 'SecurePlatform', OU: 'Server' },
        root,
        root.privateKey!,
        { validityDays: 825, isCA: false }
      );
      expect(serverCert).toBeTruthy();
      expect(serverCert.isCA).toBe(false);
      expect(serverCert.issuer.CN).toBe(root.subject.CN);
      expect(serverCert.subject.CN).toBe('localhost');
      expect(serverCert.serial).not.toBe(root.serial);
    });

    it('verify should return VALID for properly signed server cert', () => {
      const root = initRootCA();
      const serverCert = issueCertificate(
        { CN: 'localhost' },
        root,
        root.privateKey!
      );
      const result = verifyCertificate(serverCert);
      expect(result).toBe('VALID');
    });

    it('server cert signed by unknown key should fail signature check', () => {
      const root = initRootCA();
      const { privateKey: fakeKey } = crypto.generateKeyPairSync('rsa', {
        modulusLength: 2048,
        publicKeyEncoding: { type: 'spki', format: 'pem' },
        privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
      });
      const serverCert = issueCertificate(
        { CN: 'localhost' },
        root,
        fakeKey
      );
      const result = verifyCertificate(serverCert);
      expect(result).toBe('INVALID_SIGNATURE');
    });
  });

  describe('Expired client certificate', () => {
    it('issue client cert with negative validity -> verify returns EXPIRED', () => {
      const root = initRootCA();
      const expiredCert = issueCertificate(
        { CN: 'test-client', OU: 'Client' },
        root,
        root.privateKey!,
        { validityDays: -1 }
      );
      expect(expiredCert.notAfter.getTime()).toBeLessThan(Date.now());
      const result = verifyCertificate(expiredCert);
      expect(result).toBe('EXPIRED');
    });

    it('valid client cert (positive validity) should pass', () => {
      const root = initRootCA();
      const validCert = issueCertificate(
        { CN: 'test-client' },
        root,
        root.privateKey!,
        { validityDays: 30 }
      );
      const result = verifyCertificate(validCert);
      expect(result).toBe('VALID');
    });
  });

  describe('Certificate revocation', () => {
    it('revoked cert -> verify returns REVOKED', () => {
      const root = initRootCA();
      const serverCert = issueCertificate(
        { CN: 'compromised-server' },
        root,
        root.privateKey!
      );
      expect(verifyCertificate(serverCert)).toBe('VALID');
      revokeCertificate(serverCert);
      const result = verifyCertificate(serverCert);
      expect(result).toBe('REVOKED');
    });

    it('unrelated cert should remain VALID after another is revoked', () => {
      const root = initRootCA();
      const certA = issueCertificate({ CN: 'a' }, root, root.privateKey!);
      const certB = issueCertificate({ CN: 'b' }, root, root.privateKey!);
      revokeCertificate(certA);
      expect(verifyCertificate(certA)).toBe('REVOKED');
      expect(verifyCertificate(certB)).toBe('VALID');
    });
  });

  describe('Intermediate CA chain (2-level)', () => {
    it('should build 2-level CA chain: Root → Intermediate → Leaf', () => {
      const root = initRootCA();
      expect(root.pathLen).toBeGreaterThanOrEqual(1);

      const intermediate = issueCertificate(
        { CN: 'SecurePlatform Intermediate CA', OU: 'Intermediate CA' },
        root,
        root.privateKey!,
        { validityDays: 1825, isCA: true, pathLen: 0 }
      );
      globalCA.intermediate = intermediate;
      expect(intermediate.isCA).toBe(true);
      expect(verifyCertificate(intermediate)).toBe('VALID');

      const leaf = issueCertificate(
        { CN: 'leaf.example.local' },
        intermediate,
        intermediate.privateKey!,
        { validityDays: 365, isCA: false }
      );
      expect(leaf.issuer.CN).toBe(intermediate.subject.CN);
      expect(leaf.parentSerial).toBe(intermediate.serial);

      const result = verifyCertificate(leaf);
      expect(result).toBe('VALID');
    });

    it('chain should break when intermediate is revoked', () => {
      const root = initRootCA();
      const intermediate = issueCertificate(
        { CN: 'Int CA' },
        root,
        root.privateKey!,
        { isCA: true, pathLen: 0 }
      );
      const leaf = issueCertificate(
        { CN: 'leaf' },
        intermediate,
        intermediate.privateKey!
      );
      expect(verifyCertificate(leaf)).toBe('VALID');

      revokeCertificate(intermediate);
      const result = verifyCertificate(leaf);
      expect(result).toBe('REVOKED');
    });

    it('chain should break when intermediate is expired', () => {
      const root = initRootCA();
      const badIntermediate = issueCertificate(
        { CN: 'Expired Int CA' },
        root,
        root.privateKey!,
        { validityDays: -2, isCA: true, pathLen: 0 }
      );
      const leaf = issueCertificate(
        { CN: 'leaf' },
        badIntermediate,
        badIntermediate.privateKey!,
        { validityDays: 365 }
      );
      const result = verifyCertificate(leaf);
      expect(result).toBe('EXPIRED');
    });

    it('leaf signed directly by root should be independent of intermediate', () => {
      const root = initRootCA();
      const intermediate = issueCertificate(
        { CN: 'Int CA' },
        root,
        root.privateKey!,
        { isCA: true, pathLen: 0 }
      );
      revokeCertificate(intermediate);

      const directLeaf = issueCertificate(
        { CN: 'direct.leaf' },
        root,
        root.privateKey!
      );
      expect(verifyCertificate(directLeaf)).toBe('VALID');
    });
  });

  describe('Multiple scenarios matrix', () => {
    it('covers 10 verify combinations correctly', () => {
      const root = initRootCA();
      const inter = issueCertificate(
        { CN: 'Int' }, root, root.privateKey!, { isCA: true, pathLen: 0 }
      );
      const goodServer = issueCertificate({ CN: 'srv' }, root, root.privateKey!);
      const goodClient = issueCertificate({ CN: 'cli' }, root, root.privateKey!);
      const expired = issueCertificate({ CN: 'exp' }, root, root.privateKey!, { validityDays: -1 });
      const future = issueCertificate({ CN: 'fut' }, root, root.privateKey!, { validityDays: 10 });
      future.notBefore = new Date(Date.now() + 10 * 24 * 60 * 60 * 1000);
      future.tbsData = buildTBS({ serial: future.serial, subject: future.subject, issuer: future.issuer, publicKey: future.publicKey, notBefore: future.notBefore, notAfter: future.notAfter, isCA: future.isCA, pathLen: future.pathLen, parentSerial: future.parentSerial });
      future.signature = signData(future.tbsData, root.privateKey!);
      const revoked = issueCertificate({ CN: 'rev' }, root, root.privateKey!);
      revokeCertificate(revoked);
      const chainLeaf = issueCertificate({ CN: 'leaf' }, inter, inter.privateKey!);
      const wrongKey = crypto.generateKeyPairSync('rsa', {
        modulusLength: 2048,
        publicKeyEncoding: { type: 'spki', format: 'pem' },
        privateKeyEncoding: { type: 'pkcs8', format: 'pem' },
      });
      const badSig: Certificate = { ...goodServer, signature: signData(goodServer.tbsData, wrongKey.privateKey) };
      const orphan: Certificate = {
        ...goodServer,
        serial: '00'.repeat(16),
        issuer: { CN: 'NoSuchCA' },
        parentSerial: undefined,
      };
      orphan.tbsData = buildTBS({ serial: orphan.serial, subject: orphan.subject, issuer: orphan.issuer, publicKey: orphan.publicKey, notBefore: orphan.notBefore, notAfter: orphan.notAfter, isCA: orphan.isCA });
      orphan.signature = signData(orphan.tbsData, root.privateKey!);

      const cases: Array<[string, Certificate, VerifyResult]> = [
        ['valid server', goodServer, 'VALID'],
        ['valid client', goodClient, 'VALID'],
        ['expired cert', expired, 'EXPIRED'],
        ['not yet valid (future)', future, 'EXPIRED'],
        ['revoked cert', revoked, 'REVOKED'],
        ['valid chain leaf', chainLeaf, 'VALID'],
        ['invalid signature', badSig, 'INVALID_SIGNATURE'],
        ['unknown issuer', orphan, 'UNKNOWN_CA'],
        ['self (root)', root, 'VALID'],
        ['valid intermediate CA', inter, 'VALID'],
      ];

      for (const [name, cert, expected] of cases) {
        expect(verifyCertificate(cert)).toBe(expected);
      }
    });
  });
});

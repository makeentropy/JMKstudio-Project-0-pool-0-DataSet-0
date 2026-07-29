export * from './types';
export { CertificateAuthority } from './ca';
export { CertificateStore } from './store';
export { CertificateVerifier } from './verifier';

import { CertificateAuthority } from './ca';

export const createDefaultCA = (): CertificateAuthority => {
  const ca = new CertificateAuthority();
  ca.initialize('SecurePlatform Root CA', 4096, 3650);
  return ca;
};

export const defaultCertificateStoreConfig = {
  encryption: {
    algorithm: 'aes-256-gcm',
    keyDerivation: 'scrypt',
    saltBytes: 16,
    ivBytes: 16,
  },
} as const;

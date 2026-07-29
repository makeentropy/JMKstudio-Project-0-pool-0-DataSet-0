export enum CertificateStatus {
  VALID = 'VALID',
  EXPIRED = 'EXPIRED',
  REVOKED = 'REVOKED',
  UNKNOWN = 'UNKNOWN',
}

export enum CertificateType {
  ROOT_CA = 'ROOT_CA',
  INTERMEDIATE_CA = 'INTERMEDIATE_CA',
  END_ENTITY = 'END_ENTITY',
  SERVER = 'SERVER',
  CLIENT = 'CLIENT',
  CODE_SIGNING = 'CODE_SIGNING',
}

export enum RevocationReason {
  UNSPECIFIED = 0,
  KEY_COMPROMISE = 1,
  CA_COMPROMISE = 2,
  AFFILIATION_CHANGED = 3,
  SUPERSEDED = 4,
  CESSATION_OF_OPERATION = 5,
  CERTIFICATE_HOLD = 6,
  REMOVE_FROM_CRL = 8,
  PRIVILEGE_WITHDRAWN = 9,
  AA_COMPROMISE = 10,
}

export interface CertificateInfo {
  serialNumber: string;
  subject: string;
  issuer: string;
  notBefore: Date;
  notAfter: Date;
  certificateType: CertificateType;
  publicKeyFingerprint: string;
  status: CertificateStatus;
  revocationReason?: RevocationReason;
  revocationDate?: Date;
  pemData?: string;
}

export class CertificateError extends Error {
  public readonly code: string;
  public readonly cause?: unknown;

  constructor(message: string, code: string = 'CERTIFICATE_ERROR', cause?: unknown) {
    super(message);
    this.name = 'CertificateError';
    this.code = code;
    this.cause = cause;
    Object.setPrototypeOf(this, CertificateError.prototype);
  }
}

export class CertificateValidationError extends CertificateError {
  constructor(message: string, cause?: unknown) {
    super(message, 'CERTIFICATE_VALIDATION_ERROR', cause);
    this.name = 'CertificateValidationError';
    Object.setPrototypeOf(this, CertificateValidationError.prototype);
  }
}

export class CertificateSigningError extends CertificateError {
  constructor(message: string, cause?: unknown) {
    super(message, 'CERTIFICATE_SIGNING_ERROR', cause);
    this.name = 'CertificateSigningError';
    Object.setPrototypeOf(this, CertificateSigningError.prototype);
  }
}

export class CertificateRevocationError extends CertificateError {
  constructor(message: string, cause?: unknown) {
    super(message, 'CERTIFICATE_REVOCATION_ERROR', cause);
    this.name = 'CertificateRevocationError';
    Object.setPrototypeOf(this, CertificateRevocationError.prototype);
  }
}

export class CertificateStoreError extends CertificateError {
  constructor(message: string, code: string = 'CERTIFICATE_STORE_ERROR', cause?: unknown) {
    super(message, code, cause);
    this.name = 'CertificateStoreError';
    Object.setPrototypeOf(this, CertificateStoreError.prototype);
  }
}

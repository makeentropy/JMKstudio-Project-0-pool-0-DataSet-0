export class CryptoError extends Error {
  public readonly code: string;
  public readonly cause?: unknown;

  constructor(message: string, code: string = 'CRYPTO_ERROR', cause?: unknown) {
    super(message);
    this.name = 'CryptoError';
    this.code = code;
    this.cause = cause;
    Object.setPrototypeOf(this, CryptoError.prototype);
  }
}

export class ValidationError extends CryptoError {
  constructor(message: string, cause?: unknown) {
    super(message, 'VALIDATION_ERROR', cause);
    this.name = 'ValidationError';
    Object.setPrototypeOf(this, ValidationError.prototype);
  }
}

export class EncryptionError extends CryptoError {
  constructor(message: string, cause?: unknown) {
    super(message, 'ENCRYPTION_ERROR', cause);
    this.name = 'EncryptionError';
    Object.setPrototypeOf(this, EncryptionError.prototype);
  }
}

export class DecryptionError extends CryptoError {
  constructor(message: string, cause?: unknown) {
    super(message, 'DECRYPTION_ERROR', cause);
    this.name = 'DecryptionError';
    Object.setPrototypeOf(this, DecryptionError.prototype);
  }
}

export class EncodingError extends CryptoError {
  constructor(message: string, cause?: unknown) {
    super(message, 'ENCODING_ERROR', cause);
    this.name = 'EncodingError';
    Object.setPrototypeOf(this, EncodingError.prototype);
  }
}

export class DecodingError extends CryptoError {
  constructor(message: string, cause?: unknown) {
    super(message, 'DECODING_ERROR', cause);
    this.name = 'DecodingError';
    Object.setPrototypeOf(this, DecodingError.prototype);
  }
}

export class SteganographyError extends CryptoError {
  constructor(message: string, cause?: unknown) {
    super(message, 'STEGANOGRAPHY_ERROR', cause);
    this.name = 'SteganographyError';
    Object.setPrototypeOf(this, SteganographyError.prototype);
  }
}

export class SignatureError extends CryptoError {
  constructor(message: string, cause?: unknown) {
    super(message, 'SIGNATURE_ERROR', cause);
    this.name = 'SignatureError';
    Object.setPrototypeOf(this, SignatureError.prototype);
  }
}

export function validateString(value: unknown, paramName: string): asserts value is string {
  if (typeof value !== 'string') {
    throw new ValidationError(`参数 "${paramName}" 必须是字符串类型，实际类型: ${typeof value}`);
  }
  if (value.length === 0) {
    throw new ValidationError(`参数 "${paramName}" 不能为空字符串`);
  }
}

export function validateBuffer(value: unknown, paramName: string): asserts value is Buffer {
  if (!Buffer.isBuffer(value)) {
    throw new ValidationError(`参数 "${paramName}" 必须是 Buffer 类型`);
  }
}

export function validateArray<T>(value: unknown, paramName: string): asserts value is T[] {
  if (!Array.isArray(value)) {
    throw new ValidationError(`参数 "${paramName}" 必须是数组类型`);
  }
  if (value.length === 0) {
    throw new ValidationError(`参数 "${paramName}" 不能为空数组`);
  }
}

export function validateNonEmptyString(value: unknown, paramName: string): asserts value is string {
  validateString(value, paramName);
}

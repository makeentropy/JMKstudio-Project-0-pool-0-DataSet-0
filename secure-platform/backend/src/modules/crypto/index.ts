import {
  xorEncrypt,
  xorDecrypt,
  multiLayerXor,
  multiLayerXorDecrypt,
} from './xor';
import {
  base64Encode,
  base64Decode,
  base64EncodeBuffer,
  urlSafeBase64Encode,
  urlSafeBase64Decode,
  urlSafeBase64EncodeBuffer,
} from './base64';
import { urlEncode, urlDecode } from './url-encode';
import type { AESEncryptOptions, AESDecryptOptions } from './aes-256-gcm';
import {
  encrypt as aesEncrypt,
  decrypt as aesDecrypt,
  encryptBuffer as aesEncryptBuffer,
  decryptBuffer as aesDecryptBuffer,
  hashPassword,
  sha256,
  sha512,
} from './aes-256-gcm';
import {
  encrypt as hybridEncrypt,
  decrypt as hybridDecrypt,
  sign,
  verify,
} from './gpg-hybrid';
import { encodeMessageIntoImage } from './steganography';
import { ValidationError } from './errors';

export * as errors from './errors';
export {
  CryptoError,
  ValidationError,
  EncryptionError,
  DecryptionError,
  EncodingError,
  DecodingError,
  SteganographyError,
  SignatureError,
  validateString,
  validateBuffer,
  validateArray,
  validateNonEmptyString,
} from './errors';

export * as xor from './xor';
export { xorEncrypt, xorDecrypt, multiLayerXor, multiLayerXorDecrypt } from './xor';

export * as base64 from './base64';
export {
  base64Encode,
  base64Decode,
  base64EncodeBuffer,
  base64DecodeBuffer,
  urlSafeBase64Encode,
  urlSafeBase64Decode,
  urlSafeBase64EncodeBuffer,
  urlSafeBase64DecodeBuffer,
} from './base64';

export * as urlUtils from './url-encode';
export {
  urlEncode,
  urlDecode,
  queryStringEncode,
  queryStringDecode,
  buildUrl,
  parseUrl,
} from './url-encode';

export * as aes256gcm from './aes-256-gcm';
export type { AESEncryptOptions, AESDecryptOptions } from './aes-256-gcm';
export {
  encrypt as aesEncrypt,
  decrypt as aesDecrypt,
  encryptBuffer as aesEncryptBuffer,
  decryptBuffer as aesDecryptBuffer,
  encryptFile as aesEncryptFile,
  decryptFile as aesDecryptFile,
  hashPassword,
  verifyPassword,
  sha256,
  sha512,
} from './aes-256-gcm';

export * as gpgHybrid from './gpg-hybrid';
export type { KeyPair, HybridEncryptedData } from './gpg-hybrid';
export {
  generateKeyPair,
  encrypt as hybridEncrypt,
  decrypt as hybridDecrypt,
  encryptBuffer as hybridEncryptBuffer,
  decryptBuffer as hybridDecryptBuffer,
  sign,
  signBuffer,
  verify,
  verifyBuffer,
} from './gpg-hybrid';

export * as steganography from './steganography';
export {
  encodeMessageIntoImage,
  decodeMessageFromImage,
  getImageCapacity,
  hasHiddenMessage,
} from './steganography';

interface ChainResult {
  value: string | Buffer;
  isBuffer: boolean;
}

export class CryptoTools {
  private result: ChainResult;

  private constructor(initialValue: string | Buffer) {
    this.result = {
      value: initialValue,
      isBuffer: Buffer.isBuffer(initialValue),
    };
  }

  static from(value: string | Buffer): CryptoTools {
    if (typeof value !== 'string' && !Buffer.isBuffer(value)) {
      throw new ValidationError('初始值必须是字符串或 Buffer 类型');
    }
    return new CryptoTools(value);
  }

  static of(value: string | Buffer): CryptoTools {
    return CryptoTools.from(value);
  }

  private getStringValue(): string {
    if (this.result.isBuffer) {
      return (this.result.value as Buffer).toString('utf-8');
    }
    return this.result.value as string;
  }

  private getBufferValue(): Buffer {
    if (this.result.isBuffer) {
      return this.result.value as Buffer;
    }
    return Buffer.from(this.result.value as string, 'utf-8');
  }

  xorEncrypt(key: string): CryptoTools {
    const result = xorEncrypt(this.getStringValue(), key);
    this.result = { value: result, isBuffer: false };
    return this;
  }

  xorDecrypt(key: string): CryptoTools {
    const result = xorDecrypt(this.getStringValue(), key);
    this.result = { value: result, isBuffer: false };
    return this;
  }

  multiLayerXor(keys: string[]): CryptoTools {
    const result = multiLayerXor(this.getStringValue(), keys);
    this.result = { value: result, isBuffer: false };
    return this;
  }

  multiLayerXorDecrypt(keys: string[]): CryptoTools {
    const result = multiLayerXorDecrypt(this.getStringValue(), keys);
    this.result = { value: result, isBuffer: false };
    return this;
  }

  base64Encode(): CryptoTools {
    if (this.result.isBuffer) {
      const result = base64EncodeBuffer(this.result.value as Buffer);
      this.result = { value: result, isBuffer: false };
    } else {
      const result = base64Encode(this.result.value as string);
      this.result = { value: result, isBuffer: false };
    }
    return this;
  }

  base64Decode(): CryptoTools {
    const result = base64Decode(this.getStringValue());
    this.result = { value: result, isBuffer: false };
    return this;
  }

  urlSafeBase64Encode(): CryptoTools {
    if (this.result.isBuffer) {
      const result = urlSafeBase64EncodeBuffer(this.result.value as Buffer);
      this.result = { value: result, isBuffer: false };
    } else {
      const result = urlSafeBase64Encode(this.result.value as string);
      this.result = { value: result, isBuffer: false };
    }
    return this;
  }

  urlSafeBase64Decode(): CryptoTools {
    const result = urlSafeBase64Decode(this.getStringValue());
    this.result = { value: result, isBuffer: false };
    return this;
  }

  urlEncode(): CryptoTools {
    const result = urlEncode(this.getStringValue());
    this.result = { value: result, isBuffer: false };
    return this;
  }

  urlDecode(): CryptoTools {
    const result = urlDecode(this.getStringValue());
    this.result = { value: result, isBuffer: false };
    return this;
  }

  aesEncrypt(password: string, options?: AESEncryptOptions): CryptoTools {
    const result = aesEncrypt(this.getStringValue(), password, options);
    this.result = { value: result, isBuffer: false };
    return this;
  }

  aesDecrypt(password: string, options?: AESDecryptOptions): CryptoTools {
    const result = aesDecrypt(this.getStringValue(), password, options);
    this.result = { value: result, isBuffer: false };
    return this;
  }

  aesEncryptBuffer(password: string, options?: AESEncryptOptions): CryptoTools {
    const result = aesEncryptBuffer(this.getBufferValue(), password, options);
    this.result = { value: result, isBuffer: true };
    return this;
  }

  aesDecryptBuffer(password: string, options?: AESDecryptOptions): CryptoTools {
    const result = aesDecryptBuffer(this.getBufferValue(), password, options);
    this.result = { value: result, isBuffer: true };
    return this;
  }

  sha256(): CryptoTools {
    const result = sha256(this.getStringValue());
    this.result = { value: result, isBuffer: false };
    return this;
  }

  sha512(): CryptoTools {
    const result = sha512(this.getStringValue());
    this.result = { value: result, isBuffer: false };
    return this;
  }

  hashPassword(salt?: string): CryptoTools {
    const result = hashPassword(this.getStringValue(), salt);
    this.result = { value: JSON.stringify(result), isBuffer: false };
    return this;
  }

  hybridEncrypt(publicKey: string): CryptoTools {
    return this;
  }

  hybridDecrypt(privateKey: string): CryptoTools {
    return this;
  }

  encodeMessageIntoImage(password?: string): CryptoTools {
    const imageBuffer = this.getBufferValue();
    throw new ValidationError('链式调用 encodeMessageIntoImage 需要先使用 withMessage 设置消息');
  }

  withMessage(message: string): CryptoToolsWithMessage {
    return new CryptoToolsWithMessage(this.getBufferValue(), message);
  }

  withPublicKey(publicKey: string): CryptoToolsWithPublicKey {
    return new CryptoToolsWithPublicKey(this.getStringValue(), publicKey);
  }

  withPrivateKey(privateKey: string): CryptoToolsWithPrivateKey {
    return new CryptoToolsWithPrivateKey(this.getStringValue(), privateKey);
  }

  toString(): string {
    if (this.result.isBuffer) {
      return (this.result.value as Buffer).toString('utf-8');
    }
    return this.result.value as string;
  }

  toBuffer(): Buffer {
    if (this.result.isBuffer) {
      return this.result.value as Buffer;
    }
    return Buffer.from(this.result.value as string, 'utf-8');
  }

  toHex(): string {
    return this.toBuffer().toString('hex');
  }

  toBase64(): string {
    return this.toBuffer().toString('base64');
  }

  valueOf(): string | Buffer {
    return this.result.value;
  }

  get [Symbol.toStringTag](): string {
    return 'CryptoTools';
  }
}

export class CryptoToolsWithMessage {
  private imageBuffer: Buffer;
  private message: string;

  constructor(imageBuffer: Buffer, message: string) {
    this.imageBuffer = imageBuffer;
    this.message = message;
  }

  encode(password?: string): Buffer {
    return encodeMessageIntoImage(this.imageBuffer, this.message, password);
  }
}

export class CryptoToolsWithPublicKey {
  private data: string;
  private publicKey: string;

  constructor(data: string, publicKey: string) {
    this.data = data;
    this.publicKey = publicKey;
  }

  async hybridEncrypt(): Promise<string> {
    return await hybridEncrypt(this.data, this.publicKey);
  }

  async verify(signature: string): Promise<boolean> {
    return await verify(this.data, signature, this.publicKey);
  }
}

export class CryptoToolsWithPrivateKey {
  private data: string;
  private privateKey: string;

  constructor(data: string, privateKey: string) {
    this.data = data;
    this.privateKey = privateKey;
  }

  async hybridDecrypt(): Promise<string> {
    return await hybridDecrypt(this.data, this.privateKey);
  }

  async sign(): Promise<string> {
    return await sign(this.data, this.privateKey);
  }
}

export default CryptoTools;

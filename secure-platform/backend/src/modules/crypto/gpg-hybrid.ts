import * as crypto from 'node:crypto';
import { validateString, validateBuffer, EncryptionError, DecryptionError, SignatureError, CryptoError } from './errors';

const RSA_MODULUS_LENGTH = 4096;
const AES_KEY_LENGTH = 32;
const AES_IV_LENGTH = 12;
const AES_TAG_LENGTH = 16;

export interface KeyPair {
  publicKey: string;
  privateKey: string;
}

export interface HybridEncryptedData {
  encryptedKey: string;
  iv: string;
  tag: string;
  encryptedData: string;
}

export function generateKeyPair(): KeyPair {
  try {
    const { publicKey, privateKey } = crypto.generateKeyPairSync('rsa', {
      modulusLength: RSA_MODULUS_LENGTH,
      publicExponent: 0x10001,
      publicKeyEncoding: {
        type: 'spki',
        format: 'pem',
      },
      privateKeyEncoding: {
        type: 'pkcs8',
        format: 'pem',
      },
    });

    return { publicKey, privateKey };
  } catch (error) {
    throw new EncryptionError('RSA-4096 密钥对生成失败', error);
  }
}

function rsaEncryptAesKey(aesKey: Buffer, publicKeyPem: string): Buffer {
  try {
    return crypto.publicEncrypt(
      {
        key: publicKeyPem,
        padding: crypto.constants.RSA_PKCS1_OAEP_PADDING,
        oaepHash: 'sha256',
      },
      aesKey,
    );
  } catch (error) {
    throw new EncryptionError('RSA 公钥加密 AES 密钥失败', error);
  }
}

function rsaDecryptAesKey(encAesKey: Buffer, privateKeyPem: string): Buffer {
  try {
    return crypto.privateDecrypt(
      {
        key: privateKeyPem,
        padding: crypto.constants.RSA_PKCS1_OAEP_PADDING,
        oaepHash: 'sha256',
      },
      encAesKey,
    );
  } catch (error) {
    throw new DecryptionError('RSA 私钥解密 AES 密钥失败', error);
  }
}

function aesGcmEncrypt(plaintext: Buffer, aesKey: Buffer): { ciphertext: Buffer; iv: Buffer; tag: Buffer } {
  const iv = crypto.randomBytes(AES_IV_LENGTH);
  const cipher = crypto.createCipheriv('aes-256-gcm', aesKey, iv);
  const ciphertext = Buffer.concat([cipher.update(plaintext), cipher.final()]);
  const tag = cipher.getAuthTag();
  return { ciphertext, iv, tag };
}

function aesGcmDecrypt(ciphertext: Buffer, aesKey: Buffer, iv: Buffer, tag: Buffer): Buffer {
  try {
    const decipher = crypto.createDecipheriv('aes-256-gcm', aesKey, iv);
    decipher.setAuthTag(tag);
    return Buffer.concat([decipher.update(ciphertext), decipher.final()]);
  } catch (error) {
    throw new DecryptionError('AES-256-GCM 解密失败，请检查私钥或加密数据是否正确', error);
  }
}

export async function encrypt(data: string, publicKey: string): Promise<string> {
  validateString(data, 'data');
  validateString(publicKey, 'publicKey');

  try {
    const aesKey = crypto.randomBytes(AES_KEY_LENGTH);
    const encAesKey = rsaEncryptAesKey(aesKey, publicKey);
    const { ciphertext, iv, tag } = aesGcmEncrypt(Buffer.from(data, 'utf-8'), aesKey);

    const keyLengthBuffer = Buffer.alloc(4);
    keyLengthBuffer.writeUInt32BE(encAesKey.length, 0);

    const combined = Buffer.concat([keyLengthBuffer, encAesKey, iv, tag, ciphertext]);
    return combined.toString('base64');
  } catch (error) {
    if (error instanceof CryptoError) {
      throw error;
    }
    throw new EncryptionError('混合加密失败（RSA-4096 + AES-256-GCM）', error);
  }
}

export async function decrypt(encryptedData: string, privateKey: string): Promise<string> {
  validateString(encryptedData, 'encryptedData');
  validateString(privateKey, 'privateKey');

  try {
    const combined = Buffer.from(encryptedData, 'base64');

    if (combined.length < 4 + 1 + AES_IV_LENGTH + AES_TAG_LENGTH) {
      throw new DecryptionError('加密数据格式无效，数据长度不足');
    }

    let offset = 0;
    const keyLength = combined.readUInt32BE(offset);
    offset += 4;

    if (combined.length < offset + keyLength + AES_IV_LENGTH + AES_TAG_LENGTH) {
      throw new DecryptionError('加密数据格式无效，数据长度不足');
    }

    const encAesKey = combined.subarray(offset, offset + keyLength);
    offset += keyLength;

    const iv = combined.subarray(offset, offset + AES_IV_LENGTH);
    offset += AES_IV_LENGTH;

    const tag = combined.subarray(offset, offset + AES_TAG_LENGTH);
    offset += AES_TAG_LENGTH;

    const ciphertext = combined.subarray(offset);

    const aesKey = rsaDecryptAesKey(encAesKey, privateKey);
    const plaintext = aesGcmDecrypt(ciphertext, aesKey, iv, tag);

    return plaintext.toString('utf-8');
  } catch (error) {
    if (error instanceof CryptoError) {
      throw error;
    }
    throw new DecryptionError('混合解密失败，请检查私钥或加密数据是否正确', error);
  }
}

export async function encryptBuffer(data: Buffer, publicKey: string): Promise<Buffer> {
  validateBuffer(data, 'data');
  validateString(publicKey, 'publicKey');

  try {
    const aesKey = crypto.randomBytes(AES_KEY_LENGTH);
    const encAesKey = rsaEncryptAesKey(aesKey, publicKey);
    const { ciphertext, iv, tag } = aesGcmEncrypt(data, aesKey);

    const keyLengthBuffer = Buffer.alloc(4);
    keyLengthBuffer.writeUInt32BE(encAesKey.length, 0);

    return Buffer.concat([keyLengthBuffer, encAesKey, iv, tag, ciphertext]);
  } catch (error) {
    if (error instanceof CryptoError) {
      throw error;
    }
    throw new EncryptionError('Buffer 混合加密失败（RSA-4096 + AES-256-GCM）', error);
  }
}

export async function decryptBuffer(encrypted: Buffer, privateKey: string): Promise<Buffer> {
  validateBuffer(encrypted, 'encrypted');
  validateString(privateKey, 'privateKey');

  try {
    if (encrypted.length < 4 + 1 + AES_IV_LENGTH + AES_TAG_LENGTH) {
      throw new DecryptionError('加密数据格式无效，数据长度不足');
    }

    let offset = 0;
    const keyLength = encrypted.readUInt32BE(offset);
    offset += 4;

    if (encrypted.length < offset + keyLength + AES_IV_LENGTH + AES_TAG_LENGTH) {
      throw new DecryptionError('加密数据格式无效，数据长度不足');
    }

    const encAesKey = encrypted.subarray(offset, offset + keyLength);
    offset += keyLength;

    const iv = encrypted.subarray(offset, offset + AES_IV_LENGTH);
    offset += AES_IV_LENGTH;

    const tag = encrypted.subarray(offset, offset + AES_TAG_LENGTH);
    offset += AES_TAG_LENGTH;

    const ciphertext = encrypted.subarray(offset);

    const aesKey = rsaDecryptAesKey(encAesKey, privateKey);
    return aesGcmDecrypt(ciphertext, aesKey, iv, tag);
  } catch (error) {
    if (error instanceof CryptoError) {
      throw error;
    }
    throw new DecryptionError('Buffer 混合解密失败，请检查私钥或加密数据是否正确', error);
  }
}

export async function sign(data: string, privateKey: string): Promise<string> {
  validateString(data, 'data');
  validateString(privateKey, 'privateKey');

  try {
    const signature = crypto.sign('RSA-SHA256', Buffer.from(data, 'utf-8'), privateKey);
    return signature.toString('base64');
  } catch (error) {
    if (error instanceof CryptoError) {
      throw error;
    }
    throw new SignatureError('数据签名失败', error);
  }
}

export async function signBuffer(data: Buffer, privateKey: string): Promise<Buffer> {
  validateBuffer(data, 'data');
  validateString(privateKey, 'privateKey');

  try {
    return crypto.sign('RSA-SHA256', data, privateKey);
  } catch (error) {
    if (error instanceof CryptoError) {
      throw error;
    }
    throw new SignatureError('Buffer 数据签名失败', error);
  }
}

export async function verify(data: string, signature: string, publicKey: string): Promise<boolean> {
  validateString(data, 'data');
  validateString(signature, 'signature');
  validateString(publicKey, 'publicKey');

  try {
    const dataBuffer = Buffer.from(data, 'utf-8');
    const signatureBuffer = Buffer.from(signature, 'base64');
    return crypto.verify('RSA-SHA256', dataBuffer, publicKey, signatureBuffer);
  } catch {
    return false;
  }
}

export async function verifyBuffer(data: Buffer, signature: Buffer, publicKey: string): Promise<boolean> {
  validateBuffer(data, 'data');
  validateBuffer(signature, 'signature');
  validateString(publicKey, 'publicKey');

  try {
    return crypto.verify('RSA-SHA256', data, publicKey, signature);
  } catch {
    return false;
  }
}

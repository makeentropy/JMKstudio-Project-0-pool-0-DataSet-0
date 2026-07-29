import { pbkdf2Sync, createCipheriv, createDecipheriv, randomBytes, createHash } from 'node:crypto';
import { validateString, validateBuffer, EncryptionError, DecryptionError } from './errors';

const PBKDF2_ITERATIONS = 100000;
const KEY_LENGTH = 32;
const IV_LENGTH = 12;
const SALT_LENGTH = 16;
const AUTH_TAG_LENGTH = 16;

export interface AESEncryptOptions {
  iterations?: number;
}

export interface AESDecryptOptions {
  iterations?: number;
}

function deriveKey(password: string, salt: Buffer, iterations: number): Buffer {
  try {
    return pbkdf2Sync(password, salt, iterations, KEY_LENGTH, 'sha256');
  } catch (error) {
    throw new EncryptionError('密钥派生失败', error);
  }
}

export function encrypt(data: string, password: string, options: AESEncryptOptions = {}): string {
  validateString(data, 'data');
  validateString(password, 'password');

  const iterations = options.iterations ?? PBKDF2_ITERATIONS;

  if (iterations < 1000) {
    throw new EncryptionError('迭代次数不能少于 1000，以确保安全性');
  }

  try {
    const salt = randomBytes(SALT_LENGTH);
    const iv = randomBytes(IV_LENGTH);
    const key = deriveKey(password, salt, iterations);

    const cipher = createCipheriv('aes-256-gcm', key, iv);

    const encryptedBuffer = Buffer.concat([
      cipher.update(Buffer.from(data, 'utf-8')),
      cipher.final(),
    ]);

    const authTag = cipher.getAuthTag();

    const iterationsBuffer = Buffer.alloc(4);
    iterationsBuffer.writeUInt32BE(iterations, 0);

    const result = Buffer.concat([
      salt,
      iv,
      authTag,
      iterationsBuffer,
      encryptedBuffer,
    ]);

    return result.toString('base64');
  } catch (error) {
    if (error instanceof EncryptionError) {
      throw error;
    }
    throw new EncryptionError('AES-256-GCM 加密失败', error);
  }
}

export function decrypt(encrypted: string, password: string, options: AESDecryptOptions = {}): string {
  validateString(encrypted, 'encrypted');
  validateString(password, 'password');

  try {
    const encryptedBuffer = Buffer.from(encrypted, 'base64');

    const minLength = SALT_LENGTH + IV_LENGTH + AUTH_TAG_LENGTH + 4;
    if (encryptedBuffer.length < minLength) {
      throw new DecryptionError('加密数据格式无效，数据长度不足');
    }

    let offset = 0;
    const salt = encryptedBuffer.subarray(offset, offset + SALT_LENGTH);
    offset += SALT_LENGTH;

    const iv = encryptedBuffer.subarray(offset, offset + IV_LENGTH);
    offset += IV_LENGTH;

    const authTag = encryptedBuffer.subarray(offset, offset + AUTH_TAG_LENGTH);
    offset += AUTH_TAG_LENGTH;

    const iterations = options.iterations ?? encryptedBuffer.readUInt32BE(offset);
    offset += 4;

    const ciphertext = encryptedBuffer.subarray(offset);

    const key = deriveKey(password, salt, iterations);

    const decipher = createDecipheriv('aes-256-gcm', key, iv);
    decipher.setAuthTag(authTag);

    const decryptedBuffer = Buffer.concat([
      decipher.update(ciphertext),
      decipher.final(),
    ]);

    return decryptedBuffer.toString('utf-8');
  } catch (error) {
    if (error instanceof DecryptionError || error instanceof EncryptionError) {
      throw error;
    }
    if (error instanceof Error && error.message.includes('auth tag')) {
      throw new DecryptionError('解密失败：认证标签不匹配，可能密码错误或数据已被篡改');
    }
    throw new DecryptionError('AES-256-GCM 解密失败，请检查密码或加密数据是否正确', error);
  }
}

export function encryptBuffer(data: Buffer, password: string, options: AESEncryptOptions = {}): Buffer {
  validateBuffer(data, 'data');
  validateString(password, 'password');

  const iterations = options.iterations ?? PBKDF2_ITERATIONS;

  if (iterations < 1000) {
    throw new EncryptionError('迭代次数不能少于 1000，以确保安全性');
  }

  try {
    const salt = randomBytes(SALT_LENGTH);
    const iv = randomBytes(IV_LENGTH);
    const key = deriveKey(password, salt, iterations);

    const cipher = createCipheriv('aes-256-gcm', key, iv);

    const encryptedBuffer = Buffer.concat([
      cipher.update(data),
      cipher.final(),
    ]);

    const authTag = cipher.getAuthTag();

    const iterationsBuffer = Buffer.alloc(4);
    iterationsBuffer.writeUInt32BE(iterations, 0);

    return Buffer.concat([
      salt,
      iv,
      authTag,
      iterationsBuffer,
      encryptedBuffer,
    ]);
  } catch (error) {
    if (error instanceof EncryptionError) {
      throw error;
    }
    throw new EncryptionError('AES-256-GCM Buffer 加密失败', error);
  }
}

export function decryptBuffer(encrypted: Buffer, password: string, options: AESDecryptOptions = {}): Buffer {
  validateBuffer(encrypted, 'encrypted');
  validateString(password, 'password');

  try {
    const minLength = SALT_LENGTH + IV_LENGTH + AUTH_TAG_LENGTH + 4;
    if (encrypted.length < minLength) {
      throw new DecryptionError('加密数据格式无效，数据长度不足');
    }

    let offset = 0;
    const salt = encrypted.subarray(offset, offset + SALT_LENGTH);
    offset += SALT_LENGTH;

    const iv = encrypted.subarray(offset, offset + IV_LENGTH);
    offset += IV_LENGTH;

    const authTag = encrypted.subarray(offset, offset + AUTH_TAG_LENGTH);
    offset += AUTH_TAG_LENGTH;

    const iterations = options.iterations ?? encrypted.readUInt32BE(offset);
    offset += 4;

    const ciphertext = encrypted.subarray(offset);

    const key = deriveKey(password, salt, iterations);

    const decipher = createDecipheriv('aes-256-gcm', key, iv);
    decipher.setAuthTag(authTag);

    return Buffer.concat([
      decipher.update(ciphertext),
      decipher.final(),
    ]);
  } catch (error) {
    if (error instanceof DecryptionError || error instanceof EncryptionError) {
      throw error;
    }
    if (error instanceof Error && error.message.includes('auth tag')) {
      throw new DecryptionError('解密失败：认证标签不匹配，可能密码错误或数据已被篡改');
    }
    throw new DecryptionError('AES-256-GCM Buffer 解密失败，请检查密码或加密数据是否正确', error);
  }
}

export async function encryptFile(inputPath: string, outputPath: string, password: string, options: AESEncryptOptions = {}): Promise<void> {
  validateString(inputPath, 'inputPath');
  validateString(outputPath, 'outputPath');
  validateString(password, 'password');

  const fs = await import('node:fs');

  try {
    const data = fs.readFileSync(inputPath);
    const encrypted = encryptBuffer(data, password, options);
    fs.writeFileSync(outputPath, encrypted);
  } catch (error) {
    if (error instanceof EncryptionError) {
      throw error;
    }
    throw new EncryptionError(`文件加密失败: ${inputPath} -> ${outputPath}`, error);
  }
}

export async function decryptFile(inputPath: string, outputPath: string, password: string, options: AESDecryptOptions = {}): Promise<void> {
  validateString(inputPath, 'inputPath');
  validateString(outputPath, 'outputPath');
  validateString(password, 'password');

  const fs = await import('node:fs');

  try {
    const data = fs.readFileSync(inputPath);
    const decrypted = decryptBuffer(data, password, options);
    fs.writeFileSync(outputPath, decrypted);
  } catch (error) {
    if (error instanceof DecryptionError) {
      throw error;
    }
    throw new DecryptionError(`文件解密失败: ${inputPath} -> ${outputPath}`, error);
  }
}

export function hashPassword(password: string, salt?: string): { hash: string; salt: string } {
  validateString(password, 'password');

  try {
    const saltBuffer = salt ? Buffer.from(salt, 'hex') : randomBytes(SALT_LENGTH);
    const hash = pbkdf2Sync(password, saltBuffer, PBKDF2_ITERATIONS, KEY_LENGTH, 'sha256');
    return {
      hash: hash.toString('hex'),
      salt: saltBuffer.toString('hex'),
    };
  } catch (error) {
    throw new EncryptionError('密码哈希失败', error);
  }
}

export function verifyPassword(password: string, hash: string, salt: string): boolean {
  validateString(password, 'password');
  validateString(hash, 'hash');
  validateString(salt, 'salt');

  try {
    const result = pbkdf2Sync(password, Buffer.from(salt, 'hex'), PBKDF2_ITERATIONS, KEY_LENGTH, 'sha256');
    const expected = Buffer.from(hash, 'hex');

    if (result.length !== expected.length) {
      return false;
    }

    let diff = 0;
    for (let i = 0; i < result.length; i++) {
      diff |= result[i] ^ expected[i];
    }
    return diff === 0;
  } catch {
    return false;
  }
}

export function sha256(data: string): string {
  validateString(data, 'data');

  try {
    return createHash('sha256').update(data).digest('hex');
  } catch (error) {
    throw new EncryptionError('SHA-256 哈希计算失败', error);
  }
}

export function sha512(data: string): string {
  validateString(data, 'data');

  try {
    return createHash('sha512').update(data).digest('hex');
  } catch (error) {
    throw new EncryptionError('SHA-512 哈希计算失败', error);
  }
}

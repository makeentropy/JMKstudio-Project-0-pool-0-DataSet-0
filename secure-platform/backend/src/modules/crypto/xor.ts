import { validateString, validateArray, EncryptionError, DecryptionError } from './errors';

export function xorEncrypt(data: string, key: string): string {
  validateString(data, 'data');
  validateString(key, 'key');

  try {
    const dataBuffer = Buffer.from(data, 'utf-8');
    const keyBuffer = Buffer.from(key, 'utf-8');
    const result = Buffer.alloc(dataBuffer.length);

    for (let i = 0; i < dataBuffer.length; i++) {
      result[i] = dataBuffer[i] ^ keyBuffer[i % keyBuffer.length];
    }

    return result.toString('hex');
  } catch (error) {
    throw new EncryptionError('XOR 加密失败', error);
  }
}

export function xorDecrypt(encrypted: string, key: string): string {
  validateString(encrypted, 'encrypted');
  validateString(key, 'key');

  try {
    const encryptedBuffer = Buffer.from(encrypted, 'hex');
    const keyBuffer = Buffer.from(key, 'utf-8');
    const result = Buffer.alloc(encryptedBuffer.length);

    for (let i = 0; i < encryptedBuffer.length; i++) {
      result[i] = encryptedBuffer[i] ^ keyBuffer[i % keyBuffer.length];
    }

    return result.toString('utf-8');
  } catch (error) {
    throw new DecryptionError('XOR 解密失败，请检查加密数据或密钥是否正确', error);
  }
}

export function multiLayerXor(data: string, keys: string[]): string {
  validateString(data, 'data');
  validateArray<string>(keys, 'keys');

  for (let i = 0; i < keys.length; i++) {
    validateString(keys[i], `keys[${i}]`);
  }

  try {
    let result = data;

    for (const key of keys) {
      result = xorEncrypt(result, key);
    }

    return result;
  } catch (error) {
    if (error instanceof EncryptionError) {
      throw error;
    }
    throw new EncryptionError('多层 XOR 加密失败', error);
  }
}

export function multiLayerXorDecrypt(encrypted: string, keys: string[]): string {
  validateString(encrypted, 'encrypted');
  validateArray<string>(keys, 'keys');

  for (let i = 0; i < keys.length; i++) {
    validateString(keys[i], `keys[${i}]`);
  }

  try {
    let result = encrypted;

    for (let i = keys.length - 1; i >= 0; i--) {
      result = xorDecrypt(result, keys[i]);
    }

    return result;
  } catch (error) {
    if (error instanceof DecryptionError) {
      throw error;
    }
    throw new DecryptionError('多层 XOR 解密失败，请检查密钥顺序是否正确', error);
  }
}

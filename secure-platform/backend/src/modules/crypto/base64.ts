import { validateString, EncodingError, DecodingError } from './errors';

export function base64Encode(data: string): string {
  validateString(data, 'data');

  try {
    return Buffer.from(data, 'utf-8').toString('base64');
  } catch (error) {
    throw new EncodingError('Base64 编码失败', error);
  }
}

export function base64Decode(encoded: string): string {
  validateString(encoded, 'encoded');

  try {
    const buffer = Buffer.from(encoded, 'base64');
    const result = buffer.toString('utf-8');
    if (buffer.length > 0 && result === '') {
      throw new Error('解码结果为空，可能输入不是有效的 Base64 字符串');
    }
    return result;
  } catch (error) {
    throw new DecodingError('Base64 解码失败，请检查输入是否为有效的 Base64 字符串', error);
  }
}

export function base64EncodeBuffer(data: Buffer): string {
  if (!Buffer.isBuffer(data)) {
    throw new EncodingError('参数 "data" 必须是 Buffer 类型');
  }

  try {
    return data.toString('base64');
  } catch (error) {
    throw new EncodingError('Base64 Buffer 编码失败', error);
  }
}

export function base64DecodeBuffer(encoded: string): Buffer {
  validateString(encoded, 'encoded');

  try {
    return Buffer.from(encoded, 'base64');
  } catch (error) {
    throw new DecodingError('Base64 Buffer 解码失败', error);
  }
}

export function urlSafeBase64Encode(data: string): string {
  validateString(data, 'data');

  try {
    const base64 = Buffer.from(data, 'utf-8').toString('base64');
    return base64
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '');
  } catch (error) {
    throw new EncodingError('URL 安全 Base64 编码失败', error);
  }
}

export function urlSafeBase64Decode(encoded: string): string {
  validateString(encoded, 'encoded');

  try {
    let base64 = encoded
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    const padLength = (4 - (base64.length % 4)) % 4;
    base64 += '='.repeat(padLength);

    const buffer = Buffer.from(base64, 'base64');
    const result = buffer.toString('utf-8');
    if (buffer.length > 0 && result === '') {
      throw new Error('解码结果为空，可能输入不是有效的 URL 安全 Base64 字符串');
    }
    return result;
  } catch (error) {
    throw new DecodingError('URL 安全 Base64 解码失败，请检查输入是否正确', error);
  }
}

export function urlSafeBase64EncodeBuffer(data: Buffer): string {
  if (!Buffer.isBuffer(data)) {
    throw new EncodingError('参数 "data" 必须是 Buffer 类型');
  }

  try {
    const base64 = data.toString('base64');
    return base64
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '');
  } catch (error) {
    throw new EncodingError('URL 安全 Base64 Buffer 编码失败', error);
  }
}

export function urlSafeBase64DecodeBuffer(encoded: string): Buffer {
  validateString(encoded, 'encoded');

  try {
    let base64 = encoded
      .replace(/-/g, '+')
      .replace(/_/g, '/');

    const padLength = (4 - (base64.length % 4)) % 4;
    base64 += '='.repeat(padLength);

    return Buffer.from(base64, 'base64');
  } catch (error) {
    throw new DecodingError('URL 安全 Base64 Buffer 解码失败', error);
  }
}

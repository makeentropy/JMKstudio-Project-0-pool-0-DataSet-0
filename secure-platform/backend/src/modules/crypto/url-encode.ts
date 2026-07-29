import { validateString, EncodingError, DecodingError } from './errors';

export function urlEncode(data: string): string {
  validateString(data, 'data');

  try {
    return encodeURIComponent(data);
  } catch (error) {
    throw new EncodingError('URL 编码失败', error);
  }
}

export function urlDecode(encoded: string): string {
  validateString(encoded, 'encoded');

  try {
    return decodeURIComponent(encoded);
  } catch (error) {
    throw new DecodingError('URL 解码失败，请检查输入是否包含有效的 URL 编码字符', error);
  }
}

export function queryStringEncode(params: Record<string, unknown>): string {
  if (typeof params !== 'object' || params === null || Array.isArray(params)) {
    throw new EncodingError('参数 "params" 必须是对象类型');
  }

  try {
    const parts: string[] = [];

    for (const key of Object.keys(params)) {
      const value = params[key];

      if (value === undefined || value === null) {
        continue;
      }

      const encodedKey = encodeURIComponent(key);

      if (Array.isArray(value)) {
        for (const item of value) {
          const encodedValue = encodeURIComponent(String(item));
          parts.push(`${encodedKey}[]=${encodedValue}`);
        }
      } else if (typeof value === 'object') {
        parts.push(`${encodedKey}=${encodeURIComponent(JSON.stringify(value))}`);
      } else {
        const encodedValue = encodeURIComponent(String(value));
        parts.push(`${encodedKey}=${encodedValue}`);
      }
    }

    return parts.join('&');
  } catch (error) {
    throw new EncodingError('查询字符串编码失败', error);
  }
}

export function queryStringDecode(queryString: string): Record<string, unknown> {
  validateString(queryString, 'queryString');

  try {
    let qs = queryString;
    if (qs.startsWith('?')) {
      qs = qs.slice(1);
    }

    if (qs.length === 0) {
      return {};
    }

    const result: Record<string, unknown> = {};
    const pairs = qs.split('&');

    for (const pair of pairs) {
      if (!pair) continue;

      const [rawKey, rawValue] = pair.split('=');
      const key = decodeURIComponent(rawKey || '');
      const value = rawValue !== undefined ? decodeURIComponent(rawValue) : '';

      if (key.endsWith('[]')) {
        const actualKey = key.slice(0, -2);
        if (!result[actualKey]) {
          result[actualKey] = [];
        }
        (result[actualKey] as unknown[]).push(value);
      } else {
        let parsedValue: unknown = value;
        try {
          if ((value.startsWith('{') && value.endsWith('}')) ||
              (value.startsWith('[') && value.endsWith(']'))) {
            parsedValue = JSON.parse(value);
          }
        } catch {
        }
        result[key] = parsedValue;
      }
    }

    return result;
  } catch (error) {
    if (error instanceof DecodingError) {
      throw error;
    }
    throw new DecodingError('查询字符串解码失败', error);
  }
}

export function buildUrl(baseUrl: string, params?: Record<string, unknown>): string {
  validateString(baseUrl, 'baseUrl');

  if (params === undefined) {
    return baseUrl;
  }

  const query = queryStringEncode(params);

  if (!query) {
    return baseUrl;
  }

  const separator = baseUrl.includes('?') ? '&' : '?';
  return `${baseUrl}${separator}${query}`;
}

export function parseUrl(url: string): { baseUrl: string; params: Record<string, unknown> } {
  validateString(url, 'url');

  try {
    const queryIndex = url.indexOf('?');

    if (queryIndex === -1) {
      return { baseUrl: url, params: {} };
    }

    const baseUrl = url.slice(0, queryIndex);
    const queryString = url.slice(queryIndex + 1);
    const params = queryStringDecode(queryString);

    return { baseUrl, params };
  } catch (error) {
    throw new DecodingError('URL 解析失败', error);
  }
}

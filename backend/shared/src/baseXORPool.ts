import * as crypto from 'crypto';

export class BaseXORPool {
  private apiToken: string;

  constructor(apiToken: string) {
    this.apiToken = apiToken;
  }

  xorCrypt(data: string, key: string): string {
    const dataBytes = Buffer.from(data, 'utf-8');
    const keyBytes = Buffer.from(key, 'utf-8');
    const result = Buffer.alloc(dataBytes.length);

    for (let i = 0; i < dataBytes.length; i++) {
      result[i] = dataBytes[i] ^ keyBytes[i % keyBytes.length];
    }

    return result.toString('base64');
  }

  xorDecrypt(encrypted: string, key: string): string {
    const dataBytes = Buffer.from(encrypted, 'base64');
    const keyBytes = Buffer.from(key, 'utf-8');
    const result = Buffer.alloc(dataBytes.length);

    for (let i = 0; i < dataBytes.length; i++) {
      result[i] = dataBytes[i] ^ keyBytes[i % keyBytes.length];
    }

    return result.toString('utf-8');
  }

  signTag(tagId: string, expireTs: number): string {
    const rawPayload = `${tagId}|${expireTs}|${this.apiToken}`;
    return this.xorCrypt(rawPayload, this.apiToken);
  }

  verifyTag(signedStr: string): { valid: boolean; tagId: string; expire: number } {
    try {
      const raw = this.xorDecrypt(signedStr, this.apiToken);
      const parts = raw.split('|');
      if (parts.length !== 3) {
        return { valid: false, tagId: '', expire: 0 };
      }

      const [tagId, expireStr, token] = parts;
      const expire = parseInt(expireStr, 10);

      if (token === this.apiToken && Date.now() / 1000 < expire) {
        return { valid: true, tagId, expire };
      }

      return { valid: false, tagId: '', expire: 0 };
    } catch {
      return { valid: false, tagId: '', expire: 0 };
    }
  }

  genRandomStr(length: number): string {
    return crypto.randomBytes(Math.ceil(length / 2)).toString('hex').slice(0, length);
  }

  genUuid(): string {
    return crypto.randomUUID();
  }

  timestamp(): number {
    return Math.floor(Date.now() / 1000);
  }
}

export const createBaseXORPool = (apiToken: string) => {
  return new BaseXORPool(apiToken);
};

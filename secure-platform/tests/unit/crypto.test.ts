import {
  xorEncrypt,
  xorDecrypt,
  multiLayerXor,
  multiLayerXorDecrypt,
  base64Encode,
  base64Decode,
  urlSafeBase64Encode,
  urlSafeBase64Decode,
  aesEncrypt,
  aesDecrypt,
  hashPassword,
  verifyPassword,
  sha256,
  generateKeyPair,
  hybridEncrypt,
  hybridDecrypt,
  sign,
  verify,
  encodeMessageIntoImage,
  decodeMessageFromImage,
  getImageCapacity,
} from '../../backend/src/modules/crypto';
import { DecryptionError, ValidationError } from '../../backend/src/modules/crypto/errors';

const createPNGBuffer = (width: number, height: number): Buffer => {
  const signature = Buffer.from([0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a]);

  const ihdrData = Buffer.alloc(13);
  ihdrData.writeUInt32BE(width, 0);
  ihdrData.writeUInt32BE(height, 4);
  ihdrData[8] = 8;
  ihdrData[9] = 2;
  ihdrData[10] = 0;
  ihdrData[11] = 0;
  ihdrData[12] = 0;

  const { createHash } = require('node:crypto');
  const crc32 = (buf: Buffer): number => {
    let crc = 0xffffffff;
    const table = new Uint32Array(256);
    for (let n = 0; n < 256; n++) {
      let c = n;
      for (let k = 0; k < 8; k++) {
        c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
      }
      table[n] = c >>> 0;
    }
    for (let i = 0; i < buf.length; i++) {
      crc = table[(crc ^ buf[i]) & 0xff] ^ (crc >>> 8);
    }
    return (crc ^ 0xffffffff) >>> 0;
  };

  const ihdrType = Buffer.from('IHDR');
  const ihdrCrcData = Buffer.concat([ihdrType, ihdrData]);
  const ihdrCrcValue = crc32(ihdrCrcData);
  const ihdrCrc = Buffer.alloc(4);
  ihdrCrc.writeUInt32BE(ihdrCrcValue, 0);
  const ihdrLength = Buffer.alloc(4);
  ihdrLength.writeUInt32BE(13, 0);
  const ihdrChunk = Buffer.concat([ihdrLength, ihdrType, ihdrData, ihdrCrc]);

  const { deflateSync } = require('node:zlib');
  const channels = 3;
  const rawRowSize = width * channels + 1;
  const rawData = Buffer.alloc(height * rawRowSize);
  for (let y = 0; y < height; y++) {
    rawData[y * rawRowSize] = 0;
    for (let x = 0; x < width; x++) {
      const offset = y * rawRowSize + 1 + x * channels;
      rawData[offset] = 255;
      rawData[offset + 1] = 255;
      rawData[offset + 2] = 255;
    }
  }
  const compressed = deflateSync(rawData);

  const idatType = Buffer.from('IDAT');
  const idatLength = Buffer.alloc(4);
  idatLength.writeUInt32BE(compressed.length, 0);
  const idatCrcData = Buffer.concat([idatType, compressed]);
  const idatCrcValue = crc32(idatCrcData);
  const idatCrc = Buffer.alloc(4);
  idatCrc.writeUInt32BE(idatCrcValue, 0);
  const idatChunk = Buffer.concat([idatLength, idatType, compressed, idatCrc]);

  const iendType = Buffer.from('IEND');
  const iendLength = Buffer.alloc(4);
  iendLength.writeUInt32BE(0, 0);
  const iendCrcData = iendType;
  const iendCrcValue = crc32(iendCrcData);
  const iendCrc = Buffer.alloc(4);
  iendCrc.writeUInt32BE(iendCrcValue, 0);
  const iendChunk = Buffer.concat([iendLength, iendType, iendCrc]);

  return Buffer.concat([signature, ihdrChunk, idatChunk, iendChunk]);
};

describe('XOR Cipher', () => {
  it('should encrypt and decrypt with same key', () => {
    const data = 'Hello, Secure Platform!';
    const key = 'test-key-123';
    const encrypted = xorEncrypt(data, key);
    expect(encrypted).not.toBe(data);
    const decrypted = xorDecrypt(encrypted, key);
    expect(decrypted).toBe(data);
  });

  it('should fail decrypt with wrong key', () => {
    const data = 'Secret message';
    const encrypted = xorEncrypt(data, 'correct-key');
    expect(() => xorDecrypt(encrypted, 'wrong-key')).not.toThrow();
    const wrong = xorDecrypt(encrypted, 'wrong-key');
    expect(wrong).not.toBe(data);
  });

  it('should handle multi-layer XOR encryption', () => {
    const data = 'Multi-layer secure data';
    const keys = ['layer1', 'layer2', 'layer3'];
    const encrypted = multiLayerXor(data, keys);
    expect(encrypted).not.toBe(data);
    const decrypted = multiLayerXorDecrypt(encrypted, keys);
    expect(decrypted).toBe(data);
  });

  it('should fail multi-layer decrypt with wrong key order', () => {
    const data = 'Order matters';
    const keys = ['a', 'b', 'c'];
    const encrypted = multiLayerXor(data, keys);
    const wrongOrder = multiLayerXorDecrypt(encrypted, ['c', 'b', 'a']);
    expect(wrongOrder).not.toBe(data);
  });

  it('should work with different keys of various lengths', () => {
    const testCases = [
      { data: 'short', key: 'k' },
      { data: 'medium length text here', key: 'key-with-medium-length-1234567890' },
      { data: 'A'.repeat(1000), key: 'long'.repeat(50) },
    ];
    for (const tc of testCases) {
      const enc = xorEncrypt(tc.data, tc.key);
      const dec = xorDecrypt(enc, tc.key);
      expect(dec).toBe(tc.data);
    }
  });

  it('should throw on invalid input', () => {
    expect(() => xorEncrypt('', 'key')).toThrow(ValidationError);
    expect(() => xorEncrypt('data', '')).toThrow(ValidationError);
  });
});

describe('Base64', () => {
  it('should encode and decode correctly', () => {
    const original = 'Hello World! 你好世界！@#$%^&*()';
    const encoded = base64Encode(original);
    expect(encoded).toMatch(/^[A-Za-z0-9+/=]+$/);
    const decoded = base64Decode(encoded);
    expect(decoded).toBe(original);
  });

  it('should handle URL-safe Base64 variant', () => {
    const tests = [
      'Hello?param=1&other=2#hash',
      '<script>alert("xss")</script>',
      'binary\xff\x00data',
    ];
    for (const data of tests) {
      const encoded = urlSafeBase64Encode(data);
      expect(encoded).not.toContain('+');
      expect(encoded).not.toContain('/');
      expect(encoded).not.toContain('=');
      const decoded = urlSafeBase64Decode(encoded);
      expect(decoded).toBe(data);
    }
  });

  it('standard vs URL-safe should differ on special chars', () => {
    const data = '\xfb\xef\xbe';
    const standard = base64Encode(data);
    const urlSafe = urlSafeBase64Encode(data);
    const converted = standard
      .replace(/\+/g, '-')
      .replace(/\//g, '_')
      .replace(/=+$/, '');
    expect(converted).toBe(urlSafe);
  });

  it('should throw on empty string', () => {
    expect(() => base64Encode('')).toThrow(ValidationError);
    expect(() => base64Decode('')).toThrow(ValidationError);
  });

  it('should handle long strings', () => {
    const long = 'Lorem ipsum dolor sit amet '.repeat(100);
    const enc = base64Encode(long);
    const dec = base64Decode(enc);
    expect(dec).toBe(long);
  });
});

describe('AES-256-GCM', () => {
  const PASSWORD = 'Strong-Password-2024!';

  it('should encrypt and decrypt correctly', () => {
    const data = 'Sensitive data: credit card 4111-1111-1111-1111';
    const encrypted = aesEncrypt(data, PASSWORD);
    expect(encrypted).not.toBe(data);
    const decrypted = aesDecrypt(encrypted, PASSWORD);
    expect(decrypted).toBe(data);
  });

  it('should throw error on wrong password', () => {
    const data = 'Top secret';
    const encrypted = aesEncrypt(data, PASSWORD);
    expect(() => aesDecrypt(encrypted, 'wrong-password')).toThrow(DecryptionError);
  });

  it('PBKDF2 should produce consistent hash results', () => {
    const password = 'user-password';
    const { hash, salt } = hashPassword(password);
    expect(hash).toHaveLength(64);
    expect(salt).toHaveLength(32);

    const { hash: hash2 } = hashPassword(password, salt);
    expect(hash2).toBe(hash);

    expect(verifyPassword(password, hash, salt)).toBe(true);
    expect(verifyPassword('wrong', hash, salt)).toBe(false);
  });

  it('each encryption should produce different output (random salt/iv)', () => {
    const data = 'Same data each time';
    const enc1 = aesEncrypt(data, PASSWORD);
    const enc2 = aesEncrypt(data, PASSWORD);
    expect(enc1).not.toBe(enc2);
    expect(aesDecrypt(enc1, PASSWORD)).toBe(data);
    expect(aesDecrypt(enc2, PASSWORD)).toBe(data);
  });

  it('should handle unicode and binary data', () => {
    const cases = [
      '中文密码测试 🔐 安全',
      '\x00\x01\x02\xff binary data \r\n\t',
      JSON.stringify({ nested: { obj: [1, 2, 3] } }),
    ];
    for (const c of cases) {
      const enc = aesEncrypt(c, PASSWORD + 'uni');
      const dec = aesDecrypt(enc, PASSWORD + 'uni');
      expect(dec).toBe(c);
    }
  });

  it('sha256 should produce deterministic 64 char hex', () => {
    const h1 = sha256('hello');
    const h2 = sha256('hello');
    expect(h1).toHaveLength(64);
    expect(h1).toBe(h2);
    expect(sha256('hello')).not.toBe(sha256('world'));
  });

  it('should enforce minimum iterations', () => {
    expect(() => aesEncrypt('d', 'p', { iterations: 100 })).toThrow();
  });
});

describe('GPG Hybrid', () => {
  jest.setTimeout(60000);

  let keyPair: { publicKey: string; privateKey: string };

  beforeAll(async () => {
    keyPair = await generateKeyPair();
  });

  it('should generate valid key pair', async () => {
    expect(keyPair.publicKey).toBeTruthy();
    expect(keyPair.privateKey).toBeTruthy();
    expect(keyPair.publicKey).not.toBe(keyPair.privateKey);
    expect(typeof keyPair.publicKey).toBe('string');
    expect(typeof keyPair.privateKey).toBe('string');
  });

  it('should encrypt and decrypt with key pair', async () => {
    const data = 'Hybrid encrypted: RSA-4096 + AES-256-GCM';
    const encrypted = await hybridEncrypt(data, keyPair.publicKey);
    expect(encrypted).not.toBe(data);
    const decrypted = await hybridDecrypt(encrypted, keyPair.privateKey);
    expect(decrypted).toBe(data);
  });

  it('should produce valid signature and verify', async () => {
    const data = 'Document signed by SecurePlatform';
    const signature = await sign(data, keyPair.privateKey);
    expect(signature).toBeTruthy();
    const verified = await verify(data, signature, keyPair.publicKey);
    expect(verified).toBe(true);

    const tamperedData = 'Document tampered by attacker';
    const fakeVerify = await verify(tamperedData, signature, keyPair.publicKey);
    expect(fakeVerify).toBe(false);

    const badSig = signature.replace(/[A-Za-z]/g, (c) => (c.charCodeAt(0) % 2 === 0 ? c : String.fromCharCode(c.charCodeAt(0) + 1 > 122 ? c.charCodeAt(0) - 1 : c.charCodeAt(0) + 1)));
    await expect(verify(data, badSig, keyPair.publicKey)).resolves.not.toThrow();
  });

  it('different keys should not decrypt each other', async () => {
    const kp2 = await generateKeyPair();
    const data = 'For user A only';
    const encA = await hybridEncrypt(data, keyPair.publicKey);
    await expect(hybridDecrypt(encA, kp2.privateKey)).rejects.toThrow();
  });

  it('should handle large messages', async () => {
    const largeMsg = 'PAYLOAD_BLOCK-'.repeat(500);
    const enc = await hybridEncrypt(largeMsg, keyPair.publicKey);
    const dec = await hybridDecrypt(enc, keyPair.privateKey);
    expect(dec).toBe(largeMsg);
  });
});

describe('Steganography', () => {
  let testImage: Buffer;

  beforeAll(() => {
    testImage = createPNGBuffer(100, 100);
  });

  it('should create valid PNG buffer', () => {
    expect(testImage[0]).toBe(0x89);
    expect(testImage.toString('ascii', 1, 4)).toBe('PNG');
  });

  it('should encode and decode message round trip', () => {
    const message = 'Secret hidden message in the image pixels! 🔍';
    const encoded = encodeMessageIntoImage(testImage, message);
    expect(Buffer.isBuffer(encoded)).toBe(true);
    expect(encoded.length).toBeGreaterThan(0);
    expect(encoded[0]).toBe(0x89);
    const decoded = decodeMessageFromImage(encoded);
    expect(decoded).toBe(message);
  });

  it('should encode/decode with password protection', () => {
    const message = 'Password protected hidden content';
    const password = 'stego-pass-2024';
    const encoded = encodeMessageIntoImage(testImage, message, password);
    expect(() => decodeMessageFromImage(encoded, 'wrong-password')).toThrow();
    const decoded = decodeMessageFromImage(encoded, password);
    expect(decoded).toBe(message);
  });

  it('capacity calculation should match actual usage', () => {
    const capacity = getImageCapacity(testImage);
    expect(capacity).toBeGreaterThan(100);

    const messageBytes = Math.min(capacity, 2000);
    const message = 'X'.repeat(messageBytes);
    expect(() => encodeMessageIntoImage(testImage, message)).not.toThrow();

    const tooLong = 'Y'.repeat(capacity + 100);
    expect(() => encodeMessageIntoImage(testImage, tooLong)).toThrow();
  });

  it('should preserve PNG structure after encoding', () => {
    const message = 'Structural integrity test';
    const encoded = encodeMessageIntoImage(testImage, message);
    expect(encoded[0]).toBe(0x89);
    expect(encoded.toString('ascii', 1, 4)).toBe('PNG');
    const ihdrPos = encoded.indexOf('IHDR');
    expect(ihdrPos).toBeGreaterThan(0);
    const iendPos = encoded.lastIndexOf('IEND');
    expect(iendPos).toBeGreaterThan(ihdrPos);
  });

  it('capacity scales with image dimensions', () => {
    const smallImg = createPNGBuffer(20, 20);
    const bigImg = createPNGBuffer(200, 200);
    const smallCap = getImageCapacity(smallImg);
    const bigCap = getImageCapacity(bigImg);
    expect(bigCap).toBeGreaterThan(smallCap * 10);
  });
});

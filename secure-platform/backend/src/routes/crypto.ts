import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import rateLimit from 'express-rate-limit';
import {
  xorEncrypt,
  xorDecrypt,
  multiLayerXor,
  multiLayerXorDecrypt,
  base64Encode,
  base64Decode,
  base64EncodeBuffer,
  base64DecodeBuffer,
  urlEncode,
  urlDecode,
  aesEncrypt,
  aesDecrypt,
  aesEncryptBuffer,
  aesDecryptBuffer,
  generateKeyPair,
  hybridEncrypt,
  hybridDecrypt,
  encodeMessageIntoImage,
  decodeMessageFromImage,
} from '../modules/crypto';
import { ApiError } from '../app';
import logger from '../utils/logger';

const router = Router();

const cryptoLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 100,
  standardHeaders: true,
  legacyHeaders: false,
  handler: (_req: Request, res: Response): void => {
    res.status(429).json({
      success: false,
      message: '加密工具请求过于频繁，请稍后再试',
      code: 'RATE_LIMIT_EXCEEDED',
    });
  },
});

router.use(cryptoLimiter);

const xorSchema = z.object({
  data: z.string().min(1),
  key: z.string().min(1).optional(),
  keys: z.array(z.string().min(1)).optional(),
});

router.post('/xor/encrypt', (req: Request, res: Response, next: NextFunction): void => {
  try {
    const parsed = xorSchema.parse(req.body);
    const { data, key, keys } = parsed;

    if (keys && keys.length > 0) {
      const result = multiLayerXor(data, keys);
      res.json({ success: true, data: { result } });
    } else if (key) {
      const result = xorEncrypt(data, key);
      res.json({ success: true, data: { result } });
    } else {
      throw new ApiError('必须提供 key 或 keys 参数', { statusCode: 400, code: 'VALIDATION_ERROR' });
    }
  } catch (error) {
    next(error);
  }
});

router.post('/xor/decrypt', (req: Request, res: Response, next: NextFunction): void => {
  try {
    const parsed = xorSchema.parse(req.body);
    const { data, key, keys } = parsed;

    if (keys && keys.length > 0) {
      const result = multiLayerXorDecrypt(data, keys);
      res.json({ success: true, data: { result } });
    } else if (key) {
      const result = xorDecrypt(data, key);
      res.json({ success: true, data: { result } });
    } else {
      throw new ApiError('必须提供 key 或 keys 参数', { statusCode: 400, code: 'VALIDATION_ERROR' });
    }
  } catch (error) {
    next(error);
  }
});

const base64Schema = z.object({
  data: z.union([z.string(), z.instanceof(Buffer)]),
});

router.post('/base64/encode', (req: Request, res: Response, next: NextFunction): void => {
  try {
    const parsed = base64Schema.parse(req.body);
    const { data } = parsed;
    let result: string;
    if (Buffer.isBuffer(data)) {
      result = base64EncodeBuffer(data);
    } else {
      result = base64Encode(data);
    }
    res.json({ success: true, data: { result } });
  } catch (error) {
    next(error);
  }
});

router.post('/base64/decode', (req: Request, res: Response, next: NextFunction): void => {
  try {
    const parsed = z.object({ data: z.string().min(1) }).parse(req.body);
    const result = base64Decode(parsed.data);
    res.json({ success: true, data: { result } });
  } catch (error) {
    next(error);
  }
});

const urlSchema = z.object({
  data: z.string().min(1),
});

router.post('/url/encode', (req: Request, res: Response, next: NextFunction): void => {
  try {
    const parsed = urlSchema.parse(req.body);
    const result = urlEncode(parsed.data);
    res.json({ success: true, data: { result } });
  } catch (error) {
    next(error);
  }
});

router.post('/url/decode', (req: Request, res: Response, next: NextFunction): void => {
  try {
    const parsed = urlSchema.parse(req.body);
    const result = urlDecode(parsed.data);
    res.json({ success: true, data: { result } });
  } catch (error) {
    next(error);
  }
});

const aesSchema = z.object({
  data: z.union([z.string().min(1), z.instanceof(Buffer)]),
  password: z.string().min(8),
});

router.post('/aes/encrypt', (req: Request, res: Response, next: NextFunction): void => {
  try {
    const parsed = aesSchema.parse(req.body);
    const { data, password } = parsed;
    let result: string;
    if (Buffer.isBuffer(data)) {
      result = base64EncodeBuffer(aesEncryptBuffer(data, password));
    } else {
      result = aesEncrypt(data, password);
    }
    res.json({ success: true, data: { result } });
  } catch (error) {
    next(error);
  }
});

router.post('/aes/decrypt', (req: Request, res: Response, next: NextFunction): void => {
  try {
    const parsed = z.object({
      data: z.string().min(1),
      password: z.string().min(8),
    }).parse(req.body);
    const { data, password } = parsed;
    const result = aesDecrypt(data, password);
    res.json({ success: true, data: { result } });
  } catch (error) {
    next(error);
  }
});

router.post('/gpg/generate-keypair', async (_req: Request, res: Response, next: NextFunction): Promise<void> => {
  try {
    const keyPair = await generateKeyPair();
    res.json({
      success: true,
      data: {
        publicKey: keyPair.publicKey,
        privateKey: keyPair.privateKey,
      },
    });
  } catch (error) {
    next(error);
  }
});

const gpgEncryptSchema = z.object({
  data: z.string().min(1),
  publicKeyPem: z.string().min(1),
});

router.post('/gpg/encrypt', async (req: Request, res: Response, next: NextFunction): Promise<void> => {
  try {
    const parsed = gpgEncryptSchema.parse(req.body);
    const result = await hybridEncrypt(parsed.data, parsed.publicKeyPem);
    res.json({ success: true, data: { result } });
  } catch (error) {
    next(error);
  }
});

const gpgDecryptSchema = z.object({
  data: z.string().min(1),
  privateKeyPem: z.string().min(1),
});

router.post('/gpg/decrypt', async (req: Request, res: Response, next: NextFunction): Promise<void> => {
  try {
    const parsed = gpgDecryptSchema.parse(req.body);
    const result = await hybridDecrypt(parsed.data, parsed.privateKeyPem);
    res.json({ success: true, data: { result } });
  } catch (error) {
    next(error);
  }
});

function getStegoMiddleware(): (req: Request, res: Response, next: NextFunction) => void {
  return (_req: Request, _res: Response, next: NextFunction) => {
    next();
  };
}

const stegoUpload = getStegoMiddleware();

const stegoEncodeSchema = z.object({
  imageBase64: z.string().min(1),
  message: z.string().min(1),
  password: z.string().optional(),
});

router.post(
  '/steganography/encode',
  stegoUpload,
  (req: Request, res: Response, next: NextFunction): void => {
    try {
      const parsed = stegoEncodeSchema.parse(req.body);
      const { imageBase64, message, password } = parsed;

      const imageBuffer = Buffer.from(imageBase64, 'base64');
      if (imageBuffer.length === 0) {
        throw new ApiError('imageBase64 不能为空或无效的 base64 字符串', { statusCode: 400, code: 'INVALID_IMAGE' });
      }

      const resultBuffer = encodeMessageIntoImage(imageBuffer, message, password);
      const resultBase64 = resultBuffer.toString('base64');

      res.json({
        success: true,
        data: { imageBase64: resultBase64 },
      });
    } catch (error) {
      next(error);
    }
  }
);

const stegoDecodeSchema = z.object({
  imageBase64: z.string().min(1),
  password: z.string().optional(),
});

router.post(
  '/steganography/decode',
  stegoUpload,
  (req: Request, res: Response, next: NextFunction): void => {
    try {
      const parsed = stegoDecodeSchema.parse(req.body);
      const { imageBase64, password } = parsed;

      const imageBuffer = Buffer.from(imageBase64, 'base64');
      if (imageBuffer.length === 0) {
        throw new ApiError('imageBase64 不能为空或无效的 base64 字符串', { statusCode: 400, code: 'INVALID_IMAGE' });
      }

      const message = decodeMessageFromImage(imageBuffer, password);
      res.json({ success: true, data: { message } });
    } catch (error) {
      next(error);
    }
  }
);

export default router;
export { router as cryptoRoutes };

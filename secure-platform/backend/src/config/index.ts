import dotenv from 'dotenv';
import { z } from 'zod';

dotenv.config();

const nodeEnvSchema = z.enum(['development', 'test', 'production']);
type NodeEnv = z.infer<typeof nodeEnvSchema>;
const currentNodeEnv = (process.env.NODE_ENV as NodeEnv) || 'development';
const isDevOrTest = currentNodeEnv === 'development' || currentNodeEnv === 'test';

/**
 * 开发/测试环境下，若原校验失败则返回 fallback 值，避免启动时因缺少完整配置而崩溃
 */
const withDevFallback = <S extends z.ZodTypeAny>(
  schema: S,
  fallback: z.infer<S>,
  description?: string,
): z.ZodEffects<S, z.infer<S>> => {
  return z.preprocess((val) => {
    const parsed = schema.safeParse(val);
    if (parsed.success) return parsed.data;
    if (isDevOrTest) {
      if (description && typeof process !== 'undefined') {
        // eslint-disable-next-line no-console
        console.warn(
          `[config] ${description} 校验失败，开发/测试环境使用默认 fallback 值`,
        );
      }
      return fallback;
    }
    return val; // 生产环境抛出原校验错误
  }, schema.or(z.any())) as unknown as z.ZodEffects<S, z.infer<S>>;
};

const urlOrEmpty = z.preprocess(
  (v) => (v && typeof v === 'string' && v.startsWith('http') ? v : 'http://localhost/fallback'),
  z.string().url(),
);
const nonEmptyStringOrFallback = (fallback: string, field: string) =>
  withDevFallback(z.string().min(1), fallback, field);
const positiveInt = (defaultVal: number) =>
  z.preprocess((v) => {
    const n = typeof v === 'number' ? v : Number(v);
    return Number.isFinite(n) && n > 0 ? Math.floor(n) : defaultVal;
  }, z.number().int().positive());

const appConfigSchema = z.object({
  nodeEnv: nodeEnvSchema.default('development'),
  port: positiveInt(3000),
  name: z.string().min(1).default('SecurePlatform'),
  apiPrefix: z.preprocess(
    (v) => (typeof v === 'string' && v.startsWith('/') ? v : '/api'),
    z.string().startsWith('/'),
  ),
  // CORS origins 支持开发环境 * + 逗号分隔 URL
  allowedOrigins: z.preprocess((v): string[] => {
    if (Array.isArray(v)) return v as string[];
    if (typeof v !== 'string') return ['http://localhost:3000', 'http://127.0.0.1:3000'];
    const trimmed = v.trim();
    if (!trimmed || trimmed === '*') {
      return ['http://localhost:3000', 'http://127.0.0.1:3000'];
    }
    return trimmed
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
  }, z.array(z.string()).min(1)),
});

const sessionConfigSchema = z.object({
  secret: withDevFallback(z.string().min(32), 'dev-session-secret-change-me-in-production-'.padEnd(64, 'x'), 'session.secret'),
  name: z.string().min(1).default('sp.sid'),
  ttl: positiveInt(86400),
});

const jwtConfigSchema = z.object({
  secret: withDevFallback(z.string().min(32), 'dev-jwt-secret-change-me-in-production-'.padEnd(64, 'y'), 'jwt.secret'),
  issuer: z.string().min(1).default('secure-platform'),
  audience: z.string().min(1).default('secure-platform-api'),
  accessTtl: positiveInt(900),
  refreshTtl: positiveInt(604800),
});

const alipaySignTypeSchema = z.enum(['RSA', 'RSA2']);
type AlipaySignType = z.infer<typeof alipaySignTypeSchema>;

const alipayConfigSchema = z.object({
  appId: nonEmptyStringOrFallback('sandbox-app-id-dev', 'alipay.appId'),
  gateway: z.preprocess(
    (v) =>
      typeof v === 'string' && v.startsWith('http')
        ? v
        : 'https://openapi-sandbox.dl.alipaydev.com/gateway.do',
    z.string().url(),
  ),
  charset: z.string().default('UTF-8'),
  signType: alipaySignTypeSchema.default('RSA2'),
  version: z.string().default('1.0'),
  notifyUrl: urlOrEmpty,
  returnUrl: urlOrEmpty,
  privateKey: nonEmptyStringOrFallback(
    '-----BEGIN RSA PRIVATE KEY-----\nMIIEowIBAAKCAQEAdevFallback\n-----END RSA PRIVATE KEY-----',
    'alipay.privateKey',
  ),
  publicKey: nonEmptyStringOrFallback(
    '-----BEGIN PUBLIC KEY-----\nMIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAdevFallback\n-----END PUBLIC KEY-----',
    'alipay.publicKey',
  ),
  appCertSn: z.string().optional(),
  alipayCertSn: z.string().optional(),
  rootCertSn: z.string().optional(),
});

const redisConfigSchema = z.object({
  host: z.string().min(1).default('localhost'),
  port: positiveInt(6379),
  password: z.string().optional(),
  db: z.preprocess(
    (v) => {
      const n = typeof v === 'number' ? v : Number(v);
      return Number.isFinite(n) && n >= 0 ? Math.floor(n) : 0;
    },
    z.number().int().nonnegative(),
  ),
});

const logConfigSchema = z.object({
  level: z
    .enum(['error', 'warn', 'info', 'http', 'verbose', 'debug', 'silly'])
    .default('info'),
  dir: z.string().min(1).default('./logs'),
});

const configSchema = z.object({
  app: appConfigSchema,
  session: sessionConfigSchema,
  jwt: jwtConfigSchema,
  alipay: alipayConfigSchema,
  redis: redisConfigSchema,
  log: logConfigSchema,
});

export type AppConfig = z.infer<typeof appConfigSchema>;
export type SessionConfig = z.infer<typeof sessionConfigSchema>;
export type JwtConfig = z.infer<typeof jwtConfigSchema>;
export type AlipayConfig = z.infer<typeof alipayConfigSchema>;
export type RedisConfig = z.infer<typeof redisConfigSchema>;
export type LogConfig = z.infer<typeof logConfigSchema>;
export type Config = z.infer<typeof configSchema>;

const parseAllowedOrigins = (value: string | undefined): string[] => {
  if (!value) return [];
  return value.split(',').map((origin) => origin.trim()).filter(Boolean);
};

const rawConfig = {
  app: {
    nodeEnv: process.env.NODE_ENV || 'development',
    port: process.env.PORT || 3000,
    name: process.env.APP_NAME || 'SecurePlatform',
    apiPrefix: process.env.API_PREFIX || '/api',
    allowedOrigins: parseAllowedOrigins(process.env.ALLOWED_ORIGINS || process.env.CORS_ORIGIN),
  },
  session: {
    secret: process.env.SESSION_SECRET || '',
    name: process.env.SESSION_NAME || 'sp.sid',
    ttl: process.env.SESSION_TTL_SECONDS || process.env.SESSION_TTL || 86400,
  },
  jwt: {
    secret: process.env.JWT_SECRET || '',
    issuer: process.env.JWT_ISSUER || 'secure-platform',
    audience: process.env.JWT_AUDIENCE || 'secure-platform-api',
    accessTtl: process.env.JWT_ACCESS_TTL || 900,
    refreshTtl: process.env.JWT_REFRESH_TTL || 604800,
  },
  alipay: {
    appId: process.env.ALIPAY_APP_ID || '',
    gateway: process.env.ALIPAY_GATEWAY || 'https://openapi-sandbox.dl.alipaydev.com/gateway.do',
    charset: process.env.ALIPAY_CHARSET || 'UTF-8',
    signType: process.env.ALIPAY_SIGN_TYPE || 'RSA2',
    version: process.env.ALIPAY_VERSION || '1.0',
    notifyUrl: process.env.ALIPAY_NOTIFY_URL || '',
    returnUrl: process.env.ALIPAY_RETURN_URL || '',
    privateKey: process.env.ALIPAY_PRIVATE_KEY || '',
    publicKey: process.env.ALIPAY_PUBLIC_KEY || '',
    appCertSn: process.env.ALIPAY_APP_CERT_SN,
    alipayCertSn: process.env.ALIPAY_ALIPAY_CERT_SN,
    rootCertSn: process.env.ALIPAY_ROOT_CERT_SN,
  },
  redis: {
    host: process.env.REDIS_HOST || 'localhost',
    port: process.env.REDIS_PORT || 6379,
    password: process.env.REDIS_PASSWORD,
    db: process.env.REDIS_DB || 0,
  },
  log: {
    level: process.env.LOG_LEVEL || 'info',
    dir: process.env.LOG_DIR || './logs',
  },
};

const validateConfig = (): Config => {
  try {
    return configSchema.parse(rawConfig);
  } catch (error) {
    if (error instanceof z.ZodError) {
      const issues = error.issues.map((issue) => {
        const path = issue.path.join('.');
        return `[${path}]: ${issue.message}`;
      });
      throw new Error(`配置验证失败:\n${issues.join('\n')}`);
    }
    throw error;
  }
};

export const config: Config = validateConfig();
export const isProduction = config.app.nodeEnv === 'production';
export const isDevelopment = config.app.nodeEnv === 'development';
export const isTest = config.app.nodeEnv === 'test';

export { NodeEnv, AlipaySignType };
export default config;

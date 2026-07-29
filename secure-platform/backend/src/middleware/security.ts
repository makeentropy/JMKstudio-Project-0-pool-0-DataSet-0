import { Request, Response, NextFunction, RequestHandler } from 'express';
import helmet, { HelmetOptions } from 'helmet';
import cors from 'cors';
import rateLimit from 'express-rate-limit';
import session from 'express-session';
import RedisStore from 'connect-redis';
import Redis from 'ioredis';
import crypto from 'crypto';
import { v4 as uuidv4 } from 'uuid';
import { config, isProduction } from '../config';
import logger from '../utils/logger';

declare module 'express-session' {
  interface SessionData {
    userId?: string;
    csrfToken?: string;
    lastActivity?: number;
  }
}

declare global {
  namespace Express {
    interface Request {
      requestId: string;
      nonce: string;
    }
  }
}

export const nonceMiddleware = (req: Request, _res: Response, next: NextFunction): void => {
  req.nonce = crypto.randomBytes(16).toString('base64');
  next();
};

export const helmetConfig = (): RequestHandler => {
  return (req: Request, res: Response, next: NextFunction): void => {
    const nonce = req.nonce;
    const helmetOptions: HelmetOptions = {
      contentSecurityPolicy: {
        useDefaults: false,
        directives: {
          defaultSrc: ["'self'"],
          scriptSrc: ["'self'", `'nonce-${nonce}'`],
          styleSrc: ["'self'"],
          imgSrc: ["'self'", 'data:'],
          fontSrc: ["'self'"],
          connectSrc: ["'self'"],
          frameAncestors: ["'self'"],
          objectSrc: ["'none'"],
          baseUri: ["'self'"],
          formAction: ["'self'"],
          frameSrc: ["'none'"],
          mediaSrc: ["'none'"],
          manifestSrc: ["'self'"],
          workerSrc: ["'none'"],
          upgradeInsecureRequests: isProduction ? [] : null,
        },
      },
      hsts: isProduction
        ? {
            maxAge: 31536000,
            includeSubDomains: true,
            preload: true,
          }
        : false,
      frameguard: { action: 'deny' },
      xssFilter: true,
      noSniff: true,
      hidePoweredBy: true,
      permittedCrossDomainPolicies: { permittedPolicies: 'none' },
      referrerPolicy: { policy: 'strict-origin-when-cross-origin' },
      crossOriginEmbedderPolicy: isProduction ? { policy: 'require-corp' } : false,
      crossOriginOpenerPolicy: { policy: 'same-origin' },
      crossOriginResourcePolicy: { policy: 'same-origin' },
      originAgentCluster: true,
      dnsPrefetchControl: { allow: false },
      ieNoOpen: true,
    };
    helmet(helmetOptions)(req, res, next);
  };
};

export const corsConfig = (): RequestHandler => {
  const allowedOrigins = new Set(config.app.allowedOrigins);

  return cors({
    origin: (origin, callback) => {
      if (!origin) {
        if (isProduction) {
          logger.warn('CORS拒绝无来源请求');
          return callback(new Error('不允许的来源'));
        }
        return callback(null, true);
      }
      if (allowedOrigins.has(origin)) {
        return callback(null, true);
      }
      logger.warn('CORS拒绝请求', { origin });
      callback(new Error(`不允许的来源: ${origin}`));
    },
    methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'],
    allowedHeaders: [
      'Content-Type',
      'Authorization',
      'X-Request-ID',
      'X-CSRF-Token',
      'Accept',
      'Accept-Language',
      'Content-Language',
    ],
    exposedHeaders: ['X-Request-ID'],
    credentials: true,
    maxAge: 86400,
    preflightContinue: false,
    optionsSuccessStatus: 204,
  });
};

export const requestIdMiddleware = (req: Request, res: Response, next: NextFunction): void => {
  const headerRequestId = req.header('X-Request-ID');
  req.requestId = headerRequestId && headerRequestId.length <= 128 ? headerRequestId : uuidv4();
  res.setHeader('X-Request-ID', req.requestId);
  next();
};

export const disablePoweredBy = (req: Request, res: Response, next: NextFunction): void => {
  res.removeHeader('X-Powered-By');
  next();
};

export const loginRateLimiter = rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 10,
  standardHeaders: true,
  legacyHeaders: false,
  skipSuccessfulRequests: false,
  keyGenerator: (req: Request): string => {
    return req.ip || 'unknown-ip';
  },
  handler: (req: Request, res: Response): void => {
    logger.warn('登录接口限流触发', {
      ip: req.ip,
      requestId: req.requestId,
    });
    res.status(429).json({
      success: false,
      message: '登录尝试过于频繁，请15分钟后再试',
      code: 'RATE_LIMIT_EXCEEDED',
    });
  },
});

export const paymentRateLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 30,
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req: Request): string => {
    const userId = (req.session && req.session.userId) || 'anonymous';
    return `${req.ip}:${userId}`;
  },
  handler: (req: Request, res: Response): void => {
    logger.warn('支付接口限流触发', {
      ip: req.ip,
      userId: req.session?.userId,
      requestId: req.requestId,
    });
    res.status(429).json({
      success: false,
      message: '支付请求过于频繁，请稍后再试',
      code: 'RATE_LIMIT_EXCEEDED',
    });
  },
});

export const createRedisClient = (): Redis => {
  return new Redis({
    host: config.redis.host,
    port: config.redis.port,
    password: config.redis.password,
    db: config.redis.db,
    maxRetriesPerRequest: null,
    enableReadyCheck: true,
    lazyConnect: true,
    retryStrategy: (times: number): number | null => {
      if (times > 10) {
        logger.error('Redis连接重试次数过多，停止重试');
        return null;
      }
      const delay = Math.min(times * 200, 3000);
      logger.warn(`Redis连接重试 ${times} 次，${delay}ms后重试`);
      return delay;
    },
  });
};

export const createSessionMiddleware = (redisClient: Redis): RequestHandler => {
  const redisStore = new RedisStore({
    client: redisClient,
    prefix: 'session:',
    ttl: config.session.ttl,
    disableTouch: false,
  });

  return session({
    store: redisStore,
    secret: config.session.secret,
    name: config.session.name,
    resave: false,
    saveUninitialized: false,
    rolling: true,
    cookie: {
      httpOnly: true,
      secure: isProduction,
      sameSite: 'lax',
      maxAge: config.session.ttl * 1000,
      path: '/',
      signed: true,
    },
    genid: (): string => {
      return crypto.randomBytes(32).toString('hex');
    },
  });
};

export interface SecurityMiddlewareOptions {
  redisClient?: Redis;
}

export const applySecurityMiddlewares = (
  redisClient?: Redis
): RequestHandler[] => {
  const client = redisClient || createRedisClient();
  return [
    disablePoweredBy,
    nonceMiddleware,
    helmetConfig(),
    corsConfig(),
    requestIdMiddleware,
    createSessionMiddleware(client),
  ];
};

export {
  loginRateLimiter as loginRateLimit,
  paymentRateLimiter as paymentRateLimit,
};

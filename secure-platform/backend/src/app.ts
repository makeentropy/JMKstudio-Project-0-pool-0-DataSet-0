import express, { Request, Response, NextFunction, Express, Router } from 'express';
import { ZodError } from 'zod';
import { config, isProduction } from './config';
import logger from './utils/logger';
import {
  helmetConfig,
  corsConfig,
  requestIdMiddleware,
  disablePoweredBy,
  nonceMiddleware,
  createRedisClient,
  createSessionMiddleware,
} from './middleware/security';
import { certificateRoutes } from './routes/certificate';
import { accessAuthRoutes } from './routes/access-auth';
import { accessAdminRoutes } from './routes/access-admin';
import { cryptoRoutes } from './routes/crypto';
import { paymentRoutes } from './routes/payment';
import { blockchainRoutes } from './routes/blockchain';
import { serveFrontend } from './routes/frontend';

export interface ApiErrorOptions {
  statusCode?: number;
  code?: string;
  details?: unknown;
}

export class ApiError extends Error {
  public readonly statusCode: number;
  public readonly code: string;
  public readonly details?: unknown;
  public readonly isOperational: boolean;

  constructor(message: string, options: ApiErrorOptions = {}) {
    super(message);
    this.name = 'ApiError';
    this.statusCode = options.statusCode ?? 500;
    this.code = options.code ?? 'INTERNAL_ERROR';
    this.details = options.details;
    this.isOperational = true;
    Error.captureStackTrace(this, this.constructor);
  }
}

export interface AppErrorResponse {
  success: false;
  message: string;
  code: string;
  requestId: string;
  details?: unknown;
  timestamp: string;
}

export const notFoundHandler = (req: Request, res: Response): void => {
  logger.warn('请求路由不存在', {
    method: req.method,
    path: req.originalUrl,
    ip: req.ip,
    requestId: req.requestId,
  });
  const response: AppErrorResponse = {
    success: false,
    message: `请求的资源不存在: ${req.method} ${req.originalUrl}`,
    code: 'NOT_FOUND',
    requestId: req.requestId,
    timestamp: new Date().toISOString(),
  };
  res.status(404).json(response);
};

export const errorHandler = (
  err: Error | ApiError | ZodError,
  req: Request,
  res: Response,
  _next: NextFunction
): void => {
  const requestId = req.requestId || 'unknown';

  if (err instanceof ApiError) {
    logger.warn('业务错误', {
      message: err.message,
      code: err.code,
      statusCode: err.statusCode,
      requestId,
      path: req.originalUrl,
      method: req.method,
      ip: req.ip,
    });

    const response: AppErrorResponse = {
      success: false,
      message: err.message,
      code: err.code,
      requestId,
      details: err.details,
      timestamp: new Date().toISOString(),
    };
    res.status(err.statusCode).json(response);
    return;
  }

  if (err instanceof ZodError) {
    logger.warn('输入验证错误', {
      issues: err.issues,
      requestId,
      path: req.originalUrl,
      method: req.method,
      ip: req.ip,
    });

    const details = err.issues.map((issue) => ({
      path: issue.path.join('.'),
      message: issue.message,
    }));

    const response: AppErrorResponse = {
      success: false,
      message: '输入验证失败',
      code: 'VALIDATION_ERROR',
      requestId,
      details,
      timestamp: new Date().toISOString(),
    };
    res.status(400).json(response);
    return;
  }

  logger.error('未处理的错误', {
    error: err.message,
    stack: isProduction ? undefined : err.stack,
    requestId,
    path: req.originalUrl,
    method: req.method,
    ip: req.ip,
    userId: req.session?.userId,
  });

  const publicMessage = isProduction
    ? '服务器内部错误，请稍后重试'
    : err.message || '服务器内部错误';

  const response: AppErrorResponse = {
    success: false,
    message: publicMessage,
    code: 'INTERNAL_SERVER_ERROR',
    requestId,
    timestamp: new Date().toISOString(),
    ...(isProduction ? {} : { details: { stack: err.stack } }),
  };
  res.status(500).json(response);
};

export interface CreateAppOptions {
  routes?: Router;
  redisClient?: ReturnType<typeof createRedisClient>;
}

export const createApp = (options: CreateAppOptions = {}): Express => {
  const app = express();
  const { routes, redisClient } = options;

  app.disable('x-powered-by');
  app.set('trust proxy', 1);
  app.set('etag', 'strong');

  app.use(disablePoweredBy);
  app.use(nonceMiddleware);
  app.use(helmetConfig());
  app.use(corsConfig());

  app.use(express.json({
    limit: '100kb',
    strict: true,
    type: ['application/json', 'application/*+json'],
  }));

  app.use(express.urlencoded({
    extended: false,
    limit: '100kb',
    parameterLimit: 100,
  }));

  app.use(express.text({
    limit: '100kb',
    type: 'text/plain',
  }));

  const client = redisClient || createRedisClient();
  app.use(createSessionMiddleware(client));

  app.use(requestIdMiddleware);

  app.use((req: Request, res: Response, next: NextFunction) => {
    const start = Date.now();
    logger.http('请求开始', {
      method: req.method,
      path: req.originalUrl,
      ip: req.ip,
      requestId: req.requestId,
      userAgent: req.get('User-Agent'),
      contentLength: req.get('Content-Length'),
    });

    res.on('finish', () => {
      const duration = Date.now() - start;
      logger.http('请求完成', {
        method: req.method,
        path: req.originalUrl,
        statusCode: res.statusCode,
        duration,
        requestId: req.requestId,
      });
    });

    next();
  });

  const healthRouter = Router();
  healthRouter.get('/health', (_req: Request, res: Response) => {
    res.json({
      success: true,
      data: {
        status: 'ok',
        service: config.app.name,
        timestamp: new Date().toISOString(),
        uptime: process.uptime(),
      },
    });
  });
  app.use('/', healthRouter);

  app.use('/api/certificate', certificateRoutes);
  app.use('/api/auth', accessAuthRoutes);
  app.use('/api/admin', accessAdminRoutes);
  app.use('/api/crypto', cryptoRoutes);
  app.use('/api/payment', paymentRoutes);
  app.use('/api/blockchain', blockchainRoutes);

  if (routes) {
    app.use(config.app.apiPrefix, routes);
  }

  serveFrontend(app);

  app.use(notFoundHandler);
  app.use(errorHandler);

  return app;
};

export default createApp;

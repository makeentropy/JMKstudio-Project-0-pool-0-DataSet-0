import { Request, Response, NextFunction, RequestHandler, CookieOptions } from 'express';
import jwt from 'jsonwebtoken';
import crypto from 'crypto';
import { UserManager, AccessController, Permission, hasPermission, PublicUser } from '../modules/access-control';
import { ApiError } from '../app';
import { config } from '../config';
import logger from '../utils/logger';

declare global {
  namespace Express {
    interface Request {
      currentUser?: PublicUser;
      csrfToken?: string;
    }
  }
}

declare module 'express-session' {
  interface SessionData {
    userId?: string;
    csrfToken?: string;
    lastActivity?: number;
  }
}

const CSRF_TOKEN_LENGTH = 32;
const CSRF_COOKIE_NAME = 'XSRF-TOKEN';
const CSRF_HEADER_NAME = 'X-CSRF-Token';

export const createSessionAuthMiddleware = (userManager: UserManager): RequestHandler => {
  return async (req: Request, _res: Response, next: NextFunction): Promise<void> => {
    try {
      const userId = req.session?.userId;
      if (!userId) {
        return next();
      }

      const user = userManager.validateSession(userId) || userManager.getUser(userId);
      if (user) {
        req.currentUser = user;
        if (req.session) {
          req.session.lastActivity = Date.now();
        }
      } else {
        if (req.session) {
          req.session.userId = undefined;
          req.session.csrfToken = undefined;
        }
      }

      next();
    } catch (cause) {
      logger.warn('会话验证异常', {
        error: cause instanceof Error ? cause.message : String(cause),
        ip: req.ip,
        requestId: req.requestId,
      });
      next();
    }
  };
};

export const sessionAuth: RequestHandler = (_req: Request, _res: Response, _next: NextFunction): void => {
  _next();
};

export const requireAuth: RequestHandler = (req: Request, _res: Response, next: NextFunction): void => {
  if (!req.currentUser) {
    return next(new ApiError('未登录或会话已过期', {
      statusCode: 401,
      code: 'UNAUTHENTICATED',
    }));
  }
  if (!req.currentUser.isActive) {
    return next(new ApiError('账户已停用', {
      statusCode: 403,
      code: 'ACCOUNT_DISABLED',
    }));
  }
  next();
};

export const requirePermission = (permission: Permission, accessController?: AccessController): RequestHandler => {
  return (req: Request, _res: Response, next: NextFunction): void => {
    if (!req.currentUser) {
      return next(new ApiError('未登录或会话已过期', {
        statusCode: 401,
        code: 'UNAUTHENTICATED',
      }));
    }

    let userPerms: Permission = req.currentUser.permissions;
    if (accessController) {
      userPerms = accessController.getUserEffectivePermissions(req.currentUser.id);
    }

    if (hasPermission(userPerms, Permission.SUPER_ADMIN)) {
      return next();
    }

    if (hasPermission(userPerms, permission)) {
      return next();
    }

    logger.warn('权限不足', {
      userId: req.currentUser.id,
      username: req.currentUser.username,
      requiredPermission: permission,
      userPermissions: userPerms,
      path: req.path,
      method: req.method,
      requestId: req.requestId,
    });

    return next(new ApiError('权限不足', {
      statusCode: 403,
      code: 'PERMISSION_DENIED',
    }));
  };
};

export const requireAdmin: RequestHandler = requirePermission(Permission.ADMIN);
export const requireSuperAdmin: RequestHandler = requirePermission(Permission.SUPER_ADMIN);

export const generateCsrfToken = (req: Request, res: Response): string => {
  let token = req.session?.csrfToken;
  if (!token) {
    token = crypto.randomBytes(CSRF_TOKEN_LENGTH).toString('hex');
    if (req.session) {
      req.session.csrfToken = token;
    }
  }

  req.csrfToken = token;

  const cookieOptions: CookieOptions = {
    httpOnly: false,
    secure: config.app.nodeEnv === 'production',
    sameSite: 'lax',
    path: '/',
  };

  res.cookie(CSRF_COOKIE_NAME, token, cookieOptions);
  return token;
};

export const csrfProtect: RequestHandler = (req: Request, _res: Response, next: NextFunction): void => {
  const stateChangingMethods = new Set(['POST', 'PUT', 'PATCH', 'DELETE']);
  if (!stateChangingMethods.has(req.method)) {
    return next();
  }

  const sessionToken = req.session?.csrfToken;
  const headerToken = req.header(CSRF_HEADER_NAME);
  const bodyToken = req.body?._csrf;
  const queryToken = req.query?._csrf as string | undefined;

  const submittedToken = headerToken || bodyToken || queryToken;

  if (!sessionToken || !submittedToken) {
    return next(new ApiError('CSRF令牌缺失', {
      statusCode: 403,
      code: 'CSRF_MISSING_TOKEN',
    }));
  }

  try {
    const sessionBuf = Buffer.from(sessionToken, 'hex');
    const submittedBuf = Buffer.from(submittedToken, 'hex');

    if (sessionBuf.length !== submittedBuf.length) {
      throw new Error('token length mismatch');
    }

    if (!crypto.timingSafeEqual(sessionBuf, submittedBuf)) {
      throw new Error('token mismatch');
    }

    next();
  } catch {
    logger.warn('CSRF验证失败', {
      ip: req.ip,
      method: req.method,
      path: req.path,
      requestId: req.requestId,
    });
    return next(new ApiError('CSRF令牌无效', {
      statusCode: 403,
      code: 'CSRF_INVALID_TOKEN',
    }));
  }
};

export interface JwtAuthOptions {
  secret?: string;
  issuer?: string;
  audience?: string;
  userManager?: UserManager;
}

export const createJwtAuthMiddleware = (options: JwtAuthOptions = {}): RequestHandler => {
  const secret = options.secret || config.jwt.secret;
  const issuer = options.issuer || config.jwt.issuer;
  const audience = options.audience || config.jwt.audience;
  const userManager = options.userManager;

  return (req: Request, _res: Response, next: NextFunction): void => {
    const authHeader = req.header('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return next();
    }

    const token = authHeader.slice(7).trim();
    if (!token) {
      return next();
    }

    try {
      const decoded = jwt.verify(token, secret, {
        issuer,
        audience,
        algorithms: ['HS256'],
      }) as { sub?: string; exp?: number };

      if (decoded.sub) {
        if (userManager) {
          const user = userManager.getUser(decoded.sub);
          if (user && user.isActive) {
            req.currentUser = user;
          }
        } else {
          req.currentUser = {
            id: decoded.sub,
            username: 'jwt-user',
            email: decoded.sub,
            roles: [],
            permissions: Permission.NONE,
            isActive: true,
            isLocked: false,
            createdAt: new Date(),
          };
        }
      }

      next();
    } catch (cause) {
      logger.warn('JWT验证失败', {
        error: cause instanceof Error ? cause.message : String(cause),
        ip: req.ip,
        requestId: req.requestId,
      });
      next(new ApiError('JWT令牌无效', {
        statusCode: 401,
        code: 'INVALID_JWT',
        details: cause instanceof Error ? cause.message : undefined,
      }));
    }
  };
};

export const jwtAuth: RequestHandler = createJwtAuthMiddleware();

export interface CombinedAuthOptions {
  userManager?: UserManager;
  accessController?: AccessController;
  allowJwt?: boolean;
  allowSession?: boolean;
}

export const createCombinedAuth = (options: CombinedAuthOptions = {}): RequestHandler[] => {
  const middlewares: RequestHandler[] = [];

  if (options.allowSession !== false) {
    middlewares.push(createSessionAuthMiddleware(options.userManager || new UserManager()));
  }
  if (options.allowJwt !== false) {
    middlewares.push(createJwtAuthMiddleware({ userManager: options.userManager }));
  }

  return middlewares;
};

export const extractCurrentUserId = (req: Request): string | null => {
  return req.currentUser?.id ?? null;
};

export const requireOwnershipOrPermission = (
  getResourceOwnerId: (req: Request) => string | undefined | null,
  permission: Permission,
  accessController?: AccessController
): RequestHandler => {
  return (req: Request, _res: Response, next: NextFunction): void => {
    if (!req.currentUser) {
      return next(new ApiError('未登录或会话已过期', {
        statusCode: 401,
        code: 'UNAUTHENTICATED',
      }));
    }

    const ownerId = getResourceOwnerId(req);
    if (ownerId && ownerId === req.currentUser.id) {
      return next();
    }

    let userPerms: Permission = req.currentUser.permissions;
    if (accessController) {
      userPerms = accessController.getUserEffectivePermissions(req.currentUser.id);
    }

    if (hasPermission(userPerms, Permission.SUPER_ADMIN) || hasPermission(userPerms, permission)) {
      return next();
    }

    return next(new ApiError('权限不足', {
      statusCode: 403,
      code: 'PERMISSION_DENIED',
    }));
  };
};

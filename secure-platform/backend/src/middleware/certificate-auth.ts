import { Request, Response, NextFunction, RequestHandler } from 'express';
import { CertificateVerifier, CertificateInfo, CertificateValidationError } from '../modules/certificate';
import { ApiError } from '../app';
import logger from '../utils/logger';

declare global {
  namespace Express {
    interface Request {
      certificateInfo?: CertificateInfo;
    }
  }
}

export interface CertificateAuthOptions {
  verifier: CertificateVerifier;
  requireChain?: boolean;
  headerName?: string;
}

const decodeHeaderCert = (encoded: string): string => {
  const urlUnescaped = decodeURIComponent(encoded);
  try {
    return Buffer.from(urlUnescaped, 'base64').toString('utf8');
  } catch {
    return urlUnescaped;
  }
};

export const certificateAuth = (options: CertificateAuthOptions): RequestHandler => {
  const { verifier, requireChain = false, headerName = 'X-Client-Certificate' } = options;

  return (req: Request, _res: Response, next: NextFunction): void => {
    const headerValue = req.header(headerName);
    if (!headerValue) {
      return next();
    }

    try {
      const pemData = decodeHeaderCert(headerValue);
      const [valid, reason] = verifier.verifyChain(pemData);

      if (!valid && requireChain) {
        logger.warn('客户端证书链验证失败', {
          reason,
          ip: req.ip,
          requestId: req.requestId,
        });
        throw new CertificateValidationError(reason);
      }

      const validityCheck = verifier.checkValidity(pemData);
      if (!validityCheck.valid) {
        logger.warn('客户端证书有效性检查失败', {
          reason: validityCheck.reason,
          ip: req.ip,
          requestId: req.requestId,
        });
        throw new CertificateValidationError(validityCheck.reason || '证书无效');
      }

      req.certificateInfo = verifier.getCertificateInfo(pemData);
      logger.info('客户端证书验证成功', {
        subject: req.certificateInfo.subject,
        serial: req.certificateInfo.serialNumber,
        ip: req.ip,
        requestId: req.requestId,
      });

      next();
    } catch (cause) {
      if (requireChain) {
        if (cause instanceof CertificateValidationError) {
          return next(new ApiError(cause.message, {
            statusCode: 401,
            code: 'INVALID_CLIENT_CERTIFICATE',
            details: cause.code,
          }));
        }
        return next(new ApiError('客户端证书解析失败', {
          statusCode: 401,
          code: 'INVALID_CLIENT_CERTIFICATE',
          details: cause instanceof Error ? cause.message : String(cause),
        }));
      }
      next();
    }
  };
};

export const requireCertificate: RequestHandler = (req: Request, _res: Response, next: NextFunction): void => {
  if (!req.certificateInfo) {
    return next(new ApiError('需要有效的客户端证书', {
      statusCode: 401,
      code: 'CLIENT_CERTIFICATE_REQUIRED',
    }));
  }
  next();
};

export const getClientCertificateFromHeader = (req: Request, headerName: string = 'X-Client-Certificate'): string | null => {
  const headerValue = req.header(headerName);
  if (!headerValue) return null;
  return decodeHeaderCert(headerValue);
};

export const createCertificateAuthMiddleware = (
  verifier: CertificateVerifier,
  required: boolean = true
): RequestHandler[] => {
  return [
    certificateAuth({ verifier, requireChain: required }),
    ...(required ? [requireCertificate] : []),
  ];
};

import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import {
  CertificateAuthority,
  CertificateVerifier,
  CertificateType,
  CertificateStatus,
  RevocationReason,
  CertificateInfo,
  createDefaultCA,
} from '../modules/certificate';
import { Permission } from '../modules/access-control';
import { requireAuth, requirePermission, generateCsrfToken } from '../middleware/auth';
import { ApiError } from '../app';
import logger from '../utils/logger';

export interface CertificateRouterOptions {
  ca: CertificateAuthority;
  verifier: CertificateVerifier;
}

const generateSchema = z.object({
  subjectName: z.string().min(1).max(255),
  certificateType: z.nativeEnum(CertificateType),
  validityDays: z.coerce.number().int().min(1).max(3650).default(365),
  sanDns: z.array(z.string()).optional().default([]),
  sanIps: z.array(z.string().ip()).optional().default([]),
  alias: z.string().min(1).max(255).optional(),
});

const signSchema = z.object({
  csrPem: z.string().min(1),
  certificateType: z.nativeEnum(CertificateType),
  validityDays: z.coerce.number().int().min(1).max(3650).default(365),
  subjectName: z.string().min(1).max(255).optional(),
  sanDns: z.array(z.string()).optional().default([]),
  sanIps: z.array(z.string().ip()).optional().default([]),
});

const verifySchema = z.object({
  certificatePem: z.string().min(1),
  intermediateCerts: z.array(z.string()).optional(),
  checkRevocation: z.boolean().default(true),
});

const revokeSchema = z.object({
  serialNumber: z.string().min(1),
  reason: z.nativeEnum(RevocationReason).default(RevocationReason.UNSPECIFIED),
});

const listSchema = z.object({
  status: z.nativeEnum(CertificateStatus).optional(),
  certificateType: z.nativeEnum(CertificateType).optional(),
});

const issueClientSchema = z.object({
  commonName: z.string().min(1).max(255).optional(),
  validityDays: z.coerce.number().int().min(1).max(3650).default(365),
  sanDns: z.array(z.string()).optional().default([]),
});

const certificateInfoToResponse = (info: CertificateInfo, includePem: boolean = false) => ({
  serialNumber: info.serialNumber,
  subject: info.subject,
  issuer: info.issuer,
  notBefore: info.notBefore.toISOString(),
  notAfter: info.notAfter.toISOString(),
  certificateType: info.certificateType,
  publicKeyFingerprint: info.publicKeyFingerprint,
  status: info.status,
  revocationReason: info.revocationReason,
  revocationDate: info.revocationDate?.toISOString(),
  ...(includePem && info.pemData ? { pemData: info.pemData } : {}),
});

export const createCertificateRouter = (options: CertificateRouterOptions): Router => {
  const router = Router();
  const { ca, verifier } = options;

  router.get('/ca', (_req: Request, res: Response, next: NextFunction) => {
    try {
      if (!ca.isInitialized) {
        throw new ApiError('CA尚未初始化', { statusCode: 404, code: 'CA_NOT_INITIALIZED' });
      }
      const certBuf = ca.exportCaCertificate(true);
      res.setHeader('Content-Type', 'application/x-x509-ca-cert');
      res.setHeader('Content-Disposition', 'attachment; filename="ca-certificate.pem"');
      res.send(certBuf);
    } catch (err) {
      next(err);
    }
  });

  router.get('/ca/info', (_req: Request, res: Response, next: NextFunction) => {
    try {
      const info = ca.getCaInfo();
      if (!info) {
        throw new ApiError('CA尚未初始化', { statusCode: 404, code: 'CA_NOT_INITIALIZED' });
      }
      res.json({
        success: true,
        data: certificateInfoToResponse(info),
      });
    } catch (err) {
      next(err);
    }
  });

  router.post('/verify', (req: Request, res: Response, next: NextFunction) => {
    try {
      const body = verifySchema.parse(req.body);

      let valid: boolean;
      let reason: string;

      try {
        [valid, reason] = verifier.verifyChain(body.certificatePem, body.intermediateCerts || []);
      } catch (cause) {
        valid = false;
        reason = cause instanceof Error ? cause.message : String(cause);
      }

      const caValid = ca.verifyCertificate(body.certificatePem, body.checkRevocation);
      const combinedValid = valid && caValid[0];
      const combinedReason = !valid ? reason : (!caValid[0] ? caValid[1] : '证书验证通过');

      let info: ReturnType<typeof certificateInfoToResponse> | undefined;
      try {
        const certInfo = verifier.getCertificateInfo(body.certificatePem);
        info = certificateInfoToResponse(certInfo);
      } catch {
        // ignore
      }

      res.json({
        success: true,
        data: {
          valid: combinedValid,
          reason: combinedReason,
          chainValid: valid,
          chainReason: reason,
          caValid: caValid[0],
          caReason: caValid[1],
          info,
        },
      });
    } catch (err) {
      next(err);
    }
  });

  router.use(requireAuth);
  router.use(requirePermission(Permission.ADMIN));

  router.post('/generate', (req: Request, res: Response, next: NextFunction) => {
    try {
      const body = generateSchema.parse(req.body);

      if (!ca.isInitialized) {
        throw new ApiError('CA尚未初始化', { statusCode: 500, code: 'CA_NOT_INITIALIZED' });
      }

      const result = ca.issueCertificate(
        body.subjectName,
        body.certificateType,
        body.validityDays,
        body.sanDns,
        body.sanIps
      );

      logger.info('证书生成成功', {
        serialNumber: result.info.serialNumber,
        subject: result.info.subject,
        type: body.certificateType,
        userId: req.currentUser?.id,
        requestId: req.requestId,
      });

      generateCsrfToken(req, res);

      res.json({
        success: true,
        data: {
          certificatePem: result.certificatePem,
          privateKeyPem: result.privateKeyPem,
          info: certificateInfoToResponse(result.info, true),
        },
      });
    } catch (err) {
      next(err);
    }
  });

  router.post('/sign', (req: Request, res: Response, next: NextFunction) => {
    try {
      signSchema.parse(req.body);

      if (!ca.isInitialized) {
        throw new ApiError('CA尚未初始化', { statusCode: 500, code: 'CA_NOT_INITIALIZED' });
      }

      res.status(501).json({
        success: false,
        message: 'CSR签名功能暂未实现',
        code: 'NOT_IMPLEMENTED',
      });
    } catch (err) {
      next(err);
    }
  });

  router.get('/list', (req: Request, res: Response, next: NextFunction) => {
    try {
      const query = listSchema.parse(req.query);
      const list = ca.listCertificates(query.status, query.certificateType);

      generateCsrfToken(req, res);

      res.json({
        success: true,
        data: {
          certificates: list.map(info => certificateInfoToResponse(info)),
          total: list.length,
        },
      });
    } catch (err) {
      next(err);
    }
  });

  router.post('/revoke', (req: Request, res: Response, next: NextFunction) => {
    try {
      const body = revokeSchema.parse(req.body);
      ca.revokeCertificate(body.serialNumber, body.reason);

      logger.warn('证书已吊销', {
        serialNumber: body.serialNumber,
        reason: body.reason,
        userId: req.currentUser?.id,
        requestId: req.requestId,
      });

      generateCsrfToken(req, res);

      res.json({
        success: true,
        data: {
          serialNumber: body.serialNumber,
          revoked: true,
        },
      });
    } catch (err) {
      next(err);
    }
  });

  router.get('/revocation-list', (_req: Request, res: Response, next: NextFunction) => {
    try {
      const list = ca.getRevocationList();
      res.json({
        success: true,
        data: {
          revokedCertificates: list.map(r => ({
            serialNumber: r.serialNumber,
            reason: r.reason,
            date: r.date.toISOString(),
          })),
          total: list.length,
        },
      });
    } catch (err) {
      next(err);
    }
  });

  router.post('/issue-client', (req: Request, res: Response, next: NextFunction) => {
    try {
      const body = issueClientSchema.parse(req.body);

      if (!ca.isInitialized) {
        throw new ApiError('CA尚未初始化', { statusCode: 500, code: 'CA_NOT_INITIALIZED' });
      }

      const user = req.currentUser!;
      const commonName = body.commonName || `${user.username}-client-cert`;

      const result = ca.issueCertificate(
        commonName,
        CertificateType.CLIENT,
        body.validityDays,
        body.sanDns,
        []
      );

      logger.info('客户端证书签发成功', {
        serialNumber: result.info.serialNumber,
        userId: user.id,
        username: user.username,
        requestId: req.requestId,
      });

      generateCsrfToken(req, res);

      res.json({
        success: true,
        data: {
          certificatePem: result.certificatePem,
          privateKeyPem: result.privateKeyPem,
          info: certificateInfoToResponse(result.info, true),
        },
      });
    } catch (err) {
      next(err);
    }
  });

  router.get('/:serialNumber', (req: Request, res: Response, next: NextFunction) => {
    try {
      const { serialNumber } = req.params;
      const info = ca.getCertificateInfo(serialNumber);

      if (!info) {
        throw new ApiError(`证书不存在: ${serialNumber}`, { statusCode: 404, code: 'CERTIFICATE_NOT_FOUND' });
      }

      generateCsrfToken(req, res);

      res.json({
        success: true,
        data: certificateInfoToResponse(info, true),
      });
    } catch (err) {
      next(err);
    }
  });

  return router;
};

export const certificateRoutes = (() => {
  try {
    const defaultCA = createDefaultCA();
    const defaultVerifier = new CertificateVerifier();
    return createCertificateRouter({ ca: defaultCA, verifier: defaultVerifier });
  } catch {
    return Router();
  }
})();
export default certificateRoutes;

import { Router, Request, Response, NextFunction } from 'express';
import { z } from 'zod';
import rateLimit from 'express-rate-limit';
import { config } from '../config';
import { ApiError } from '../app';
import logger from '../utils/logger';
import {
  PaymentController,
  PaymentMethod,
  PaymentProduct,
  PaymentStatus,
} from '../modules/payment';

const router = Router();

const paymentController = new PaymentController(config.alipay);

const requireAuth = (req: Request, _res: Response, next: NextFunction): void => {
  const userId = req.session?.userId;
  if (!userId) {
    return next(new ApiError('未登录或登录已过期', { statusCode: 401, code: 'UNAUTHORIZED' }));
  }
  next();
};

const requirePermission = (role: string) => (req: Request, _res: Response, next: NextFunction): void => {
  const userId = req.session?.userId;
  if (!userId) {
    return next(new ApiError('未登录或登录已过期', { statusCode: 401, code: 'UNAUTHORIZED' }));
  }
  if (role === 'ADMIN') {
    const isAdmin = (req.session as unknown as { role?: string })?.role === 'ADMIN';
    if (!isAdmin) {
      const adminEnv = process.env.ADMIN_USER_IDS?.split(',') || [];
      if (!adminEnv.includes(userId)) {
        return next(new ApiError('需要管理员权限', { statusCode: 403, code: 'FORBIDDEN' }));
      }
    }
  }
  next();
};

const paymentLimiter = rateLimit({
  windowMs: 60 * 1000,
  max: 30,
  standardHeaders: true,
  legacyHeaders: false,
  keyGenerator: (req: Request): string => {
    const userId = (req.session && req.session.userId) || 'anonymous';
    return `${req.ip}:${userId}`;
  },
  handler: (_req: Request, res: Response): void => {
    res.status(429).json({
      success: false,
      message: '支付请求过于频繁，请稍后再试',
      code: 'RATE_LIMIT_EXCEEDED',
    });
  },
});

router.use(paymentLimiter);

const createOrderSchema = z.object({
  method: z.nativeEnum(PaymentMethod),
  product: z.nativeEnum(PaymentProduct),
  amount: z.number().positive().lte(1000000),
  subject: z.string().min(1).max(256).optional(),
  idempotencyKey: z.string().max(128).optional(),
  metadata: z.record(z.unknown()).optional(),
});

router.post('/create', requireAuth, (req: Request, res: Response, next: NextFunction): void => {
  try {
    const userId = req.session!.userId!;
    const parsed = createOrderSchema.parse(req.body);

    const result = paymentController.createOrder({
      userId,
      ...parsed,
    });

    res.json({
      success: true,
      data: {
        order: result.order,
        paymentOptions: result.paymentOptions,
      },
    });
  } catch (error) {
    next(error);
  }
});

const alipayPagePaySchema = z.object({
  orderId: z.string().min(1),
  returnUrl: z.string().url().optional(),
  notifyUrl: z.string().url().optional(),
});

router.post('/alipay/page', requireAuth, async (req: Request, res: Response, next: NextFunction): Promise<void> => {
  try {
    const userId = req.session!.userId!;
    const parsed = alipayPagePaySchema.parse(req.body);

    const returnUrl = parsed.returnUrl || config.alipay.returnUrl;
    const notifyUrl = parsed.notifyUrl || config.alipay.notifyUrl;

    const result = await paymentController.alipayPagePay(
      parsed.orderId,
      userId,
      returnUrl,
      notifyUrl
    );

    res.json({
      success: true,
      data: {
        orderId: result.orderId,
        htmlForm: result.htmlForm,
      },
    });
  } catch (error) {
    next(error);
  }
});

router.post(
  '/alipay/notify',
  expressRaw(),
  async (req: Request, res: Response, next: NextFunction): Promise<void> => {
    try {
      const params: Record<string, string | undefined> = {};

      if (req.body && typeof req.body === 'object') {
        for (const [key, value] of Object.entries(req.body)) {
          params[key] = typeof value === 'string' ? value : String(value ?? '');
        }
      }

      logger.info('收到支付宝异步通知', {
        outTradeNo: params.out_trade_no,
        tradeStatus: params.trade_status,
        tradeNo: params.trade_no,
      });

      const result = await paymentController.handleAlipayNotify(params);
      res.type('text/plain');
      res.send(result);
    } catch (error) {
      logger.error('支付宝异步通知处理异常', {
        error: error instanceof Error ? error.message : String(error),
      });
      res.type('text/plain');
      res.status(500).send('fail');
    }
  }
);

const alipayReturnSchema = z.object({
  out_trade_no: z.string().min(1).optional(),
  trade_no: z.string().optional(),
  sign: z.string().optional(),
});

router.get('/alipay/return', async (req: Request, res: Response, next: NextFunction): Promise<void> => {
  try {
    const parsed = alipayReturnSchema.parse(req.query);
    const params: Record<string, string | undefined> = {};
    for (const [key, value] of Object.entries(parsed)) {
      params[key] = value as string | undefined;
    }

    const order = await paymentController.handleAlipayReturn(params);

    res.json({
      success: true,
      data: {
        orderId: order.id,
        status: order.status,
        amount: order.amount,
        isSuccess: order.status === PaymentStatus.SUCCESS,
      },
    });
  } catch (error) {
    next(error);
  }
});

const redeemCardSchema = z.object({
  cardNumber: z.string().min(1).max(64),
  cardPassword: z.string().min(1).max(32),
});

router.post('/card/redeem', requireAuth, async (req: Request, res: Response, next: NextFunction): Promise<void> => {
  try {
    const userId = req.session!.userId!;
    const parsed = redeemCardSchema.parse(req.body);

    const result = await paymentController.redeemCard(
      parsed.cardNumber,
      parsed.cardPassword,
      userId
    );

    res.json({
      success: true,
      data: {
        success: result.success,
        message: result.message,
        newBalance: result.newBalance,
      },
    });
  } catch (error) {
    next(error);
  }
});

const generateCardsSchema = z.object({
  denomination: z.number().positive().lte(100000),
  count: z.number().int().positive().lte(1000),
  prefix: z.string().max(16).optional(),
});

router.post(
  '/card/generate',
  requirePermission('ADMIN'),
  (req: Request, res: Response, next: NextFunction): void => {
    try {
      const parsed = generateCardsSchema.parse(req.body);
      const cards = paymentController.generateCards(
        parsed.denomination,
        parsed.count,
        parsed.prefix
      );

      res.json({
        success: true,
        data: {
          count: cards.length,
          cards,
        },
      });
    } catch (error) {
      next(error);
    }
  }
);

router.get('/balance', requireAuth, (req: Request, res: Response, next: NextFunction): void => {
  try {
    const userId = req.session!.userId!;
    const balance = paymentController.getBalance(userId);

    res.json({
      success: true,
      data: {
        balance,
        currency: 'CNY',
      },
    });
  } catch (error) {
    next(error);
  }
});

const listOrdersSchema = z.object({
  limit: z.coerce.number().int().positive().lte(200).optional(),
  offset: z.coerce.number().int().nonnegative().optional(),
});

router.get('/orders', requireAuth, (req: Request, res: Response, next: NextFunction): void => {
  try {
    const userId = req.session!.userId!;
    const parsed = listOrdersSchema.parse(req.query);
    const orders = paymentController.listOrders(userId, parsed.limit, parsed.offset);

    res.json({
      success: true,
      data: {
        count: orders.length,
        orders,
      },
    });
  } catch (error) {
    next(error);
  }
});

router.get('/orders/:id', requireAuth, (req: Request, res: Response, next: NextFunction): void => {
  try {
    const userId = req.session!.userId!;
    const { id } = z.object({ id: z.string().min(1) }).parse(req.params);
    const order = paymentController.getOrder(id, userId);

    res.json({
      success: true,
      data: { order },
    });
  } catch (error) {
    next(error);
  }
});

const refundOrderSchema = z.object({
  refundAmount: z.number().positive().optional(),
  reason: z.string().max(500).optional(),
});

router.post('/orders/:id/refund', requireAuth, async (req: Request, res: Response, next: NextFunction): Promise<void> => {
  try {
    const userId = req.session!.userId!;
    const { id } = z.object({ id: z.string().min(1) }).parse(req.params);
    const parsed = refundOrderSchema.parse(req.body);

    const refund = await paymentController.refundOrder(
      id,
      userId,
      parsed.refundAmount,
      parsed.reason
    );

    res.json({
      success: true,
      data: { refund },
    });
  } catch (error) {
    next(error);
  }
});

function expressRaw() {
  return (req: Request, _res: Response, next: NextFunction): void => {
    if (req.headers['content-type'] === 'application/x-www-form-urlencoded') {
      return next();
    }
    if (typeof req.body === 'string') {
      return next();
    }
    let data = '';
    req.setEncoding('utf8');
    req.on('data', (chunk: string) => {
      data += chunk;
    });
    req.on('end', () => {
      if (data) {
        try {
          const parsed = new URLSearchParams(data);
          const obj: Record<string, string> = {};
          parsed.forEach((value, key) => {
            obj[key] = value;
          });
          req.body = obj;
        } catch {
          req.body = {};
        }
      }
      next();
    });
  };
}

export default router;
export { router as paymentRoutes, paymentController };

import { v4 as uuidv4 } from 'uuid';
import type { AlipayConfig } from '../../config';
import { ApiError } from '../../app';
import logger from '../../utils/logger';
import {
  Order,
  Refund,
  RechargeCard,
  Transaction,
  PaymentStatus,
  PaymentMethod,
  PaymentProduct,
} from './types';
import { AlipayPayment } from './alipay';
import { CardRechargeSystem } from './card-recharge';
import { OrderManager } from './orders';

export interface CreateOrderParams {
  userId: string;
  method: PaymentMethod;
  product: PaymentProduct;
  amount: number;
  subject?: string;
  idempotencyKey?: string;
  metadata?: Record<string, unknown>;
}

export interface CreateOrderResult {
  order: Order;
  paymentOptions: PaymentMethod[];
}

export interface AlipayPagePayResult {
  orderId: string;
  htmlForm: string;
}

export interface RedeemCardResult {
  success: boolean;
  message: string;
  transaction?: Transaction;
  newBalance: number;
}

export class PaymentController {
  private alipay: AlipayPayment;
  private cardSystem: CardRechargeSystem;
  private orderManager: OrderManager;

  constructor(alipayConfig: AlipayConfig) {
    this.alipay = new AlipayPayment(alipayConfig);
    this.cardSystem = new CardRechargeSystem();
    this.orderManager = new OrderManager();
  }

  getOrderManager(): OrderManager {
    return this.orderManager;
  }

  getCardSystem(): CardRechargeSystem {
    return this.cardSystem;
  }

  getAlipay(): AlipayPayment {
    return this.alipay;
  }

  createOrder(params: CreateOrderParams): CreateOrderResult {
    const { userId, method, product, amount, subject, idempotencyKey, metadata } = params;

    if (idempotencyKey) {
      const idempotency = this.orderManager.ensureIdempotency(idempotencyKey);
      if (idempotency.exists && idempotency.orderId) {
        const existingOrder = this.orderManager.getOrderById(idempotency.orderId);
        if (existingOrder) {
          return {
            order: existingOrder,
            paymentOptions: this.getAvailablePaymentMethods(existingOrder.amount),
          };
        }
      }
    }

    const order = this.orderManager.createOrder(
      userId,
      method,
      product,
      amount,
      {
        ...metadata,
        subject: subject || metadata?.subject || `订单支付 ¥${amount.toFixed(2)}`,
      }
    );

    if (idempotencyKey) {
      this.orderManager.registerIdempotency(idempotencyKey, order.id);
    }

    return {
      order,
      paymentOptions: this.getAvailablePaymentMethods(amount),
    };
  }

  private getAvailablePaymentMethods(amount: number): PaymentMethod[] {
    const methods: PaymentMethod[] = [];
    if (amount >= 0.01) {
      methods.push(PaymentMethod.ALIPAY);
      methods.push(PaymentMethod.CARD);
    }
    return methods;
  }

  async alipayPagePay(
    orderId: string,
    userId: string,
    returnUrl: string,
    notifyUrl: string
  ): Promise<AlipayPagePayResult> {
    const order = this.orderManager.getOrderById(orderId);
    if (!order) {
      throw new ApiError('订单不存在', { statusCode: 404, code: 'ORDER_NOT_FOUND' });
    }

    if (order.userId !== userId) {
      throw new ApiError('无权访问此订单', { statusCode: 403, code: 'FORBIDDEN' });
    }

    if (order.status !== PaymentStatus.PENDING) {
      throw new ApiError(`订单状态不允许支付: ${order.status}`, { statusCode: 400, code: 'INVALID_ORDER_STATUS' });
    }

    const htmlForm = this.alipay.pagePay(
      order.outTradeNo,
      order.amount,
      order.subject,
      returnUrl,
      notifyUrl
    );

    logger.info('支付宝电脑网站支付表单生成', { orderId, outTradeNo: order.outTradeNo, userId });

    return {
      orderId: order.id,
      htmlForm,
    };
  }

  async handleAlipayNotify(params: Record<string, string | undefined>): Promise<string> {
    const [verified, orderData] = await this.alipay.verifyNotify(params);
    if (!verified) {
      logger.warn('支付宝异步通知验签失败');
      return 'fail';
    }

    const outTradeNo = params.out_trade_no;
    if (!outTradeNo) {
      return 'fail';
    }

    const tradeStatus = params.trade_status;
    const tradeNo = params.trade_no;

    const existingOrder = this.orderManager.getOrderByOutTradeNo(outTradeNo);
    if (!existingOrder) {
      logger.warn('支付宝异步通知订单不存在', { outTradeNo });
      return 'success';
    }

    const isSuccess = tradeStatus === 'TRADE_SUCCESS' || tradeStatus === 'TRADE_FINISHED';
    const isClosed = tradeStatus === 'TRADE_CLOSED';

    let targetStatus: PaymentStatus | null = null;
    if (isSuccess) {
      targetStatus = PaymentStatus.SUCCESS;
    } else if (isClosed) {
      targetStatus = PaymentStatus.CLOSED;
    }

    if (targetStatus && existingOrder.status === PaymentStatus.PENDING) {
      try {
        this.orderManager.updateOrderStatus(existingOrder.id, targetStatus, {
          tradeNo,
          paidAt: isSuccess ? new Date() : undefined,
          metadata: { alipayNotifyParams: params },
        });

        if (targetStatus === PaymentStatus.SUCCESS) {
          logger.info('支付宝异步通知支付成功', { orderId: existingOrder.id, outTradeNo, tradeNo });
        }
      } catch (error) {
        logger.error('支付宝异步通知更新订单失败', {
          error: error instanceof Error ? error.message : String(error),
          outTradeNo,
        });
      }
    }

    return 'success';
  }

  async handleAlipayReturn(params: Record<string, string | undefined>): Promise<Order> {
    const outTradeNo = params.out_trade_no;
    if (!outTradeNo) {
      throw new ApiError('缺少订单号参数', { statusCode: 400, code: 'INVALID_PARAM' });
    }

    const existingOrder = this.orderManager.getOrderByOutTradeNo(outTradeNo);
    if (!existingOrder) {
      throw new ApiError('订单不存在', { statusCode: 404, code: 'ORDER_NOT_FOUND' });
    }

    if (existingOrder.status === PaymentStatus.PENDING) {
      const queryResult = await this.alipay.queryOrder(outTradeNo, params.trade_no);
      if (queryResult.status === PaymentStatus.SUCCESS) {
        return this.orderManager.updateOrderStatus(existingOrder.id, PaymentStatus.SUCCESS, {
          tradeNo: params.trade_no,
          paidAt: new Date(),
        });
      }
    }

    return existingOrder;
  }

  async redeemCard(cardNumber: string, cardPassword: string, userId: string): Promise<RedeemCardResult> {
    const [success, message] = await this.cardSystem.redeemCard(cardNumber, cardPassword, userId);
    return {
      success,
      message,
      newBalance: this.cardSystem.getBalance(userId),
    };
  }

  generateCards(denomination: number, count: number, prefix?: string): RechargeCard[] {
    return this.cardSystem.generateCards(denomination, count, prefix);
  }

  getBalance(userId: string): number {
    return this.cardSystem.getBalance(userId);
  }

  listTransactions(userId: string, limit?: number, offset?: number): Transaction[] {
    return this.cardSystem.listTransactions(userId, limit, offset);
  }

  getOrder(orderId: string, userId: string): Order {
    const order = this.orderManager.getOrderById(orderId);
    if (!order) {
      throw new ApiError('订单不存在', { statusCode: 404, code: 'ORDER_NOT_FOUND' });
    }
    if (order.userId !== userId) {
      throw new ApiError('无权访问此订单', { statusCode: 403, code: 'FORBIDDEN' });
    }
    return order;
  }

  listOrders(userId: string, limit?: number, offset?: number): Order[] {
    return this.orderManager.listOrdersByUser(userId, limit, offset);
  }

  async refundOrder(orderId: string, userId: string, refundAmount?: number, reason?: string): Promise<Refund> {
    const order = this.orderManager.getOrderById(orderId);
    if (!order) {
      throw new ApiError('订单不存在', { statusCode: 404, code: 'ORDER_NOT_FOUND' });
    }
    if (order.userId !== userId) {
      throw new ApiError('无权操作此订单', { statusCode: 403, code: 'FORBIDDEN' });
    }
    if (order.status !== PaymentStatus.SUCCESS) {
      throw new ApiError(`订单状态不允许退款: ${order.status}`, { statusCode: 400, code: 'INVALID_ORDER_STATUS' });
    }

    const actualRefundAmount = refundAmount ?? order.amount;
    if (actualRefundAmount > order.amount) {
      throw new ApiError('退款金额不能超过订单金额', { statusCode: 400, code: 'INVALID_REFUND_AMOUNT' });
    }
    if (actualRefundAmount <= 0) {
      throw new ApiError('退款金额必须大于0', { statusCode: 400, code: 'INVALID_REFUND_AMOUNT' });
    }

    const outRequestNo = `RF${Date.now()}${uuidv4().substring(0, 8).toUpperCase()}`;
    let refundResult: Refund;

    if (order.method === PaymentMethod.ALIPAY) {
      refundResult = await this.alipay.refund(
        order.outTradeNo,
        actualRefundAmount,
        outRequestNo,
        reason
      );
    } else {
      throw new ApiError(`不支持的退款方式: ${order.method}`, { statusCode: 400, code: 'UNSUPPORTED_METHOD' });
    }

    refundResult.orderId = order.id;
    this.orderManager.updateOrderStatus(order.id, PaymentStatus.REFUNDED, {
      metadata: { refund: refundResult },
    });

    logger.info('订单退款成功', { orderId, refundAmount: actualRefundAmount, outRequestNo });
    return refundResult;
  }
}

export default PaymentController;

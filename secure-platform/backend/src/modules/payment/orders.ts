import { v4 as uuidv4 } from 'uuid';
import { ApiError } from '../../app';
import logger from '../../utils/logger';
import {
  Order,
  PaymentStatus,
  PaymentMethod,
  PaymentProduct,
} from './types';

export class OrderManager {
  private orders: Map<string, Order> = new Map();
  private idempotencyKeys: Map<string, string> = new Map();
  private userOrdersIndex: Map<string, string[]> = new Map();
  private outTradeNoIndex: Map<string, string> = new Map();

  private generateOutTradeNo(): string {
    const timestamp = Date.now().toString();
    const random = uuidv4().replace(/-/g, '').substring(0, 16).toUpperCase();
    return `SP${timestamp}${random}`;
  }

  createOrder(
    userId: string,
    method: PaymentMethod,
    product: PaymentProduct,
    amount: number,
    metadata?: Record<string, unknown>
  ): Order {
    if (!userId) {
      throw new ApiError('用户ID不能为空', { statusCode: 400, code: 'INVALID_USER' });
    }
    if (amount <= 0) {
      throw new ApiError('订单金额必须大于0', { statusCode: 400, code: 'INVALID_AMOUNT' });
    }

    const now = new Date();
    const order: Order = {
      id: uuidv4(),
      userId,
      method,
      product,
      amount,
      currency: 'CNY',
      status: PaymentStatus.PENDING,
      outTradeNo: this.generateOutTradeNo(),
      subject: metadata?.subject as string || '订单支付',
      metadata,
      createdAt: now,
      updatedAt: now,
    };

    this.orders.set(order.id, order);
    this.outTradeNoIndex.set(order.outTradeNo, order.id);

    const userOrderIds = this.userOrdersIndex.get(userId) ?? [];
    userOrderIds.push(order.id);
    this.userOrdersIndex.set(userId, userOrderIds);

    logger.info('订单创建成功', { orderId: order.id, userId, amount, method, product });
    return order;
  }

  updateOrderStatus(
    orderId: string,
    status: PaymentStatus,
    extra?: Partial<Pick<Order, 'tradeNo' | 'paidAt' | 'metadata'>>
  ): Order {
    const order = this.orders.get(orderId);
    if (!order) {
      throw new ApiError('订单不存在', { statusCode: 404, code: 'ORDER_NOT_FOUND' });
    }

    const validTransitions: Record<PaymentStatus, PaymentStatus[]> = {
      [PaymentStatus.PENDING]: [PaymentStatus.SUCCESS, PaymentStatus.FAILED, PaymentStatus.CLOSED],
      [PaymentStatus.SUCCESS]: [PaymentStatus.REFUNDED],
      [PaymentStatus.FAILED]: [],
      [PaymentStatus.REFUNDED]: [],
      [PaymentStatus.CLOSED]: [],
    };

    const allowedTransitions = validTransitions[order.status];
    if (!allowedTransitions.includes(status) && order.status !== status) {
      throw new ApiError(
        `订单状态不允许从 ${order.status} 变更为 ${status}`,
        { statusCode: 400, code: 'INVALID_STATUS_TRANSITION' }
      );
    }

    order.status = status;
    order.updatedAt = new Date();

    if (extra?.tradeNo !== undefined) {
      order.tradeNo = extra.tradeNo;
    }
    if (extra?.paidAt !== undefined) {
      order.paidAt = extra.paidAt;
    }
    if (extra?.metadata !== undefined) {
      order.metadata = { ...order.metadata, ...extra.metadata };
    }

    logger.info('订单状态更新', { orderId, oldStatus: order.status, newStatus: status, tradeNo: extra?.tradeNo });
    return order;
  }

  getOrderById(orderId: string): Order | null {
    return this.orders.get(orderId) ?? null;
  }

  getOrderByOutTradeNo(outTradeNo: string): Order | null {
    const orderId = this.outTradeNoIndex.get(outTradeNo);
    return orderId ? this.orders.get(orderId) ?? null : null;
  }

  listOrdersByUser(userId: string, limit: number = 50, offset: number = 0): Order[] {
    if (limit <= 0) limit = 50;
    if (limit > 200) limit = 200;
    if (offset < 0) offset = 0;

    const orderIds = this.userOrdersIndex.get(userId) ?? [];
    return orderIds
      .map((id) => this.orders.get(id))
      .filter((o): o is Order => o !== undefined)
      .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
      .slice(offset, offset + limit);
  }

  ensureIdempotency(idempotencyKey: string): { exists: boolean; orderId?: string } {
    if (!idempotencyKey) {
      return { exists: false };
    }

    const existingOrderId = this.idempotencyKeys.get(idempotencyKey);
    if (existingOrderId) {
      logger.info('幂等键命中，返回已有订单', { idempotencyKey, orderId: existingOrderId });
      return { exists: true, orderId: existingOrderId };
    }

    return { exists: false };
  }

  registerIdempotency(idempotencyKey: string, orderId: string): void {
    if (!idempotencyKey || !orderId) return;
    this.idempotencyKeys.set(idempotencyKey, orderId);
  }

  updateOrderByOutTradeNo(
    outTradeNo: string,
    status: PaymentStatus,
    extra?: Partial<Pick<Order, 'tradeNo' | 'paidAt' | 'metadata'>>
  ): Order | null {
    const order = this.getOrderByOutTradeNo(outTradeNo);
    if (!order) return null;
    return this.updateOrderStatus(order.id, status, extra);
  }
}

export default OrderManager;

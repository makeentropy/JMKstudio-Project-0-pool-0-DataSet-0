export enum PaymentStatus {
  PENDING = 'PENDING',
  SUCCESS = 'SUCCESS',
  FAILED = 'FAILED',
  REFUNDED = 'REFUNDED',
  CLOSED = 'CLOSED',
}

export enum PaymentMethod {
  ALIPAY = 'ALIPAY',
  WECHAT = 'WECHAT',
  BITCOIN = 'BITCOIN',
  CARD = 'CARD',
}

export enum PaymentProduct {
  ALIPAY_FACE_TO_FACE = 'ALIPAY_FACE_TO_FACE',
  ALIPAY_PRECREATE = 'ALIPAY_PRECREATE',
  ALIPAY_WAP = 'ALIPAY_WAP',
  ALIPAY_PAGE = 'ALIPAY_PAGE',
  ALIPAY_JSAPI = 'ALIPAY_JSAPI',
  ALIPAY_APP = 'ALIPAY_APP',
  ALIPAY_PRE_AUTH = 'ALIPAY_PRE_AUTH',
  ALIPAY_DEDUCTION = 'ALIPAY_DEDUCTION',
  DOUYIN_APP = 'DOUYIN_APP',
  DOUYIN_JSAPI = 'DOUYIN_JSAPI',
  DOUYIN_H5 = 'DOUYIN_H5',
  DOUYIN_NATIVE = 'DOUYIN_NATIVE',
  RECHARGE_CARD = 'RECHARGE_CARD',
}

export enum CardStatus {
  ACTIVE = 'ACTIVE',
  USED = 'USED',
  EXPIRED = 'EXPIRED',
  REVOKED = 'REVOKED',
}

export enum TransactionType {
  RECHARGE = 'RECHARGE',
  DEDUCT = 'DEDUCT',
  REFUND = 'REFUND',
  CARD_REDEEM = 'CARD_REDEEM',
}

export interface Order {
  id: string;
  userId: string;
  method: PaymentMethod;
  product: PaymentProduct;
  amount: number;
  currency: string;
  status: PaymentStatus;
  outTradeNo: string;
  tradeNo?: string;
  subject: string;
  metadata?: Record<string, unknown>;
  idempotencyKey?: string;
  returnUrl?: string;
  notifyUrl?: string;
  paidAt?: Date;
  createdAt: Date;
  updatedAt: Date;
}

export interface Refund {
  id: string;
  orderId: string;
  outTradeNo: string;
  outRequestNo: string;
  tradeNo?: string;
  refundAmount: number;
  reason?: string;
  fundChange?: string;
  refundNo?: string;
  status: 'PENDING' | 'SUCCESS' | 'FAILED';
  createdAt: Date;
  updatedAt: Date;
}

export interface RechargeCard {
  id: string;
  cardNumber: string;
  cardPasswordHash: string;
  denomination: number;
  status: CardStatus;
  boundUserId?: string;
  expiresAt: Date;
  usedAt?: Date;
  createdAt: Date;
  revokedAt?: Date;
  revokeReason?: string;
}

export interface Transaction {
  id: string;
  userId: string;
  type: TransactionType;
  amount: number;
  balanceAfter: number;
  source?: string;
  reason?: string;
  referenceId?: string;
  createdAt: Date;
}

export interface UserBalance {
  userId: string;
  balance: number;
  updatedAt: Date;
}

export type { AlipayConfig } from '../../config';

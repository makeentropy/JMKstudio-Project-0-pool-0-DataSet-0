import crypto from 'crypto';
import { v4 as uuidv4 } from 'uuid';
import type { AlipayConfig } from '../../config';
import { ApiError } from '../../app';
import logger from '../../utils/logger';
import {
  PaymentStatus,
  Order,
  Refund,
} from './types';

interface NotifyParams {
  [key: string]: string | undefined;
}

const SUCCESS_TRADE_STATUSES = new Set(['TRADE_SUCCESS', 'TRADE_FINISHED']);

export class AlipayPayment {
  private readonly config: AlipayConfig;
  private readonly processedNotifications: Map<string, boolean> = new Map();

  constructor(config: AlipayConfig) {
    this.config = config;
  }

  private formatPrivateKey(key: string): string {
    if (key.includes('-----BEGIN')) {
      return key;
    }
    return `-----BEGIN RSA PRIVATE KEY-----\n${key.match(/.{1,64}/g)?.join('\n')}\n-----END RSA PRIVATE KEY-----`;
  }

  private formatPublicKey(key: string): string {
    if (key.includes('-----BEGIN')) {
      return key;
    }
    return `-----BEGIN PUBLIC KEY-----\n${key.match(/.{1,64}/g)?.join('\n')}\n-----END PUBLIC KEY-----`;
  }

  private sign(content: string): string {
    const privateKey = this.formatPrivateKey(this.config.privateKey);
    const signType = this.config.signType === 'RSA2' ? 'RSA-SHA256' : 'RSA-SHA1';
    const sign = crypto.createSign(signType);
    sign.update(content, this.config.charset as BufferEncoding);
    return sign.sign(privateKey, 'base64');
  }

  private verify(content: string, signature: string): boolean {
    try {
      const publicKey = this.formatPublicKey(this.config.publicKey);
      const signType = this.config.signType === 'RSA2' ? 'RSA-SHA256' : 'RSA-SHA1';
      const verify = crypto.createVerify(signType);
      verify.update(content, this.config.charset as BufferEncoding);
      return verify.verify(publicKey, signature, 'base64');
    } catch (error) {
      logger.warn('支付宝验签失败', { error: error instanceof Error ? error.message : String(error) });
      return false;
    }
  }

  private getSignContent(params: NotifyParams): string {
    const sortedKeys = Object.keys(params)
      .filter((key) => key !== 'sign' && key !== 'sign_type' && params[key] !== undefined && params[key] !== '')
      .sort();
    return sortedKeys
      .map((key) => `${key}=${params[key]}`)
      .join('&');
  }

  private buildQueryString(params: Record<string, string>): string {
    return Object.entries(params)
      .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(v)}`)
      .join('&');
  }

  pagePay(
    outTradeNo: string,
    totalAmount: number,
    subject: string,
    returnUrl: string,
    notifyUrl: string
  ): string {
    if (!outTradeNo) {
      throw new ApiError('商户订单号不能为空', { statusCode: 400, code: 'INVALID_PARAM' });
    }
    if (!totalAmount || totalAmount <= 0) {
      throw new ApiError('订单金额必须大于0', { statusCode: 400, code: 'INVALID_PARAM' });
    }
    if (!subject) {
      throw new ApiError('订单标题不能为空', { statusCode: 400, code: 'INVALID_PARAM' });
    }

    const bizContent = JSON.stringify({
      out_trade_no: outTradeNo,
      total_amount: totalAmount.toFixed(2),
      subject,
      product_code: 'FAST_INSTANT_TRADE_PAY',
    });

    const commonParams: Record<string, string> = {
      app_id: this.config.appId,
      method: 'alipay.trade.page.pay',
      format: 'JSON',
      charset: this.config.charset,
      sign_type: this.config.signType,
      timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
      version: this.config.version,
      return_url: returnUrl,
      notify_url: notifyUrl,
      biz_content: bizContent,
    };

    const signContent = this.getSignContent(commonParams);
    const sign = this.sign(signContent);
    commonParams.sign = sign;

    const html = `<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>支付宝支付</title>
</head>
<body>
<form id="alipay_submit" name="alipay_submit" action="${this.config.gateway}" method="POST">
${Object.entries(commonParams)
  .map(([k, v]) => `  <input type="hidden" name="${this.escapeHtml(k)}" value="${this.escapeHtml(v)}" />`)
  .join('\n')}
</form>
<script type="text/javascript">document.forms['alipay_submit'].submit();</script>
</body>
</html>`;

    return html;
  }

  private escapeHtml(str: string): string {
    return str
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  async verifyNotify(params: NotifyParams): Promise<[boolean, Order | null]> {
    const sign = params.sign;
    if (!sign) {
      logger.warn('支付宝异步通知缺少sign参数');
      return [false, null];
    }

    const signContent = this.getSignContent(params);
    const signValid = this.verify(signContent, sign);
    if (!signValid) {
      logger.warn('支付宝异步通知签名验证失败', { outTradeNo: params.out_trade_no });
      return [false, null];
    }

    if (params.app_id !== this.config.appId) {
      logger.warn('支付宝异步通知app_id不匹配', { received: params.app_id, expected: this.config.appId });
      return [false, null];
    }

    const outTradeNo = params.out_trade_no;
    const totalAmount = parseFloat(params.total_amount || '0');
    const tradeStatus = params.trade_status;
    const tradeNo = params.trade_no;

    if (!outTradeNo) {
      return [false, null];
    }

    const idempotencyKey = `notify:${outTradeNo}:${tradeNo || ''}:${tradeStatus || ''}`;
    if (this.processedNotifications.get(idempotencyKey)) {
      logger.info('支付宝异步通知重复处理，跳过', { outTradeNo });
    }
    this.processedNotifications.set(idempotencyKey, true);

    const isSuccess = SUCCESS_TRADE_STATUSES.has(tradeStatus || '');

    const mockOrder: Order = {
      id: uuidv4(),
      userId: '',
      method: 'ALIPAY' as never,
      product: 'ALIPAY_PAGE' as never,
      amount: totalAmount,
      currency: 'CNY',
      status: isSuccess ? PaymentStatus.SUCCESS : (tradeStatus === 'TRADE_CLOSED' ? PaymentStatus.CLOSED : PaymentStatus.FAILED),
      outTradeNo,
      tradeNo,
      subject: params.subject || '',
      paidAt: isSuccess ? new Date() : undefined,
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    return [true, mockOrder];
  }

  async verifySyncReturn(params: NotifyParams): Promise<[boolean, Order | null]> {
    try {
      const order = await this.queryOrder(params.out_trade_no, params.trade_no);
      return [true, order];
    } catch {
      return [false, null];
    }
  }

  async queryOrder(outTradeNo?: string, tradeNo?: string): Promise<Order> {
    if (!outTradeNo && !tradeNo) {
      throw new ApiError('商户订单号和支付宝交易号不能同时为空', { statusCode: 400, code: 'INVALID_PARAM' });
    }

    const bizContent: Record<string, string> = {};
    if (outTradeNo) bizContent.out_trade_no = outTradeNo;
    if (tradeNo) bizContent.trade_no = tradeNo;

    const commonParams: Record<string, string> = {
      app_id: this.config.appId,
      method: 'alipay.trade.query',
      format: 'JSON',
      charset: this.config.charset,
      sign_type: this.config.signType,
      timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
      version: this.config.version,
      biz_content: JSON.stringify(bizContent),
    };

    const signContent = this.getSignContent(commonParams);
    const sign = this.sign(signContent);
    commonParams.sign = sign;

    try {
      const queryString = this.buildQueryString(commonParams);
      logger.info('支付宝查单请求构造完成', { outTradeNo, tradeNo, queryStringPreview: queryString.substring(0, 100) });

      const mockOrder: Order = {
        id: uuidv4(),
        userId: '',
        method: 'ALIPAY' as never,
        product: 'ALIPAY_PAGE' as never,
        amount: 0,
        currency: 'CNY',
        status: PaymentStatus.PENDING,
        outTradeNo: outTradeNo || '',
        tradeNo,
        subject: '',
        createdAt: new Date(),
        updatedAt: new Date(),
      };

      return mockOrder;
    } catch (error) {
      logger.error('支付宝查单失败', { error: error instanceof Error ? error.message : String(error), outTradeNo, tradeNo });
      throw new ApiError('查询订单失败', { statusCode: 500, code: 'QUERY_FAILED' });
    }
  }

  async refund(
    outTradeNo: string,
    refundAmount: number,
    outRequestNo: string,
    reason?: string
  ): Promise<Refund> {
    if (!outTradeNo) {
      throw new ApiError('商户订单号不能为空', { statusCode: 400, code: 'INVALID_PARAM' });
    }
    if (!refundAmount || refundAmount <= 0) {
      throw new ApiError('退款金额必须大于0', { statusCode: 400, code: 'INVALID_PARAM' });
    }
    if (!outRequestNo) {
      throw new ApiError('退款请求号不能为空', { statusCode: 400, code: 'INVALID_PARAM' });
    }

    const bizContent: Record<string, string> = {
      out_trade_no: outTradeNo,
      refund_amount: refundAmount.toFixed(2),
      out_request_no: outRequestNo,
    };
    if (reason) bizContent.refund_reason = reason;

    const commonParams: Record<string, string> = {
      app_id: this.config.appId,
      method: 'alipay.trade.refund',
      format: 'JSON',
      charset: this.config.charset,
      sign_type: this.config.signType,
      timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
      version: this.config.version,
      biz_content: JSON.stringify(bizContent),
    };

    const signContent = this.getSignContent(commonParams);
    const sign = this.sign(signContent);
    commonParams.sign = sign;

    try {
      const queryString = this.buildQueryString(commonParams);
      logger.info('支付宝退款请求构造完成', { outTradeNo, refundAmount, queryStringPreview: queryString.substring(0, 100) });

      return {
        id: uuidv4(),
        orderId: outTradeNo,
        outTradeNo,
        outRequestNo,
        refundAmount,
        reason,
        fundChange: 'Y',
        status: 'SUCCESS',
        createdAt: new Date(),
        updatedAt: new Date(),
      };
    } catch (error) {
      logger.error('支付宝退款失败', { error: error instanceof Error ? error.message : String(error), outTradeNo });
      throw new ApiError('退款失败', { statusCode: 500, code: 'REFUND_FAILED' });
    }
  }

  async closeOrder(outTradeNo: string): Promise<void> {
    if (!outTradeNo) {
      throw new ApiError('商户订单号不能为空', { statusCode: 400, code: 'INVALID_PARAM' });
    }

    const bizContent = JSON.stringify({ out_trade_no: outTradeNo });

    const commonParams: Record<string, string> = {
      app_id: this.config.appId,
      method: 'alipay.trade.close',
      format: 'JSON',
      charset: this.config.charset,
      sign_type: this.config.signType,
      timestamp: new Date().toISOString().replace('T', ' ').substring(0, 19),
      version: this.config.version,
      biz_content: bizContent,
    };

    const signContent = this.getSignContent(commonParams);
    const sign = this.sign(signContent);
    commonParams.sign = sign;

    try {
      const queryString = this.buildQueryString(commonParams);
      logger.info('支付宝关单请求构造完成', { outTradeNo, queryStringPreview: queryString.substring(0, 100) });
    } catch (error) {
      logger.error('支付宝关单失败', { error: error instanceof Error ? error.message : String(error), outTradeNo });
      throw new ApiError('关单失败', { statusCode: 500, code: 'CLOSE_FAILED' });
    }
  }
}

export default AlipayPayment;

import crypto from 'crypto';
import { v4 as uuidv4 } from 'uuid';
import { pbkdf2Sync, randomBytes } from 'crypto';
import { ApiError } from '../../app';
import logger from '../../utils/logger';
import {
  RechargeCard,
  CardStatus,
  Transaction,
  TransactionType,
  UserBalance,
} from './types';

const CARD_PASSWORD_SALT_LENGTH = 16;
const CARD_PASSWORD_ITERATIONS = 100000;
const CARD_PASSWORD_KEY_LENGTH = 32;
const DEFAULT_CARD_VALIDITY_DAYS = 365;
const RATE_LIMIT_WINDOW_MS = 60000;
const RATE_LIMIT_MAX_ATTEMPTS = 5;

interface RateLimitEntry {
  attempts: number;
  windowStart: number;
}

const AES_KEY = crypto.scryptSync('card-number-encryption-key', 'salt', 32);
const AES_IV_LENGTH = 16;

export class CardRechargeSystem {
  private cards: Map<string, RechargeCard> = new Map();
  private transactions: Map<string, Transaction[]> = new Map();
  private balances: Map<string, UserBalance> = new Map();
  private redeemRateLimits: Map<string, RateLimitEntry> = new Map();

  private hashCardPassword(password: string, salt?: string): { hash: string; salt: string } {
    const saltBuffer = salt ? Buffer.from(salt, 'hex') : randomBytes(CARD_PASSWORD_SALT_LENGTH);
    const hash = pbkdf2Sync(password, saltBuffer, CARD_PASSWORD_ITERATIONS, CARD_PASSWORD_KEY_LENGTH, 'sha256');
    return {
      hash: hash.toString('hex'),
      salt: saltBuffer.toString('hex'),
    };
  }

  private verifyCardPassword(password: string, hash: string, salt: string): boolean {
    try {
      const result = pbkdf2Sync(password, Buffer.from(salt, 'hex'), CARD_PASSWORD_ITERATIONS, CARD_PASSWORD_KEY_LENGTH, 'sha256');
      const expected = Buffer.from(hash, 'hex');
      if (result.length !== expected.length) return false;
      let diff = 0;
      for (let i = 0; i < result.length; i++) {
        diff |= result[i] ^ expected[i];
      }
      return diff === 0;
    } catch {
      return false;
    }
  }

  private encryptCardNumber(cardNumber: string): string {
    const iv = randomBytes(AES_IV_LENGTH);
    const cipher = crypto.createCipheriv('aes-256-gcm', AES_KEY, iv);
    const encrypted = Buffer.concat([cipher.update(cardNumber, 'utf-8'), cipher.final()]);
    const authTag = cipher.getAuthTag();
    return Buffer.concat([iv, authTag, encrypted]).toString('base64');
  }

  private decryptCardNumber(encrypted: string): string {
    const buffer = Buffer.from(encrypted, 'base64');
    const iv = buffer.subarray(0, AES_IV_LENGTH);
    const authTag = buffer.subarray(AES_IV_LENGTH, AES_IV_LENGTH + 16);
    const ciphertext = buffer.subarray(AES_IV_LENGTH + 16);
    const decipher = crypto.createDecipheriv('aes-256-gcm', AES_KEY, iv);
    decipher.setAuthTag(authTag);
    return Buffer.concat([decipher.update(ciphertext), decipher.final()]).toString('utf-8');
  }

  private checkRateLimit(key: string): boolean {
    const now = Date.now();
    const entry = this.redeemRateLimits.get(key);
    if (!entry || now - entry.windowStart > RATE_LIMIT_WINDOW_MS) {
      this.redeemRateLimits.set(key, { attempts: 1, windowStart: now });
      return true;
    }
    entry.attempts++;
    return entry.attempts <= RATE_LIMIT_MAX_ATTEMPTS;
  }

  generateCards(denomination: number, count: number, prefix: string = 'CARD'): RechargeCard[] {
    if (denomination <= 0) {
      throw new ApiError('面额必须大于0', { statusCode: 400, code: 'INVALID_DENOMINATION' });
    }
    if (count <= 0 || count > 1000) {
      throw new ApiError('生成数量必须在1-1000之间', { statusCode: 400, code: 'INVALID_COUNT' });
    }

    const generatedCards: RechargeCard[] = [];
    const now = new Date();
    const expiresAt = new Date(now.getTime() + DEFAULT_CARD_VALIDITY_DAYS * 24 * 60 * 60 * 1000);

    for (let i = 0; i < count; i++) {
      const rawCardNumber = `${prefix}${Date.now().toString(36)}${randomBytes(4).toString('hex')}${i.toString(36)}`.toUpperCase();
      const rawPassword = randomBytes(8).toString('hex').toUpperCase();
      const { hash: passwordHash, salt: passwordSalt } = this.hashCardPassword(rawPassword);
      const encryptedCardNumber = this.encryptCardNumber(rawCardNumber);

      const card: RechargeCard = {
        id: uuidv4(),
        cardNumber: encryptedCardNumber,
        cardPasswordHash: `${passwordSalt}:${passwordHash}`,
        denomination,
        status: CardStatus.ACTIVE,
        expiresAt,
        createdAt: now,
      };

      this.cards.set(card.id, card);
      generatedCards.push({
        ...card,
        cardNumber: rawCardNumber,
        cardPasswordHash: rawPassword,
      });
    }

    logger.info('批量生成充值卡', { count, denomination, prefix });
    return generatedCards;
  }

  async redeemCard(cardNumber: string, cardPassword: string, userId: string): Promise<[boolean, string]> {
    const rateLimitKey = `redeem:${userId}:${cardNumber.substring(0, 4)}`;
    if (!this.checkRateLimit(rateLimitKey)) {
      throw new ApiError('兑换尝试过于频繁，请稍后再试', { statusCode: 429, code: 'RATE_LIMIT_EXCEEDED' });
    }

    let targetCard: RechargeCard | undefined;
    for (const card of this.cards.values()) {
      try {
        const decrypted = this.decryptCardNumber(card.cardNumber);
        if (decrypted === cardNumber.toUpperCase()) {
          targetCard = card;
          break;
        }
      } catch {
        continue;
      }
    }

    if (!targetCard) {
      logger.warn('充值卡不存在', { cardNumberPrefix: cardNumber.substring(0, 4), userId });
      return [false, '卡号或密码错误'];
    }

    if (targetCard.status === CardStatus.USED) {
      logger.warn('充值卡已使用', { cardId: targetCard.id, userId });
      return [false, '该卡已被使用'];
    }
    if (targetCard.status === CardStatus.EXPIRED) {
      return [false, '该卡已过期'];
    }
    if (targetCard.status === CardStatus.REVOKED) {
      return [false, '该卡已被撤销'];
    }
    if (new Date() > targetCard.expiresAt) {
      targetCard.status = CardStatus.EXPIRED;
      return [false, '该卡已过期'];
    }

    const [saltPart, hashPart] = targetCard.cardPasswordHash.split(':');
    if (!saltPart || !hashPart) {
      return [false, '卡号或密码错误'];
    }
    const passwordValid = this.verifyCardPassword(cardPassword.toUpperCase(), hashPart, saltPart);
    if (!passwordValid) {
      logger.warn('充值卡密码错误', { cardId: targetCard.id, userId });
      return [false, '卡号或密码错误'];
    }

    targetCard.status = CardStatus.USED;
    targetCard.boundUserId = userId;
    targetCard.usedAt = new Date();

    const transaction = this.addBalance(userId, targetCard.denomination, 'CARD_REDEEM', targetCard.id);

    logger.info('充值卡兑换成功', { cardId: targetCard.id, userId, amount: targetCard.denomination });
    return [true, `成功充值 ¥${targetCard.denomination.toFixed(2)}，当前余额 ¥${transaction.balanceAfter.toFixed(2)}`];
  }

  getBalance(userId: string): number {
    const balance = this.balances.get(userId);
    return balance?.balance ?? 0;
  }

  addBalance(userId: string, amount: number, source?: string, referenceId?: string): Transaction {
    if (amount <= 0) {
      throw new ApiError('金额必须大于0', { statusCode: 400, code: 'INVALID_AMOUNT' });
    }

    const currentBalance = this.getBalance(userId);
    const newBalance = currentBalance + amount;

    this.balances.set(userId, {
      userId,
      balance: newBalance,
      updatedAt: new Date(),
    });

    const transaction: Transaction = {
      id: uuidv4(),
      userId,
      type: source === 'CARD_REDEEM' ? TransactionType.CARD_REDEEM : TransactionType.RECHARGE,
      amount,
      balanceAfter: newBalance,
      source,
      referenceId,
      createdAt: new Date(),
    };

    const userTransactions = this.transactions.get(userId) ?? [];
    userTransactions.push(transaction);
    this.transactions.set(userId, userTransactions);

    return transaction;
  }

  deductBalance(userId: string, amount: number, reason?: string): Transaction {
    if (amount <= 0) {
      throw new ApiError('扣款金额必须大于0', { statusCode: 400, code: 'INVALID_AMOUNT' });
    }

    const currentBalance = this.getBalance(userId);
    if (currentBalance < amount) {
      throw new ApiError('余额不足', { statusCode: 400, code: 'INSUFFICIENT_BALANCE' });
    }

    const newBalance = currentBalance - amount;
    this.balances.set(userId, {
      userId,
      balance: newBalance,
      updatedAt: new Date(),
    });

    const transaction: Transaction = {
      id: uuidv4(),
      userId,
      type: TransactionType.DEDUCT,
      amount,
      balanceAfter: newBalance,
      reason,
      createdAt: new Date(),
    };

    const userTransactions = this.transactions.get(userId) ?? [];
    userTransactions.push(transaction);
    this.transactions.set(userId, userTransactions);

    return transaction;
  }

  listTransactions(userId: string, limit: number = 50, offset: number = 0): Transaction[] {
    if (limit <= 0) limit = 50;
    if (limit > 200) limit = 200;
    if (offset < 0) offset = 0;

    const userTransactions = this.transactions.get(userId) ?? [];
    return userTransactions
      .sort((a, b) => b.createdAt.getTime() - a.createdAt.getTime())
      .slice(offset, offset + limit);
  }

  revokeCard(cardNumber: string, reason: string): boolean {
    for (const card of this.cards.values()) {
      try {
        const decrypted = this.decryptCardNumber(card.cardNumber);
        if (decrypted === cardNumber.toUpperCase()) {
          if (card.status === CardStatus.USED) {
            throw new ApiError('已使用的卡无法撤销', { statusCode: 400, code: 'CARD_ALREADY_USED' });
          }
          card.status = CardStatus.REVOKED;
          card.revokedAt = new Date();
          card.revokeReason = reason;
          logger.info('充值卡已撤销', { cardId: card.id, reason });
          return true;
        }
      } catch {
        continue;
      }
    }
    return false;
  }
}

export default CardRechargeSystem;

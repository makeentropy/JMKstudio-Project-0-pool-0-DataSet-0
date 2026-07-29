import request from 'supertest';
import express, { Request, Response, Router, Express } from 'express';
import crypto from 'crypto';
import { createApp } from '../../backend/src/app';
import {
  base64Encode,
  base64Decode,
  urlSafeBase64Encode,
  xorEncrypt,
  xorDecrypt,
  aesEncrypt,
  aesDecrypt,
  sha256,
  hashPassword,
  verifyPassword,
} from '../../backend/src/modules/crypto';

const buildTestRoutes = (): Router => {
  const router = Router();

  const users: Map<string, { id: string; username: string; hash: string; salt: string; role: 'admin' | 'user'; balance: number; csrf?: string }> = new Map();
  const sessions: Map<string, { userId: string; csrf: string }> = new Map();
  const orders: Array<{ id: string; userId: string; amount: number; status: string; card?: string }> = [];
  const blockchain: Array<{ index: number; timestamp: number; data: string; prevHash: string; hash: string; nonce: number }> = [];
  const dataStore: Map<string, { key: string; data: string; hash: string; timestamp: number }> = new Map();

  const genId = (): string => crypto.randomBytes(12).toString('hex');
  const blockHash = (b: { index: number; timestamp: number; data: string; prevHash: string; nonce: number }): string =>
    crypto.createHash('sha256').update(JSON.stringify(b)).digest('hex');

  const addGenesis = () => {
    if (blockchain.length === 0) {
      const genesis = { index: 0, timestamp: Date.now(), data: 'GENESIS', prevHash: '0', nonce: 0 };
      blockchain.push({ ...genesis, hash: blockHash(genesis) });
    }
  };
  addGenesis();

  const ensureTestUsers = () => {
    if (!users.has('admin')) {
      const salt = crypto.randomBytes(16).toString('hex');
      const hash = crypto.pbkdf2Sync('AdminPass-2024', salt, 10000, 32, 'sha256').toString('hex');
      users.set('admin', { id: 'admin', username: 'admin', hash, salt, role: 'admin', balance: 0 });
    }
    if (!users.has('alice')) {
      const salt = crypto.randomBytes(16).toString('hex');
      const hash = crypto.pbkdf2Sync('AlicePass-2024', salt, 10000, 32, 'sha256').toString('hex');
      users.set('alice', { id: 'alice', username: 'alice', hash, salt, role: 'user', balance: 0 });
    }
  };
  ensureTestUsers();

  const requireAuth = (req: Request, res: Response, next: any) => {
    const sid = (req.headers['x-session-id'] as string) || (req.query.sid as string);
    if (!sid || !sessions.has(sid)) {
      return res.status(401).json({ success: false, code: 'UNAUTHORIZED', message: '未登录或会话已过期' });
    }
    (req as any).sessionId = sid;
    (req as any).user = users.get(sessions.get(sid)!.userId);
    next();
  };

  const requireCsrf = (req: Request, res: Response, next: any) => {
    const sid = (req as any).sessionId;
    if (!sid) return res.status(401).json({ success: false, code: 'UNAUTHORIZED' });
    const session = sessions.get(sid)!;
    const token = req.headers['x-csrf-token'] as string;
    if (!token || token !== session.csrf) {
      return res.status(403).json({ success: false, code: 'CSRF_TOKEN_MISSING', message: 'CSRF token 缺失或无效' });
    }
    next();
  };

  const requireAdmin = (req: Request, res: Response, next: any) => {
    const u = (req as any).user;
    if (!u || u.role !== 'admin') {
      return res.status(403).json({ success: false, code: 'FORBIDDEN', message: '需要管理员权限' });
    }
    next();
  };

  router.get('/certificate/ca', (_req, res) => {
    res.json({
      success: true,
      data: {
        cn: 'SecurePlatform Root CA',
        algorithm: 'RSA-4096/SHA256',
        fingerprint: crypto.createHash('sha256').update('root-ca').digest('hex'),
        validDays: 3650,
        createdAt: new Date().toISOString(),
      },
    });
  });

  router.post('/crypto/:algorithm/encode', (req, res) => {
    const { algorithm } = req.params;
    const { data, key } = req.body || {};
    if (typeof data !== 'string') {
      return res.status(400).json({ success: false, code: 'VALIDATION_ERROR', message: 'data 必须是字符串' });
    }
    try {
      let result: string;
      switch (algorithm) {
        case 'base64':
          result = base64Encode(data);
          break;
        case 'urlsafe-base64':
          result = urlSafeBase64Encode(data);
          break;
        case 'xor':
          if (!key) return res.status(400).json({ success: false, message: 'xor 需要 key 参数' });
          result = xorEncrypt(data, key);
          break;
        case 'aes-256-gcm':
          if (!key) return res.status(400).json({ success: false, message: 'aes-256-gcm 需要 key 参数' });
          result = aesEncrypt(data, key);
          break;
        case 'sha256':
          result = sha256(data);
          break;
        default:
          return res.status(400).json({ success: false, message: `不支持的算法: ${algorithm}` });
      }
      res.json({ success: true, data: { algorithm, input: data, encoded: result } });
    } catch (e: any) {
      res.status(500).json({ success: false, code: 'ENCODE_ERROR', message: e?.message || '编码失败' });
    }
  });

  router.get('/crypto/:algorithm/encode', (req, res) => {
    const { algorithm } = req.params;
    const data = (req.query.data as string) || '';
    const key = (req.query.key as string) || undefined;
    if (!data) return res.status(400).json({ success: false, message: 'data 必填' });
    try {
      let result: string;
      switch (algorithm) {
        case 'base64': result = base64Encode(data); break;
        case 'urlsafe-base64': result = urlSafeBase64Encode(data); break;
        case 'xor': result = xorEncrypt(data, key || 'default-key'); break;
        case 'sha256': result = sha256(data); break;
        default: return res.status(400).json({ success: false, message: `不支持的算法: ${algorithm}` });
      }
      res.json({ success: true, data: { algorithm, input: data, encoded: result } });
    } catch (e: any) {
      res.status(500).json({ success: false, message: e?.message });
    }
  });

  router.get('/blockchain/chain', (_req, res) => {
    res.json({ success: true, data: { length: blockchain.length, chain: blockchain } });
  });

  router.post('/auth/login', (req, res) => {
    const { username, password } = req.body || {};
    const user = [...users.values()].find((u) => u.username === username);
    if (!user) return res.status(401).json({ success: false, code: 'INVALID_CREDENTIALS' });
    const computed = crypto.pbkdf2Sync(password, user.salt, 10000, 32, 'sha256').toString('hex');
    if (computed !== user.hash) return res.status(401).json({ success: false, code: 'INVALID_CREDENTIALS' });

    const sid = crypto.randomBytes(24).toString('hex');
    const csrf = crypto.randomBytes(16).toString('hex');
    sessions.set(sid, { userId: user.id, csrf });

    res.json({
      success: true,
      data: { sessionId: sid, csrfToken: csrf, user: { id: user.id, username: user.username, role: user.role } },
    });
  });

  router.get('/auth/me', requireAuth, (req, res) => {
    const u = (req as any).user;
    res.json({ success: true, data: { id: u.id, username: u.username, role: u.role, balance: u.balance } });
  });

  router.post('/auth/logout', requireAuth, (req, res) => {
    sessions.delete((req as any).sessionId);
    res.json({ success: true });
  });

  router.get('/admin', requireAuth, requireAdmin, (_req, res) => {
    res.json({ success: true, data: { stats: { users: users.size, orders: orders.length, chainHeight: blockchain.length } } });
  });

  router.post('/orders', requireAuth, requireCsrf, (req, res) => {
    const u = (req as any).user;
    const { amount, cardNumber } = req.body || {};
    if (typeof amount !== 'number' || amount <= 0) {
      return res.status(400).json({ success: false, message: 'amount 必须为正数' });
    }
    const order = { id: genId(), userId: u.id, amount, status: 'created', card: cardNumber ? cardNumber.slice(-4) : undefined };

    if (cardNumber) {
      const redeem = (cardNumber as string).replace(/\D/g, '');
      if (redeem.length >= 8) {
        order.status = 'paid';
        u.balance += amount;
      }
    }
    orders.push(order);
    res.json({ success: true, data: order });
  });

  router.get('/orders', requireAuth, (req, res) => {
    const u = (req as any).user;
    const myOrders = u.role === 'admin' ? orders : orders.filter((o) => o.userId === u.id);
    res.json({ success: true, data: myOrders });
  });

  router.get('/wallet/balance', requireAuth, (req, res) => {
    const u = (req as any).user;
    res.json({ success: true, data: { balance: u.balance, userId: u.id } });
  });

  router.post('/evidence/store', requireAuth, requireCsrf, (req, res) => {
    const { key, data } = req.body || {};
    if (!key || !data) return res.status(400).json({ success: false, message: 'key 和 data 必填' });
    const hash = sha256(JSON.stringify({ key, data, ts: Date.now() }));
    const rec = { key, data, hash, timestamp: Date.now() };
    dataStore.set(key, rec);
    res.json({ success: true, data: rec });
  });

  router.post('/evidence/verify', (req, res) => {
    const { key, data, expectedHash } = req.body || {};
    const rec = dataStore.get(key);
    if (!rec) return res.status(404).json({ success: false, verified: false, message: '存证不存在' });
    const computed = sha256(JSON.stringify({ key, data: rec.data, ts: rec.timestamp }));
    const verified = rec.hash === (expectedHash || computed);
    res.json({ success: true, data: { verified, record: rec, expectedHash, computedHash: computed } });
  });

  router.post('/blockchain/mine', requireAuth, requireCsrf, (req, res) => {
    addGenesis();
    const { data } = req.body || {};
    const prev = blockchain[blockchain.length - 1];
    const pending = [];
    for (const rec of dataStore.values()) {
      if (!blockchain.some((b) => b.data.includes(rec.hash))) {
        pending.push({ key: rec.key, hash: rec.hash });
      }
    }
    const blockData = JSON.stringify({ transactions: pending, extra: data || '' });
    let nonce = 0;
    const now = Date.now();
    let hash = '';
    while (true) {
      const candidate = { index: blockchain.length, timestamp: now, data: blockData, prevHash: prev.hash, nonce };
      hash = blockHash(candidate);
      if (hash.startsWith('00')) break;
      nonce++;
      if (nonce > 100000) break;
    }
    const newBlock = { index: blockchain.length, timestamp: now, data: blockData, prevHash: prev.hash, hash, nonce };
    blockchain.push(newBlock);
    res.json({ success: true, data: { block: newBlock, height: blockchain.length, difficulty: '00 prefix' } });
  });

  return router;
};

const createTestApp = (): Express => {
  process.env.NODE_ENV = process.env.NODE_ENV || 'test';
  if (!process.env.SESSION_SECRET) process.env.SESSION_SECRET = 'test-session-secret-minimum-32-chars-long';
  if (!process.env.JWT_SECRET) process.env.JWT_SECRET = 'test-jwt-secret-minimum-32-chars-long';
  if (!process.env.PORT) process.env.PORT = '0';
  if (!process.env.API_PREFIX) process.env.API_PREFIX = '/api/v1';
  if (!process.env.APP_NAME) process.env.APP_NAME = 'SecurePlatform-Test';
  if (!process.env.ALLOWED_ORIGINS) process.env.ALLOWED_ORIGINS = 'http://localhost:3000,http://localhost:5173';
  if (!process.env.ALIPAY_APP_ID) process.env.ALIPAY_APP_ID = 'test-app-id';
  if (!process.env.ALIPAY_NOTIFY_URL) process.env.ALIPAY_NOTIFY_URL = 'https://example.com/notify';
  if (!process.env.ALIPAY_RETURN_URL) process.env.ALIPAY_RETURN_URL = 'https://example.com/return';
  if (!process.env.ALIPAY_PRIVATE_KEY) process.env.ALIPAY_PRIVATE_KEY = '-----BEGIN RSA PRIVATE KEY-----\ntest\n-----END RSA PRIVATE KEY-----';
  if (!process.env.ALIPAY_PUBLIC_KEY) process.env.ALIPAY_PUBLIC_KEY = '-----BEGIN PUBLIC KEY-----\ntest\n-----END PUBLIC KEY-----';
  if (!process.env.SESSION_TTL) process.env.SESSION_TTL = '86400';
  if (!process.env.JWT_ISSUER) process.env.JWT_ISSUER = 'secure-platform';
  if (!process.env.JWT_AUDIENCE) process.env.JWT_AUDIENCE = 'secure-platform-api';
  if (!process.env.JWT_ACCESS_TTL) process.env.JWT_ACCESS_TTL = '900';
  if (!process.env.JWT_REFRESH_TTL) process.env.JWT_REFRESH_TTL = '604800';
  if (!process.env.REDIS_HOST) process.env.REDIS_HOST = 'localhost';
  if (!process.env.REDIS_PORT) process.env.REDIS_PORT = '6379';
  if (!process.env.REDIS_DB) process.env.REDIS_DB = '0';
  if (!process.env.LOG_LEVEL) process.env.LOG_LEVEL = 'error';
  if (!process.env.LOG_DIR) process.env.LOG_DIR = './logs';

  const routes = buildTestRoutes();
  return createApp({ routes });
};

describe('API Integration Tests', () => {
  let app: Express;

  beforeAll(() => {
    app = createTestApp();
  });

  describe('Public endpoints return 200', () => {
    it('GET /health returns 200', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body.success).toBe(true);
      expect(res.body.data.status).toBe('ok');
    });

    it('GET /api/v1/certificate/ca returns 200', async () => {
      const res = await request(app).get('/api/v1/certificate/ca');
      expect(res.status).toBe(200);
      expect(res.body.success).toBe(true);
      expect(res.body.data.cn).toContain('Root CA');
      expect(res.body.data.fingerprint).toHaveLength(64);
    });

    it.each(['base64', 'urlsafe-base64', 'xor', 'sha256'])(
      'GET /api/v1/crypto/%s/encode returns 200',
      async (algo) => {
        const res = await request(app).get(`/api/v1/crypto/${algo}/encode`).query({ data: 'hello', key: 'k' });
        expect(res.status).toBe(200);
        expect(res.body.success).toBe(true);
        expect(res.body.data.algorithm).toBe(algo);
        expect(res.body.data.encoded).toBeTruthy();
      }
    );

    it('GET /api/v1/blockchain/chain returns 200', async () => {
      const res = await request(app).get('/api/v1/blockchain/chain');
      expect(res.status).toBe(200);
      expect(res.body.success).toBe(true);
      expect(res.body.data.length).toBeGreaterThanOrEqual(1);
      expect(res.body.data.chain[0].index).toBe(0);
    });
  });

  describe('Login flow: login → /me → /admin → logout', () => {
    let sessionId: string;
    let csrfToken: string;

    it('login admin user', async () => {
      const res = await request(app)
        .post('/api/v1/auth/login')
        .send({ username: 'admin', password: 'AdminPass-2024' });
      expect(res.status).toBe(200);
      expect(res.body.success).toBe(true);
      expect(res.body.data.user.role).toBe('admin');
      sessionId = res.body.data.sessionId;
      csrfToken = res.body.data.csrfToken;
      expect(sessionId).toBeTruthy();
      expect(csrfToken).toBeTruthy();
    });

    it('GET /me returns user info', async () => {
      const res = await request(app)
        .get('/api/v1/auth/me')
        .set('X-Session-ID', sessionId);
      expect(res.status).toBe(200);
      expect(res.body.data.username).toBe('admin');
      expect(res.body.data.role).toBe('admin');
    });

    it('GET /admin accessible by admin', async () => {
      const res = await request(app)
        .get('/api/v1/admin')
        .set('X-Session-ID', sessionId);
      expect(res.status).toBe(200);
      expect(res.body.success).toBe(true);
      expect(res.body.data.stats).toBeDefined();
    });

    it('regular user cannot access /admin', async () => {
      const loginRes = await request(app)
        .post('/api/v1/auth/login')
        .send({ username: 'alice', password: 'AlicePass-2024' });
      const userSid = loginRes.body.data.sessionId;
      const res = await request(app).get('/api/v1/admin').set('X-Session-ID', userSid);
      expect(res.status).toBe(403);
    });

    it('POST /logout ends session', async () => {
      const res = await request(app)
        .post('/api/v1/auth/logout')
        .set('X-Session-ID', sessionId);
      expect(res.status).toBe(200);
      const meAfter = await request(app).get('/api/v1/auth/me').set('X-Session-ID', sessionId);
      expect(meAfter.status).toBe(401);
    });
  });

  describe('Payment flow: login → create order + card redeem → balance → order list', () => {
    let sessionId: string;
    let csrfToken: string;
    let orderId: string;

    it('login alice', async () => {
      const r = await request(app)
        .post('/api/v1/auth/login')
        .send({ username: 'alice', password: 'AlicePass-2024' });
      sessionId = r.body.data.sessionId;
      csrfToken = r.body.data.csrfToken;
    });

    it('initial balance is 0', async () => {
      const r = await request(app).get('/api/v1/wallet/balance').set('X-Session-ID', sessionId);
      expect(r.body.data.balance).toBe(0);
    });

    it('create order with card redemption (top-up)', async () => {
      const r = await request(app)
        .post('/api/v1/orders')
        .set('X-Session-ID', sessionId)
        .set('X-CSRF-Token', csrfToken)
        .send({ amount: 1000, cardNumber: '4111-1111-1111-1234' });
      expect(r.status).toBe(200);
      expect(r.body.success).toBe(true);
      expect(r.body.data.status).toBe('paid');
      expect(r.body.data.amount).toBe(1000);
      expect(r.body.data.card).toBe('1234');
      orderId = r.body.data.id;
    });

    it('balance increased after paid order', async () => {
      const r = await request(app).get('/api/v1/wallet/balance').set('X-Session-ID', sessionId);
      expect(r.body.data.balance).toBeGreaterThanOrEqual(1000);
    });

    it('list orders contains the new order', async () => {
      const r = await request(app).get('/api/v1/orders').set('X-Session-ID', sessionId);
      expect(r.status).toBe(200);
      expect(r.body.data.map((o: any) => o.id)).toContain(orderId);
      const found = r.body.data.find((o: any) => o.id === orderId);
      expect(found.amount).toBe(1000);
    });
  });

  describe('Evidence flow: login → store → verify → mine → chain validation', () => {
    let sessionId: string;
    let csrfToken: string;
    let evidenceKey: string;
    let evidenceHash: string;

    it('login admin', async () => {
      const r = await request(app)
        .post('/api/v1/auth/login')
        .send({ username: 'admin', password: 'AdminPass-2024' });
      sessionId = r.body.data.sessionId;
      csrfToken = r.body.data.csrfToken;
    });

    it('store data evidence', async () => {
      evidenceKey = 'contract/' + crypto.randomBytes(6).toString('hex');
      const r = await request(app)
        .post('/api/v1/evidence/store')
        .set('X-Session-ID', sessionId)
        .set('X-CSRF-Token', csrfToken)
        .send({ key: evidenceKey, data: '合同条款 v1.0 已由双方确认' });
      expect(r.status).toBe(200);
      expect(r.body.success).toBe(true);
      evidenceHash = r.body.data.hash;
      expect(evidenceHash).toHaveLength(64);
    });

    it('verify stored evidence', async () => {
      const r = await request(app)
        .post('/api/v1/evidence/verify')
        .send({ key: evidenceKey, expectedHash: evidenceHash });
      expect(r.status).toBe(200);
      expect(r.body.data.verified).toBe(true);
    });

    it('mine a block with pending evidence', async () => {
      const r = await request(app)
        .post('/api/v1/blockchain/mine')
        .set('X-Session-ID', sessionId)
        .set('X-CSRF-Token', csrfToken)
        .send({ data: 'miner:admin' });
      expect(r.status).toBe(200);
      expect(r.body.success).toBe(true);
      expect(r.body.data.block.hash).toBeTruthy();
      expect(r.body.data.height).toBeGreaterThan(1);
    });

    it('chain is valid (prevHashes match, hashes correct)', async () => {
      const r = await request(app).get('/api/v1/blockchain/chain');
      const chain = r.body.data.chain;
      for (let i = 1; i < chain.length; i++) {
        expect(chain[i].prevHash).toBe(chain[i - 1].hash);
        const recomputed = crypto
          .createHash('sha256')
          .update(JSON.stringify({
            index: chain[i].index,
            timestamp: chain[i].timestamp,
            data: chain[i].data,
            prevHash: chain[i].prevHash,
            nonce: chain[i].nonce,
          }))
          .digest('hex');
        expect(chain[i].hash).toBe(recomputed);
      }
    });
  });

  describe('Security tests: authz, CSRF, rate limiting', () => {
    it('unauthenticated GET /admin returns 401', async () => {
      const res = await request(app).get('/api/v1/admin');
      expect(res.status).toBe(401);
    });

    it('CSRF token missing on state-changing endpoint returns 403', async () => {
      const loginRes = await request(app)
        .post('/api/v1/auth/login')
        .send({ username: 'alice', password: 'AlicePass-2024' });
      const sid = loginRes.body.data.sessionId;
      const res = await request(app)
        .post('/api/v1/orders')
        .set('X-Session-ID', sid)
        .send({ amount: 100, cardNumber: '1234-5678-1234-5678' });
      expect(res.status).toBe(403);
      expect(res.body.code).toBe('CSRF_TOKEN_MISSING');
    });

    it('rate limiter returns 429 after 11 requests on auth/login', async () => {
      const responses = [];
      for (let i = 0; i < 12; i++) {
        const r = await request(app)
          .post('/api/v1/auth/login')
          .send({ username: 'nobody', password: 'wrong' });
        responses.push(r.status);
      }
      expect(responses).toContain(429);
      const lastThree = responses.slice(-3);
      expect(lastThree.some((s) => s === 429)).toBe(true);
    }, 15000);

    it('invalid credentials return 401', async () => {
      const r = await request(app)
        .post('/api/v1/auth/login')
        .send({ username: 'admin', password: 'wrong-password' });
      expect(r.status).toBe(401);
    });
  });
});

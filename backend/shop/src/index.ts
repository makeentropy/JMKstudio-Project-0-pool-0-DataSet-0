import express from 'express';
import cors from 'cors';
import { createBaseXORPool } from '@basexor/shared';
import { shopDB } from './db';

const PORT = process.env.SHOP_PORT || 3002;
const API_TOKEN = process.env.API_TOKEN || 'baseXOR_jmk_api_token_2026';
const CARD_EXPIRE_DAYS = 365;

const app = express();
const xorPool = createBaseXORPool(API_TOKEN);

app.use(cors());
app.use(express.json());

app.get('/health', (req, res) => {
  res.json({ status: 'ok', service: 'Shop-API.bin', timestamp: xorPool.timestamp() });
});

app.post('/order/create', (req, res) => {
  const { price, subject, sign } = req.body;

  const verifyResult = xorPool.verifyTag(sign);
  if (!verifyResult.valid) {
    return res.status(401).json({ code: 401, msg: 'invalid sign' });
  }

  const orderId = xorPool.genUuid();
  const orderSign = xorPool.signTag(orderId, xorPool.timestamp() + 86400);

  shopDB.insertOrder({
    order_id: orderId,
    price: price || '29.90',
    subject: subject || 'theme_premium',
    status: 'wait_pay',
    created_at: xorPool.timestamp(),
  });

  res.json({
    order_id: orderId,
    pay_url: `/pay/${orderId}`,
    sign: orderSign,
  });
});

app.post('/order/callback', (req, res) => {
  const { order_id, trade_no, sign } = req.body;

  const verifyResult = xorPool.verifyTag(sign);
  if (!verifyResult.valid) {
    return res.status(401).json({ code: 401, msg: 'invalid sign' });
  }

  const order = shopDB.getOrder(order_id);
  if (!order) {
    return res.status(404).json({ code: 404, msg: 'order not found' });
  }

  if (order.status === 'paid') {
    return res.json({
      code: 0,
      msg: 'already paid',
      card_key: order.card_key,
    });
  }

  shopDB.updateOrderStatus(order_id, 'paid');

  const cardKey = xorPool.genRandomStr(32);
  const expireAt = xorPool.timestamp() + CARD_EXPIRE_DAYS * 86400;

  shopDB.insertCard({
    card_key: cardKey,
    status: 'unused',
    expire_at: expireAt,
    created_at: xorPool.timestamp(),
  });

  shopDB.setOrderCardKey(order_id, cardKey);

  res.json({
    code: 0,
    msg: 'success',
    card_key: cardKey,
  });
});

app.post('/card/verify', (req, res) => {
  const { card_key } = req.body;

  const card = shopDB.getCard(card_key);
  if (!card) {
    return res.json({ valid: false, msg: 'card not found' });
  }

  if (card.status !== 'unused') {
    return res.json({ valid: false, msg: 'card already used' });
  }

  if (xorPool.timestamp() > card.expire_at) {
    return res.json({ valid: false, msg: 'card expired' });
  }

  const tagAuth = xorPool.signTag('theme_premium', card.expire_at);
  shopDB.useCard(card_key);

  res.json({
    valid: true,
    tag_auth: tagAuth,
    expire_at: card.expire_at,
  });
});

app.get('/admin/stats', (req, res) => {
  const authHeader = req.headers['x-jmk-auth'] as string;
  const verifyResult = xorPool.verifyTag(authHeader);
  if (!verifyResult.valid || verifyResult.tagId !== 'admin_upload') {
    return res.status(403).json({ code: 403, msg: 'Forbidden' });
  }

  res.json({
    orders_count: shopDB.getAllOrders().length,
    cards_total: shopDB.getAllCards().length,
    cards_used: shopDB.getAllCards().filter(c => c.status === 'used').length,
    cards_unused: shopDB.getAllCards().filter(c => c.status === 'unused').length,
  });
});

app.post('/admin/card/import', (req, res) => {
  const authHeader = req.headers['x-jmk-auth'] as string;
  const verifyResult = xorPool.verifyTag(authHeader);
  if (!verifyResult.valid || verifyResult.tagId !== 'admin_upload') {
    return res.status(403).json({ code: 403, msg: 'Forbidden' });
  }

  const { cards } = req.body;
  if (!Array.isArray(cards)) {
    return res.status(400).json({ code: 400, msg: 'invalid cards format' });
  }

  const now = xorPool.timestamp();
  const count = shopDB.batchImportCards(
    cards.map((cardKey: string) => ({
      card_key: cardKey,
      status: 'unused' as const,
      expire_at: now + CARD_EXPIRE_DAYS * 86400,
    }))
  );

  res.json({ code: 0, msg: 'success', imported: count });
});

app.listen(PORT, () => {
  console.log(`[INFO] Shop-API.bin started on port ${PORT}`);
  console.log(`[INFO] BaseXOR pool initialized`);
});

"use strict";
var __importDefault = (this && this.__importDefault) || function (mod) {
    return (mod && mod.__esModule) ? mod : { "default": mod };
};
Object.defineProperty(exports, "__esModule", { value: true });
const express_1 = __importDefault(require("express"));
const cors_1 = __importDefault(require("cors"));
const shared_1 = require("@basexor/shared");
const db_1 = require("./db");
const PORT = process.env.SHOP_PORT || 3002;
const API_TOKEN = process.env.API_TOKEN || 'baseXOR_jmk_api_token_2026';
const CARD_EXPIRE_DAYS = 365;
const app = (0, express_1.default)();
const xorPool = (0, shared_1.createBaseXORPool)(API_TOKEN);
app.use((0, cors_1.default)());
app.use(express_1.default.json());
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
    db_1.shopDB.insertOrder({
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
    const order = db_1.shopDB.getOrder(order_id);
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
    db_1.shopDB.updateOrderStatus(order_id, 'paid');
    const cardKey = xorPool.genRandomStr(32);
    const expireAt = xorPool.timestamp() + CARD_EXPIRE_DAYS * 86400;
    db_1.shopDB.insertCard({
        card_key: cardKey,
        status: 'unused',
        expire_at: expireAt,
        created_at: xorPool.timestamp(),
    });
    db_1.shopDB.setOrderCardKey(order_id, cardKey);
    res.json({
        code: 0,
        msg: 'success',
        card_key: cardKey,
    });
});
app.post('/card/verify', (req, res) => {
    const { card_key } = req.body;
    const card = db_1.shopDB.getCard(card_key);
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
    db_1.shopDB.useCard(card_key);
    res.json({
        valid: true,
        tag_auth: tagAuth,
        expire_at: card.expire_at,
    });
});
app.get('/admin/stats', (req, res) => {
    const authHeader = req.headers['x-jmk-auth'];
    const verifyResult = xorPool.verifyTag(authHeader);
    if (!verifyResult.valid || verifyResult.tagId !== 'admin_upload') {
        return res.status(403).json({ code: 403, msg: 'Forbidden' });
    }
    res.json({
        orders_count: db_1.shopDB.getAllOrders().length,
        cards_total: db_1.shopDB.getAllCards().length,
        cards_used: db_1.shopDB.getAllCards().filter(c => c.status === 'used').length,
        cards_unused: db_1.shopDB.getAllCards().filter(c => c.status === 'unused').length,
    });
});
app.post('/admin/card/import', (req, res) => {
    const authHeader = req.headers['x-jmk-auth'];
    const verifyResult = xorPool.verifyTag(authHeader);
    if (!verifyResult.valid || verifyResult.tagId !== 'admin_upload') {
        return res.status(403).json({ code: 403, msg: 'Forbidden' });
    }
    const { cards } = req.body;
    if (!Array.isArray(cards)) {
        return res.status(400).json({ code: 400, msg: 'invalid cards format' });
    }
    const now = xorPool.timestamp();
    const count = db_1.shopDB.batchImportCards(cards.map((cardKey) => ({
        card_key: cardKey,
        status: 'unused',
        expire_at: now + CARD_EXPIRE_DAYS * 86400,
    })));
    res.json({ code: 0, msg: 'success', imported: count });
});
app.listen(PORT, () => {
    console.log(`[INFO] Shop-API.bin started on port ${PORT}`);
    console.log(`[INFO] BaseXOR pool initialized`);
});

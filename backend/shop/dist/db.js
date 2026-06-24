"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.shopDB = exports.ShopDB = void 0;
class ShopDB {
    constructor() {
        this.orders = new Map();
        this.cards = new Map();
    }
    insertOrder(order) {
        this.orders.set(order.order_id, order);
    }
    getOrder(orderId) {
        return this.orders.get(orderId);
    }
    updateOrderStatus(orderId, status) {
        const order = this.orders.get(orderId);
        if (!order)
            return false;
        order.status = status;
        return true;
    }
    setOrderCardKey(orderId, cardKey) {
        const order = this.orders.get(orderId);
        if (!order)
            return false;
        order.card_key = cardKey;
        return true;
    }
    insertCard(card) {
        this.cards.set(card.card_key, card);
    }
    getCard(cardKey) {
        return this.cards.get(cardKey);
    }
    useCard(cardKey) {
        const card = this.cards.get(cardKey);
        if (!card || card.status !== 'unused')
            return false;
        card.status = 'used';
        card.used_at = Math.floor(Date.now() / 1000);
        return true;
    }
    batchImportCards(cardList) {
        const now = Math.floor(Date.now() / 1000);
        let count = 0;
        for (const card of cardList) {
            if (!this.cards.has(card.card_key)) {
                this.cards.set(card.card_key, { ...card, created_at: now });
                count++;
            }
        }
        return count;
    }
    getAllOrders() {
        return Array.from(this.orders.values());
    }
    getAllCards() {
        return Array.from(this.cards.values());
    }
}
exports.ShopDB = ShopDB;
exports.shopDB = new ShopDB();

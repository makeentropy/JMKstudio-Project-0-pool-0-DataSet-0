export interface Order {
  order_id: string;
  price: string;
  subject: string;
  status: 'wait_pay' | 'paid' | 'cancelled';
  created_at: number;
  card_key?: string;
}

export interface Card {
  card_key: string;
  status: 'unused' | 'used';
  expire_at: number;
  created_at: number;
  used_at?: number;
}

export class ShopDB {
  private orders: Map<string, Order> = new Map();
  private cards: Map<string, Card> = new Map();

  insertOrder(order: Order): void {
    this.orders.set(order.order_id, order);
  }

  getOrder(orderId: string): Order | undefined {
    return this.orders.get(orderId);
  }

  updateOrderStatus(orderId: string, status: Order['status']): boolean {
    const order = this.orders.get(orderId);
    if (!order) return false;
    order.status = status;
    return true;
  }

  setOrderCardKey(orderId: string, cardKey: string): boolean {
    const order = this.orders.get(orderId);
    if (!order) return false;
    order.card_key = cardKey;
    return true;
  }

  insertCard(card: Card): void {
    this.cards.set(card.card_key, card);
  }

  getCard(cardKey: string): Card | undefined {
    return this.cards.get(cardKey);
  }

  useCard(cardKey: string): boolean {
    const card = this.cards.get(cardKey);
    if (!card || card.status !== 'unused') return false;
    card.status = 'used';
    card.used_at = Math.floor(Date.now() / 1000);
    return true;
  }

  batchImportCards(cardList: Omit<Card, 'created_at'>[]): number {
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

  getAllOrders(): Order[] {
    return Array.from(this.orders.values());
  }

  getAllCards(): Card[] {
    return Array.from(this.cards.values());
  }
}

export const shopDB = new ShopDB();

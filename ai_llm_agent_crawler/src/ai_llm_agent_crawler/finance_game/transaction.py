"""
交易系统模块

提供订单管理、订单撮合、交易清算、交易验证等功能。
"""

import heapq
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from ai_llm_agent_crawler.finance_game.models import (
    Order,
    OrderBook,
    OrderBookEntry,
    OrderSide,
    OrderStatus,
    OrderType,
    Transaction,
    TransactionStatus,
    TransactionType,
)
from ai_llm_agent_crawler.finance_game.account import AccountManager, FeeStructure
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class TransactionValidator:
    """交易验证器"""

    def __init__(self, min_amount: float = 0.0001, max_amount: float = 1_000_000_000.0):
        self.min_amount = min_amount
        self.max_amount = max_amount

    def validate_order(self, order: Order, available_balance: float) -> Tuple[bool, List[str]]:
        errors = []

        if order.amount < self.min_amount:
            errors.append(f"Order amount {order.amount} below minimum {self.min_amount}")
        if order.amount > self.max_amount:
            errors.append(f"Order amount {order.amount} above maximum {self.max_amount}")

        if order.order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT):
            if order.price is None or order.price <= 0:
                errors.append("Limit orders require a valid price")

        if order.order_type == OrderType.STOP_LIMIT:
            if order.stop_price is None:
                errors.append("Stop-limit orders require a stop price")

        if order.side == OrderSide.BUY:
            notional = order.amount * (order.price or 0)
            if notional > available_balance:
                errors.append(
                    f"Insufficient balance: need {notional}, available {available_balance}"
                )

        return len(errors) == 0, errors

    def validate_transaction(self, transaction: Transaction) -> Tuple[bool, List[str]]:
        errors = []
        if transaction.amount <= 0:
            errors.append("Transaction amount must be positive")
        if not transaction.from_account_id and not transaction.to_account_id:
            errors.append("Transaction must have at least one account")
        return len(errors) == 0, errors


class OrderMatcher:
    """订单撮合引擎"""

    def __init__(self, fee_structure: Optional[FeeStructure] = None):
        self.fee_structure = fee_structure or FeeStructure()
        self._order_books: Dict[str, OrderBook] = {}
        self._buy_orders: Dict[str, List[Tuple[float, str, Order]]] = {}
        self._sell_orders: Dict[str, List[Tuple[float, str, Order]]] = {}
        self._order_index: Dict[str, Order] = {}

    def get_order_book(self, market: str) -> OrderBook:
        if market not in self._order_books:
            self._order_books[market] = OrderBook(market=market)
        return self._order_books[market]

    def add_order(self, order: Order) -> Tuple[bool, List[Transaction]]:
        if order.status != OrderStatus.PENDING:
            return False, []

        self._order_index[order.order_id] = order

        if order.order_type == OrderType.MARKET:
            return self._match_market_order(order)
        else:
            return self._add_limit_order(order)

    def _match_market_order(self, order: Order) -> Tuple[bool, List[Transaction]]:
        transactions = []
        remaining = order.amount

        if order.side == OrderSide.BUY:
            asks = self._get_sorted_asks(order.market)
            for price, _, ask_order in asks:
                if remaining <= 0:
                    break
                fill_amount = min(remaining, ask_order.remaining_amount)
                txn = self._execute_trade(order, ask_order, price, fill_amount, taker_is_buyer=True)
                if txn:
                    transactions.append(txn)
                    remaining -= fill_amount
        else:
            bids = self._get_sorted_bids(order.market)
            for price, _, bid_order in bids:
                if remaining <= 0:
                    break
                fill_amount = min(remaining, bid_order.remaining_amount)
                txn = self._execute_trade(bid_order, order, price, fill_amount, taker_is_buyer=False)
                if txn:
                    transactions.append(txn)
                    remaining -= fill_amount

        order.filled_amount = order.amount - remaining
        if remaining == 0:
            order.status = OrderStatus.FILLED
        else:
            order.status = OrderStatus.PARTIALLY_FILLED

        order.updated_at = datetime.now()
        self._update_order_book(order.market)
        return True, transactions

    def _add_limit_order(self, order: Order) -> Tuple[bool, List[Transaction]]:
        transactions = []
        remaining = order.amount

        if order.side == OrderSide.BUY:
            asks = self._get_sorted_asks(order.market)
            for price, _, ask_order in asks:
                if remaining <= 0 or price > order.price:
                    break
                fill_amount = min(remaining, ask_order.remaining_amount)
                txn = self._execute_trade(order, ask_order, price, fill_amount, taker_is_buyer=True)
                if txn:
                    transactions.append(txn)
                    remaining -= fill_amount
        else:
            bids = self._get_sorted_bids(order.market)
            for price, _, bid_order in bids:
                if remaining <= 0 or price < order.price:
                    break
                fill_amount = min(remaining, bid_order.remaining_amount)
                txn = self._execute_trade(bid_order, order, price, fill_amount, taker_is_buyer=False)
                if txn:
                    transactions.append(txn)
                    remaining -= fill_amount

        order.filled_amount = order.amount - remaining

        if remaining > 0:
            order.status = OrderStatus.OPEN if order.filled_amount == 0 else OrderStatus.PARTIALLY_FILLED
            self._insert_into_book(order)
        else:
            order.status = OrderStatus.FILLED

        order.updated_at = datetime.now()
        self._update_order_book(order.market)
        return True, transactions

    def _execute_trade(
        self,
        buy_order: Order,
        sell_order: Order,
        price: float,
        amount: float,
        taker_is_buyer: bool,
    ) -> Optional[Transaction]:
        if amount <= 0:
            return None

        buy_order.filled_amount += amount
        sell_order.filled_amount += amount

        if buy_order.filled_amount >= buy_order.amount:
            buy_order.status = OrderStatus.FILLED
        else:
            buy_order.status = OrderStatus.PARTIALLY_FILLED

        if sell_order.filled_amount >= sell_order.amount:
            sell_order.status = OrderStatus.FILLED
        else:
            sell_order.status = OrderStatus.PARTIALLY_FILLED

        buy_order.avg_fill_price = self._calc_avg_price(buy_order, price, amount)
        sell_order.avg_fill_price = self._calc_avg_price(sell_order, price, amount)

        buy_order.updated_at = datetime.now()
        sell_order.updated_at = datetime.now()

        notional = price * amount
        taker_fee = self.fee_structure.calculate_trade_fee(amount, price, is_maker=False)
        maker_fee = self.fee_structure.calculate_trade_fee(amount, price, is_maker=True)

        transaction = Transaction(
            transaction_type=TransactionType.TRADE_BUY if taker_is_buyer else TransactionType.TRADE_SELL,
            status=TransactionStatus.COMPLETED,
            from_account_id=sell_order.account_id,
            to_account_id=buy_order.account_id,
            amount=amount,
            currency=type("C", (), {"value": "BASE"})(),
            fee=taker_fee + maker_fee,
            description=f"Trade: {amount} @ {price}",
            reference_id=str(uuid.uuid4()),
            metadata={
                "buy_order_id": buy_order.order_id,
                "sell_order_id": sell_order.order_id,
                "price": price,
                "taker_is_buyer": taker_is_buyer,
                "maker_fee": maker_fee,
                "taker_fee": taker_fee,
            },
        )

        return transaction

    def _calc_avg_price(self, order: Order, price: float, amount: float) -> float:
        prev_total = order.avg_fill_price * (order.filled_amount - amount)
        new_total = price * amount
        if order.filled_amount == 0:
            return price
        return (prev_total + new_total) / order.filled_amount

    def _insert_into_book(self, order: Order) -> None:
        if order.market not in self._buy_orders:
            self._buy_orders[order.market] = []
            self._sell_orders[order.market] = []

        timestamp = datetime.now().timestamp()
        if order.side == OrderSide.BUY:
            heapq.heappush(
                self._buy_orders[order.market],
                (-order.price, timestamp, order),
            )
        else:
            heapq.heappush(
                self._sell_orders[order.market],
                (order.price, timestamp, order),
            )

    def _get_sorted_bids(self, market: str) -> List[Tuple[float, float, Order]]:
        if market not in self._buy_orders:
            return []
        orders = []
        temp = list(self._buy_orders[market])
        while temp:
            neg_price, ts, order = heapq.heappop(temp)
            if order.is_active:
                orders.append((-neg_price, ts, order))
        return orders

    def _get_sorted_asks(self, market: str) -> List[Tuple[float, float, Order]]:
        if market not in self._sell_orders:
            return []
        orders = []
        temp = list(self._sell_orders[market])
        while temp:
            price, ts, order = heapq.heappop(temp)
            if order.is_active:
                orders.append((price, ts, order))
        return orders

    def _update_order_book(self, market: str) -> None:
        book = self.get_order_book(market)
        book.timestamp = datetime.now()

        bid_levels: Dict[float, Tuple[float, int]] = {}
        for _, _, order in self._get_sorted_bids(market):
            if not order.is_active:
                continue
            price = order.price or 0
            current = bid_levels.get(price, (0.0, 0))
            bid_levels[price] = (current[0] + order.remaining_amount, current[1] + 1)

        ask_levels: Dict[float, Tuple[float, int]] = {}
        for _, _, order in self._get_sorted_asks(market):
            if not order.is_active:
                continue
            price = order.price or 0
            current = ask_levels.get(price, (0.0, 0))
            ask_levels[price] = (current[0] + order.remaining_amount, current[1] + 1)

        book.bids = [
            OrderBookEntry(price=p, amount=a, order_count=c)
            for p, (a, c) in sorted(bid_levels.items(), reverse=True)[:20]
        ]
        book.asks = [
            OrderBookEntry(price=p, amount=a, order_count=c)
            for p, (a, c) in sorted(ask_levels.items())[:20]
        ]

        if book.bids and book.asks:
            book.last_price = (book.bids[0].price + book.asks[0].price) / 2

    def cancel_order(self, order_id: str) -> bool:
        order = self._order_index.get(order_id)
        if not order or not order.is_active:
            return False
        order.status = OrderStatus.CANCELLED
        order.updated_at = datetime.now()
        self._update_order_book(order.market)
        return True

    def get_order(self, order_id: str) -> Optional[Order]:
        return self._order_index.get(order_id)

    def get_market_price(self, market: str) -> Optional[float]:
        book = self.get_order_book(market)
        return book.get_mid_price()


class SettlementEngine:
    """清算引擎"""

    def __init__(self, account_manager: AccountManager):
        self.account_manager = account_manager
        self._pending_settlements: List[Transaction] = []
        self.logger = get_logger(f"{__name__}.SettlementEngine")

    def settle_transaction(self, transaction: Transaction) -> bool:
        if transaction.status != TransactionStatus.COMPLETED:
            return False

        if transaction.from_account_id and transaction.to_account_id:
            currency = transaction.currency.value if hasattr(transaction.currency, 'value') else str(transaction.currency)
            result, _ = self.account_manager.transfer(
                from_account_id=transaction.from_account_id,
                to_account_id=transaction.to_account_id,
                currency=currency,
                amount=transaction.amount,
                description=transaction.description,
            )
            return result

        return True

    def settle_batch(self, transactions: List[Transaction]) -> Tuple[int, int]:
        success_count = 0
        fail_count = 0
        for txn in transactions:
            if self.settle_transaction(txn):
                success_count += 1
            else:
                fail_count += 1
        return success_count, fail_count


class TransactionEngine:
    """交易引擎 - 整合订单撮合、验证和清算"""

    def __init__(
        self,
        account_manager: Optional[AccountManager] = None,
        fee_structure: Optional[FeeStructure] = None,
    ):
        self.account_manager = account_manager or AccountManager(fee_structure=fee_structure)
        self.fee_structure = fee_structure or FeeStructure()
        self.validator = TransactionValidator()
        self.matcher = OrderMatcher(fee_structure=self.fee_structure)
        self.settlement = SettlementEngine(self.account_manager)
        self.logger = get_logger(f"{__name__}.TransactionEngine")

    def place_order(self, order: Order) -> Tuple[bool, List[Transaction], List[str]]:
        errors = []

        account = self.account_manager.ledger.get_account(order.account_id)
        if not account:
            errors.append("Account not found")
            return False, [], errors

        currency = "USD"
        available = account.get_available_balance(currency)
        if order.side == OrderSide.BUY and order.order_type != OrderType.MARKET and order.price:
            required = order.amount * order.price
            if not account.freeze(currency, required):
                errors.append("Failed to freeze balance")
                return False, [], errors

        valid, validation_errors = self.validator.validate_order(order, available)
        if not valid:
            errors.extend(validation_errors)
            return False, [], errors

        success, transactions = self.matcher.add_order(order)
        if success and transactions:
            for txn in transactions:
                self.settlement.settle_transaction(txn)

        return success, transactions, errors

    def cancel_order(self, order_id: str) -> bool:
        order = self.matcher.get_order(order_id)
        if not order:
            return False

        success = self.matcher.cancel_order(order_id)
        if success:
            currency = "USD"
            account = self.account_manager.ledger.get_account(order.account_id)
            if account and order.side == OrderSide.BUY:
                remaining_value = order.remaining_amount * (order.price or 0)
                account.unfreeze(currency, remaining_value)

        return success

    def get_order_book(self, market: str) -> OrderBook:
        return self.matcher.get_order_book(market)

    def get_market_price(self, market: str) -> Optional[float]:
        return self.matcher.get_market_price(market)

    def get_order(self, order_id: str) -> Optional[Order]:
        return self.matcher.get_order(order_id)

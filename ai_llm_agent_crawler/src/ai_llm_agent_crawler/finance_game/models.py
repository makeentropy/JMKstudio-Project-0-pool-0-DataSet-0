"""
金融游戏核心数据模型

定义账户、交易、订单、区块、市场、投资组合等核心数据结构。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class AccountType(str, Enum):
    """账户类型枚举"""
    MAIN = "main"
    SAVINGS = "savings"
    TRADING = "trading"
    MARGIN = "margin"
    INVESTMENT = "investment"
    REWARD = "reward"
    MINING = "mining"


class TransactionType(str, Enum):
    """交易类型枚举"""
    DEPOSIT = "deposit"
    WITHDRAWAL = "withdrawal"
    TRANSFER = "transfer"
    TRADE_BUY = "trade_buy"
    TRADE_SELL = "trade_sell"
    FEE = "fee"
    INTEREST = "interest"
    DIVIDEND = "dividend"
    REWARD = "reward"
    MINING = "mining"
    STAKING = "staking"


class TransactionStatus(str, Enum):
    """交易状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    REVERSED = "reversed"


class OrderType(str, Enum):
    """订单类型枚举"""
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"
    ICEBERG = "iceberg"


class OrderSide(str, Enum):
    """订单方向枚举"""
    BUY = "buy"
    SELL = "sell"


class OrderStatus(str, Enum):
    """订单状态枚举"""
    PENDING = "pending"
    OPEN = "open"
    PARTIALLY_FILLED = "partially_filled"
    FILLED = "filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"


class BlockStatus(str, Enum):
    """区块状态枚举"""
    PENDING = "pending"
    PROPOSED = "proposed"
    VALIDATED = "validated"
    FINALIZED = "finalized"
    ORPHANED = "orphaned"


class MarketType(str, Enum):
    """市场类型枚举"""
    SPOT = "spot"
    FUTURES = "futures"
    OPTIONS = "options"
    MARGIN = "margin"
    STAKING = "staking"


class AssetClass(str, Enum):
    """资产类别枚举"""
    CASH = "cash"
    EQUITY = "equity"
    BOND = "bond"
    COMMODITY = "commodity"
    CRYPTO = "crypto"
    DERIVATIVE = "derivative"
    REAL_ESTATE = "real_estate"
    ETF = "etf"


class RiskLevel(str, Enum):
    """风险等级枚举"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    SPECULATIVE = "speculative"


class Currency(str, Enum):
    """货币枚举"""
    USD = "USD"
    CNY = "CNY"
    EUR = "EUR"
    JPY = "JPY"
    GBP = "GBP"
    BTC = "BTC"
    ETH = "ETH"
    GAME_COIN = "GAME"


class Money(BaseModel):
    """金额模型"""
    amount: float = Field(default=0.0, ge=0.0)
    currency: Currency = Field(default=Currency.USD)

    def __add__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(f"Currency mismatch: {self.currency} vs {other.currency}")
        return Money(amount=self.amount + other.amount, currency=self.currency)

    def __sub__(self, other: "Money") -> "Money":
        if self.currency != other.currency:
            raise ValueError(f"Currency mismatch: {self.currency} vs {other.currency}")
        return Money(amount=max(0, self.amount - other.amount), currency=self.currency)

    def __mul__(self, factor: float) -> "Money":
        return Money(amount=self.amount * factor, currency=self.currency)


class Account(BaseModel):
    """账户模型"""
    account_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    account_type: AccountType = Field(default=AccountType.MAIN)
    name: str = Field(default="")
    balances: Dict[str, float] = Field(default_factory=dict)
    frozen_balances: Dict[str, float] = Field(default_factory=dict)
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_available_balance(self, currency: str) -> float:
        total = self.balances.get(currency, 0.0)
        frozen = self.frozen_balances.get(currency, 0.0)
        return max(0.0, total - frozen)

    def get_total_balance(self, currency: str) -> float:
        return self.balances.get(currency, 0.0)

    def deposit(self, currency: str, amount: float) -> None:
        if amount <= 0:
            raise ValueError("Deposit amount must be positive")
        self.balances[currency] = self.balances.get(currency, 0.0) + amount
        self.updated_at = datetime.now()

    def withdraw(self, currency: str, amount: float) -> bool:
        if amount <= 0:
            return False
        available = self.get_available_balance(currency)
        if available < amount:
            return False
        self.balances[currency] -= amount
        self.updated_at = datetime.now()
        return True

    def freeze(self, currency: str, amount: float) -> bool:
        if self.get_available_balance(currency) < amount:
            return False
        self.frozen_balances[currency] = self.frozen_balances.get(currency, 0.0) + amount
        self.updated_at = datetime.now()
        return True

    def unfreeze(self, currency: str, amount: float) -> bool:
        frozen = self.frozen_balances.get(currency, 0.0)
        if frozen < amount:
            return False
        self.frozen_balances[currency] -= amount
        self.updated_at = datetime.now()
        return True


class Transaction(BaseModel):
    """交易记录模型"""
    transaction_id: str = Field(default_factory=lambda: str(uuid4()))
    transaction_type: TransactionType
    status: TransactionStatus = Field(default=TransactionStatus.PENDING)
    from_account_id: Optional[str] = None
    to_account_id: Optional[str] = None
    amount: float = Field(gt=0)
    currency: Currency
    fee: float = Field(default=0.0, ge=0.0)
    description: str = Field(default="")
    reference_id: Optional[str] = None
    block_height: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Order(BaseModel):
    """订单模型"""
    order_id: str = Field(default_factory=lambda: str(uuid4()))
    user_id: str
    account_id: str
    market: str
    order_type: OrderType
    side: OrderSide
    status: OrderStatus = Field(default=OrderStatus.PENDING)
    price: Optional[float] = None
    amount: float = Field(gt=0)
    filled_amount: float = Field(default=0.0, ge=0.0)
    avg_fill_price: float = Field(default=0.0)
    stop_price: Optional[float] = None
    iceberg_amount: Optional[float] = None
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    expires_at: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("price")
    @classmethod
    def check_price_for_limit(cls, v: Optional[float], info: Any) -> Optional[float]:
        order_type = info.data.get("order_type")
        if order_type in (OrderType.LIMIT, OrderType.STOP_LIMIT) and v is None:
            raise ValueError("Limit orders require a price")
        return v

    @property
    def remaining_amount(self) -> float:
        return max(0.0, self.amount - self.filled_amount)

    @property
    def is_active(self) -> bool:
        return self.status in (OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED)


class OrderBookEntry(BaseModel):
    """订单簿条目"""
    price: float
    amount: float
    order_count: int = Field(default=1)


class OrderBook(BaseModel):
    """订单簿模型"""
    market: str
    bids: List[OrderBookEntry] = Field(default_factory=list)
    asks: List[OrderBookEntry] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=datetime.now)
    last_price: float = Field(default=0.0)
    volume_24h: float = Field(default=0.0)

    def get_best_bid(self) -> Optional[float]:
        return self.bids[0].price if self.bids else None

    def get_best_ask(self) -> Optional[float]:
        return self.asks[0].price if self.asks else None

    def get_mid_price(self) -> Optional[float]:
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid and best_ask:
            return (best_bid + best_ask) / 2
        return best_bid or best_ask

    def get_spread(self) -> Optional[float]:
        best_bid = self.get_best_bid()
        best_ask = self.get_best_ask()
        if best_bid and best_ask:
            return best_ask - best_bid
        return None


class BlockHeader(BaseModel):
    """区块头模型"""
    version: int = Field(default=1)
    height: int = Field(ge=0)
    previous_hash: str = Field(default="")
    merkle_root: str = Field(default="")
    timestamp: datetime = Field(default_factory=datetime.now)
    difficulty: float = Field(default=1.0, ge=0.0)
    nonce: int = Field(default=0)
    miner: str = Field(default="")
    game_round: int = Field(default=0)
    entropy_seed: float = Field(default=0.0)


class GameBlock(BaseModel):
    """游戏区块模型"""
    block_hash: str = Field(default="")
    header: BlockHeader
    status: BlockStatus = Field(default=BlockStatus.PENDING)
    transactions: List[Transaction] = Field(default_factory=list)
    transaction_count: int = Field(default=0)
    game_actions: List[Dict[str, Any]] = Field(default_factory=list)
    market_snapshots: Dict[str, "MarketSnapshot"] = Field(default_factory=dict)
    reward_amount: float = Field(default=0.0)
    entropy_value: float = Field(default=0.0)
    terrain_hash: str = Field(default="")
    mind_vector: List[float] = Field(default_factory=list)
    size_bytes: int = Field(default=0)
    validation_signatures: List[str] = Field(default_factory=list)

    def calculate_merkle_root(self) -> str:
        import hashlib
        if not self.transactions:
            return hashlib.sha256(b"empty").hexdigest()
        hashes = [hashlib.sha256(t.transaction_id.encode()).hexdigest() for t in self.transactions]
        while len(hashes) > 1:
            if len(hashes) % 2 == 1:
                hashes.append(hashes[-1])
            new_hashes = []
            for i in range(0, len(hashes), 2):
                combined = hashes[i] + hashes[i + 1]
                new_hashes.append(hashlib.sha256(combined.encode()).hexdigest())
            hashes = new_hashes
        return hashes[0]

    def calculate_hash(self) -> str:
        import hashlib
        header_str = (
            f"{self.header.version}"
            f"{self.header.height}"
            f"{self.header.previous_hash}"
            f"{self.header.merkle_root}"
            f"{self.header.timestamp.isoformat()}"
            f"{self.header.difficulty}"
            f"{self.header.nonce}"
            f"{self.entropy_value}"
        )
        return hashlib.sha256(header_str.encode()).hexdigest()


class MarketData(BaseModel):
    """市场数据模型"""
    market: str
    price: float = Field(ge=0.0)
    volume_24h: float = Field(default=0.0, ge=0.0)
    high_24h: float = Field(default=0.0)
    low_24h: float = Field(default=0.0)
    open_24h: float = Field(default=0.0)
    change_24h: float = Field(default=0.0)
    change_percent_24h: float = Field(default=0.0)
    timestamp: datetime = Field(default_factory=datetime.now)


class MarketSnapshot(BaseModel):
    """市场快照模型"""
    market: str
    block_height: int
    open_price: float = Field(ge=0.0)
    close_price: float = Field(ge=0.0)
    high_price: float = Field(ge=0.0)
    low_price: float = Field(ge=0.0)
    volume: float = Field(default=0.0, ge=0.0)
    trades_count: int = Field(default=0)
    volatility: float = Field(default=0.0)
    entropy: float = Field(default=0.0)
    timestamp: datetime = Field(default_factory=datetime.now)


class Asset(BaseModel):
    """资产模型"""
    asset_id: str = Field(default_factory=lambda: str(uuid4()))
    symbol: str
    name: str
    asset_class: AssetClass
    market: str = Field(default="")
    current_price: float = Field(default=0.0)
    quantity: float = Field(default=0.0)
    avg_cost: float = Field(default=0.0)
    currency: Currency = Field(default=Currency.USD)
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def market_value(self) -> float:
        return self.current_price * self.quantity

    @property
    def cost_basis(self) -> float:
        return self.avg_cost * self.quantity

    @property
    def unrealized_pnl(self) -> float:
        return self.market_value - self.cost_basis

    @property
    def unrealized_pnl_percent(self) -> float:
        if self.cost_basis == 0:
            return 0.0
        return (self.unrealized_pnl / self.cost_basis) * 100


class Position(BaseModel):
    """持仓模型"""
    symbol: str
    side: OrderSide
    quantity: float = Field(default=0.0)
    avg_entry_price: float = Field(default=0.0)
    current_price: float = Field(default=0.0)
    leverage: float = Field(default=1.0)
    margin: float = Field(default=0.0)
    unrealized_pnl: float = Field(default=0.0)
    realized_pnl: float = Field(default=0.0)
    liquidation_price: Optional[float] = None
    opened_at: datetime = Field(default_factory=datetime.now)


class RiskMetrics(BaseModel):
    """风险指标模型"""
    portfolio_value: float = Field(default=0.0)
    total_return: float = Field(default=0.0)
    annualized_return: float = Field(default=0.0)
    volatility: float = Field(default=0.0)
    sharpe_ratio: float = Field(default=0.0)
    sortino_ratio: float = Field(default=0.0)
    max_drawdown: float = Field(default=0.0)
    max_drawdown_duration: float = Field(default=0.0)
    var_95: float = Field(default=0.0)
    var_99: float = Field(default=0.0)
    cvar_95: float = Field(default=0.0)
    beta: float = Field(default=0.0)
    alpha: float = Field(default=0.0)
    information_ratio: float = Field(default=0.0)
    calmar_ratio: float = Field(default=0.0)
    tail_ratio: float = Field(default=0.0)
    gain_loss_ratio: float = Field(default=0.0)
    profit_factor: float = Field(default=0.0)


class Portfolio(BaseModel):
    """投资组合模型"""
    portfolio_id: str = Field(default_factory=lambda: str(uuid4()))
    name: str
    user_id: str
    account_id: str
    assets: List[Asset] = Field(default_factory=list)
    positions: List[Position] = Field(default_factory=list)
    cash_balances: Dict[str, float] = Field(default_factory=dict)
    risk_level: RiskLevel = Field(default=RiskLevel.MODERATE)
    target_allocations: Dict[str, float] = Field(default_factory=dict)
    risk_metrics: RiskMetrics = Field(default_factory=RiskMetrics)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @property
    def total_value(self) -> float:
        asset_value = sum(a.market_value for a in self.assets)
        cash_value = sum(self.cash_balances.values())
        return asset_value + cash_value

    def get_asset(self, symbol: str) -> Optional[Asset]:
        for asset in self.assets:
            if asset.symbol == symbol:
                return asset
        return None

    def get_allocation(self, symbol: str) -> float:
        asset = self.get_asset(symbol)
        if not asset or self.total_value == 0:
            return 0.0
        return asset.market_value / self.total_value


class GameConfig(BaseModel):
    """游戏配置模型"""
    game_name: str = Field(default="FinanceEntropy")
    initial_balance: Dict[str, float] = Field(default_factory=lambda: {"USD": 10000.0, "GAME": 1000.0})
    block_time_seconds: int = Field(default=60, ge=1)
    max_transactions_per_block: int = Field(default=1000, ge=1)
    mining_reward_base: float = Field(default=50.0)
    mining_reward_halving_interval: int = Field(default=210000)
    fee_rate: float = Field(default=0.001, ge=0.0, le=0.1)
    interest_rate: float = Field(default=0.05)
    initial_difficulty: float = Field(default=1.0)
    difficulty_adjustment_interval: int = Field(default=2016)
    market_count: int = Field(default=10)
    max_leverage: float = Field(default=10.0)
    min_margin_ratio: float = Field(default=0.1)
    entropy_growth_rate: float = Field(default=0.01)
    terrain_dimensions: Tuple[int, int] = Field(default=(128, 128))
    mind_vector_size: int = Field(default=256)


class GameState(BaseModel):
    """游戏状态模型"""
    current_block_height: int = Field(default=0)
    current_block_hash: str = Field(default="")
    total_transactions: int = Field(default=0)
    total_value_locked: float = Field(default=0.0)
    global_entropy: float = Field(default=0.0)
    game_round: int = Field(default=0)
    active_users: int = Field(default=0)
    total_markets: int = Field(default=0)
    mining_difficulty: float = Field(default=1.0)
    last_block_time: Optional[datetime] = None
    genesis_time: datetime = Field(default_factory=datetime.now)
    market_states: Dict[str, MarketData] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)

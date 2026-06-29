"""
金融游戏核心模块

提供资金账户管理、交易系统、游戏区块、投资组合等金融游戏核心功能。

主要组件:
- 账户系统 (account): 资金账户、多币种余额、账户历史
- 交易系统 (transaction): 买卖交易、订单簿、交易撮合
- 游戏区块 (game_block): 游戏区块生成、区块验证、链上数据
- 市场系统 (market): 市场行情、价格发现、波动率计算
- 投资组合 (portfolio): 资产配置、风险收益分析、再平衡
"""

from ai_llm_agent_crawler.finance_game.models import (
    AccountType,
    TransactionType,
    TransactionStatus,
    OrderType,
    OrderSide,
    OrderStatus,
    BlockStatus,
    MarketType,
    AssetClass,
    RiskLevel,
    Currency,
    Money,
    Account,
    Transaction,
    Order,
    OrderBook,
    GameBlock,
    BlockHeader,
    MarketData,
    MarketSnapshot,
    Asset,
    Portfolio,
    Position,
    RiskMetrics,
    GameConfig,
    GameState,
)

from ai_llm_agent_crawler.finance_game.account import (
    AccountManager,
    AccountLedger,
    InterestCalculator,
    FeeStructure,
)

from ai_llm_agent_crawler.finance_game.transaction import (
    TransactionEngine,
    OrderMatcher,
    SettlementEngine,
    TransactionValidator,
)

from ai_llm_agent_crawler.finance_game.game_block import (
    GameBlockChain,
    BlockGenerator,
    BlockValidator,
    BlockRewardCalculator,
)

from ai_llm_agent_crawler.finance_game.market import (
    MarketSimulator,
    PriceEngine,
    VolatilityCalculator,
    MarketDataFeed,
)

from ai_llm_agent_crawler.finance_game.portfolio import (
    PortfolioManager,
    RiskAnalyzer,
    AssetAllocator,
    RebalancingEngine,
)

__all__ = [
    # 枚举和基础模型
    "AccountType",
    "TransactionType",
    "TransactionStatus",
    "OrderType",
    "OrderSide",
    "OrderStatus",
    "BlockStatus",
    "MarketType",
    "AssetClass",
    "RiskLevel",
    "Currency",
    "Money",
    "Account",
    "Transaction",
    "Order",
    "OrderBook",
    "GameBlock",
    "BlockHeader",
    "MarketData",
    "MarketSnapshot",
    "Asset",
    "Portfolio",
    "Position",
    "RiskMetrics",
    "GameConfig",
    "GameState",
    # 账户系统
    "AccountManager",
    "AccountLedger",
    "InterestCalculator",
    "FeeStructure",
    # 交易系统
    "TransactionEngine",
    "OrderMatcher",
    "SettlementEngine",
    "TransactionValidator",
    # 游戏区块
    "GameBlockChain",
    "BlockGenerator",
    "BlockValidator",
    "BlockRewardCalculator",
    # 市场系统
    "MarketSimulator",
    "PriceEngine",
    "VolatilityCalculator",
    "MarketDataFeed",
    # 投资组合
    "PortfolioManager",
    "RiskAnalyzer",
    "AssetAllocator",
    "RebalancingEngine",
]

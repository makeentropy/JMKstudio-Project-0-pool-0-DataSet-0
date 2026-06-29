"""
游戏区块模块

提供游戏区块生成、区块验证、链上数据管理、区块奖励计算等功能。
"""

import hashlib
import math
import random
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

from ai_llm_agent_crawler.finance_game.models import (
    BlockHeader,
    BlockStatus,
    GameBlock,
    GameConfig,
    GameState,
    MarketSnapshot,
    Transaction,
    TransactionStatus,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class BlockRewardCalculator:
    """区块奖励计算器"""

    def __init__(self, config: Optional[GameConfig] = None):
        self.config = config or GameConfig()

    def calculate_block_reward(self, block_height: int) -> float:
        halvings = block_height // self.config.mining_reward_halving_interval
        reward = self.config.mining_reward_base / (2 ** halvings)
        return max(reward, 0.00000001)

    def calculate_transaction_fees(self, transactions: List[Transaction]) -> float:
        return sum(tx.fee for tx in transactions if tx.status == TransactionStatus.COMPLETED)

    def calculate_total_reward(self, block: GameBlock) -> float:
        block_reward = self.calculate_block_reward(block.header.height)
        tx_fees = self.calculate_transaction_fees(block.transactions)
        return block_reward + tx_fees

    def calculate_entropy_bonus(self, entropy_value: float, base_reward: float) -> float:
        bonus_factor = 1.0 + (entropy_value * 0.1)
        return base_reward * bonus_factor


class BlockValidator:
    """区块验证器"""

    def __init__(self, config: Optional[GameConfig] = None):
        self.config = config or GameConfig()

    def validate_block(
        self,
        block: GameBlock,
        previous_block: Optional[GameBlock] = None,
    ) -> Tuple[bool, List[str]]:
        errors = []

        if not block.block_hash:
            calculated_hash = block.calculate_hash()
            if block.block_hash != calculated_hash:
                errors.append("Invalid block hash")

        merkle_root = block.calculate_merkle_root()
        if block.header.merkle_root and block.header.merkle_root != merkle_root:
            errors.append("Invalid merkle root")

        if len(block.transactions) > self.config.max_transactions_per_block:
            errors.append("Too many transactions in block")

        if previous_block:
            if block.header.previous_hash != previous_block.block_hash:
                errors.append("Invalid previous block hash")
            if block.header.height != previous_block.header.height + 1:
                errors.append("Invalid block height")
            if block.header.timestamp < previous_block.header.timestamp:
                errors.append("Block timestamp is before previous block")

        if block.header.difficulty < 0:
            errors.append("Invalid difficulty")

        for tx in block.transactions:
            if tx.status != TransactionStatus.COMPLETED:
                errors.append(f"Transaction {tx.transaction_id} not completed")

        return len(errors) == 0, errors

    def validate_header(self, header: BlockHeader) -> Tuple[bool, List[str]]:
        errors = []
        if header.height < 0:
            errors.append("Invalid block height")
        if header.difficulty <= 0:
            errors.append("Invalid difficulty")
        return len(errors) == 0, errors

    def validate_proof_of_work(self, block: GameBlock) -> bool:
        target = int(2 ** 256 / block.header.difficulty) if block.header.difficulty > 0 else 0
        block_hash = block.calculate_hash()
        hash_int = int(block_hash, 16)
        return hash_int < target if target > 0 else True


class BlockGenerator:
    """区块生成器"""

    def __init__(
        self,
        config: Optional[GameConfig] = None,
        reward_calculator: Optional[BlockRewardCalculator] = None,
    ):
        self.config = config or GameConfig()
        self.reward_calculator = reward_calculator or BlockRewardCalculator(self.config)
        self.logger = get_logger(f"{__name__}.BlockGenerator")

    def create_genesis_block(self) -> GameBlock:
        header = BlockHeader(
            height=0,
            previous_hash="0" * 64,
            timestamp=datetime.now(),
            difficulty=self.config.initial_difficulty,
            nonce=0,
            miner="genesis",
            game_round=0,
            entropy_seed=0.0,
        )
        block = GameBlock(
            header=header,
            status=BlockStatus.FINALIZED,
            reward_amount=self.config.mining_reward_base,
        )
        block.header.merkle_root = block.calculate_merkle_root()
        block.block_hash = block.calculate_hash()
        self.logger.info("Genesis block created")
        return block

    def generate_block(
        self,
        previous_block: GameBlock,
        transactions: List[Transaction],
        miner: str,
        market_snapshots: Optional[Dict[str, MarketSnapshot]] = None,
        game_actions: Optional[List[Dict[str, Any]]] = None,
        entropy_value: float = 0.0,
        terrain_hash: str = "",
        mind_vector: Optional[List[float]] = None,
    ) -> GameBlock:
        height = previous_block.header.height + 1
        game_round = previous_block.header.game_round + 1

        header = BlockHeader(
            height=height,
            previous_hash=previous_block.block_hash,
            timestamp=datetime.now(),
            difficulty=self._adjust_difficulty(previous_block),
            nonce=random.randint(0, 1000000),
            miner=miner,
            game_round=game_round,
            entropy_seed=entropy_value,
        )

        base_reward = self.reward_calculator.calculate_block_reward(height)
        total_reward = self.reward_calculator.calculate_entropy_bonus(entropy_value, base_reward)

        block = GameBlock(
            header=header,
            status=BlockStatus.PROPOSED,
            transactions=transactions[:self.config.max_transactions_per_block],
            transaction_count=min(len(transactions), self.config.max_transactions_per_block),
            game_actions=game_actions or [],
            market_snapshots=market_snapshots or {},
            reward_amount=total_reward,
            entropy_value=entropy_value,
            terrain_hash=terrain_hash,
            mind_vector=mind_vector or [0.0] * self.config.mind_vector_size,
        )

        block.header.merkle_root = block.calculate_merkle_root()
        block.block_hash = block.calculate_hash()

        return block

    def _adjust_difficulty(self, previous_block: GameBlock) -> float:
        height = previous_block.header.height
        if height == 0 or height % self.config.difficulty_adjustment_interval != 0:
            return previous_block.header.difficulty

        return previous_block.header.difficulty * 1.05

    def mine_block(self, block: GameBlock, max_nonce: int = 1000000) -> Optional[GameBlock]:
        target = int(2 ** 256 / block.header.difficulty) if block.header.difficulty > 0 else 0

        for nonce in range(max_nonce):
            block.header.nonce = nonce
            block_hash = block.calculate_hash()
            hash_int = int(block_hash, 16)

            if target == 0 or hash_int < target:
                block.block_hash = block_hash
                block.status = BlockStatus.VALIDATED
                return block

        return None


class GameBlockChain:
    """游戏区块链"""

    def __init__(
        self,
        config: Optional[GameConfig] = None,
        generator: Optional[BlockGenerator] = None,
        validator: Optional[BlockValidator] = None,
    ):
        self.config = config or GameConfig()
        self.generator = generator or BlockGenerator(self.config)
        self.validator = validator or BlockValidator(self.config)

        self._chain: List[GameBlock] = []
        self._pending_transactions: List[Transaction] = []
        self._game_state = GameState()
        self._orphan_blocks: Dict[str, GameBlock] = {}
        self._on_block_handlers: List[Callable[[GameBlock], None]] = []

        self.logger = get_logger(f"{__name__}.GameBlockChain")
        self._initialize_chain()

    def _initialize_chain(self) -> None:
        genesis = self.generator.create_genesis_block()
        self._chain.append(genesis)
        self._game_state.current_block_height = 0
        self._game_state.current_block_hash = genesis.block_hash
        self._game_state.mining_difficulty = genesis.header.difficulty
        self._game_state.last_block_time = genesis.header.timestamp
        self._game_state.genesis_time = genesis.header.timestamp

    @property
    def latest_block(self) -> GameBlock:
        return self._chain[-1]

    @property
    def chain_height(self) -> int:
        return len(self._chain) - 1

    @property
    def game_state(self) -> GameState:
        return self._game_state

    def get_block(self, height: int) -> Optional[GameBlock]:
        if 0 <= height < len(self._chain):
            return self._chain[height]
        return None

    def get_block_by_hash(self, block_hash: str) -> Optional[GameBlock]:
        for block in reversed(self._chain):
            if block.block_hash == block_hash:
                return block
        return self._orphan_blocks.get(block_hash)

    def add_transaction(self, transaction: Transaction) -> bool:
        if transaction.status not in (TransactionStatus.PENDING, TransactionStatus.PROCESSING):
            return False
        self._pending_transactions.append(transaction)
        return True

    def add_transactions(self, transactions: List[Transaction]) -> int:
        count = 0
        for txn in transactions:
            if self.add_transaction(txn):
                count += 1
        return count

    def mine_block(
        self,
        miner: str,
        market_snapshots: Optional[Dict[str, MarketSnapshot]] = None,
        game_actions: Optional[List[Dict[str, Any]]] = None,
        entropy_value: float = 0.0,
        terrain_hash: str = "",
        mind_vector: Optional[List[float]] = None,
    ) -> Optional[GameBlock]:
        transactions = self._pending_transactions[:self.config.max_transactions_per_block]

        block = self.generator.generate_block(
            previous_block=self.latest_block,
            transactions=transactions,
            miner=miner,
            market_snapshots=market_snapshots,
            game_actions=game_actions,
            entropy_value=entropy_value,
            terrain_hash=terrain_hash,
            mind_vector=mind_vector,
        )

        valid, errors = self.validator.validate_block(block, self.latest_block)
        if not valid:
            self.logger.error(f"Block validation failed: {errors}")
            return None

        mined_block = self.generator.mine_block(block)
        if not mined_block:
            return None

        self._chain.append(mined_block)
        self._pending_transactions = self._pending_transactions[len(transactions):]
        self._update_game_state(mined_block)

        for handler in self._on_block_handlers:
            try:
                handler(mined_block)
            except Exception as e:
                self.logger.error(f"Block handler error: {e}")

        self.logger.info(
            f"Block {mined_block.header.height} mined by {miner}, "
            f"txns: {mined_block.transaction_count}, "
            f"reward: {mined_block.reward_amount:.4f}"
        )
        return mined_block

    def _update_game_state(self, block: GameBlock) -> None:
        self._game_state.current_block_height = block.header.height
        self._game_state.current_block_hash = block.block_hash
        self._game_state.total_transactions += block.transaction_count
        self._game_state.global_entropy += block.entropy_value
        self._game_state.game_round = block.header.game_round
        self._game_state.mining_difficulty = block.header.difficulty
        self._game_state.last_block_time = block.header.timestamp

        if block.market_snapshots:
            from ai_llm_agent_crawler.finance_game.models import MarketData
            for market, snapshot in block.market_snapshots.items():
                self._game_state.market_states[market] = MarketData(
                    market=market,
                    price=snapshot.close_price,
                    volume_24h=snapshot.volume,
                    high_24h=snapshot.high_price,
                    low_24h=snapshot.low_price,
                    timestamp=snapshot.timestamp,
                )

    def validate_chain(self) -> Tuple[bool, List[str]]:
        errors = []
        for i in range(1, len(self._chain)):
            valid, block_errors = self.validator.validate_block(
                self._chain[i], self._chain[i - 1]
            )
            if not valid:
                errors.append(f"Block {i}: {', '.join(block_errors)}")
        return len(errors) == 0, errors

    def get_pending_transactions(self) -> List[Transaction]:
        return self._pending_transactions.copy()

    def get_pending_transaction_count(self) -> int:
        return len(self._pending_transactions)

    def register_block_handler(self, handler: Callable[[GameBlock], None]) -> None:
        self._on_block_handlers.append(handler)

    def unregister_block_handler(self, handler: Callable[[GameBlock], None]) -> None:
        self._on_block_handlers.remove(handler)

    def get_block_range(self, start_height: int, end_height: int) -> List[GameBlock]:
        start = max(0, start_height)
        end = min(len(self._chain), end_height + 1)
        return self._chain[start:end]

    def calculate_chain_entropy(self) -> float:
        if len(self._chain) < 2:
            return 0.0
        return sum(b.entropy_value for b in self._chain) / len(self._chain)

    def get_statistics(self) -> Dict[str, Any]:
        total_txns = sum(b.transaction_count for b in self._chain)
        total_rewards = sum(b.reward_amount for b in self._chain)
        avg_block_time = 0.0
        if len(self._chain) > 1:
            total_time = (
                self._chain[-1].header.timestamp - self._chain[0].header.timestamp
            ).total_seconds()
            avg_block_time = total_time / (len(self._chain) - 1)

        return {
            "chain_height": self.chain_height,
            "total_blocks": len(self._chain),
            "total_transactions": total_txns,
            "total_rewards": total_rewards,
            "average_block_time": avg_block_time,
            "pending_transactions": len(self._pending_transactions),
            "global_entropy": self._game_state.global_entropy,
            "difficulty": self._game_state.mining_difficulty,
            "game_round": self._game_state.game_round,
        }

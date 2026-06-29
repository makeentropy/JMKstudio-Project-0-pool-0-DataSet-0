"""
Agent Skill向量机 - 核心数据模型

定义Skill、策略、Agent等核心数据结构。
"""

from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np
from pydantic import BaseModel, Field


class SkillType(str, Enum):
    """Skill类型枚举"""
    TRADING = "trading"
    ANALYSIS = "analysis"
    RISK_MANAGEMENT = "risk_management"
    PORTFOLIO_MANAGEMENT = "portfolio_management"
    MARKET_MAKING = "market_making"
    ARBITRAGE = "arbitrage"
    SENTIMENT = "sentiment"
    TECHNICAL = "technical"
    FUNDAMENTAL = "fundamental"
    ENTROPY_ANALYSIS = "entropy_analysis"
    TERRAIN_NAVIGATION = "terrain_navigation"
    MIND_REASONING = "mind_reasoning"
    ADAPTIVE = "adaptive"
    EXPLORATORY = "exploratory"
    OPTIMIZATION = "optimization"


class StrategyType(str, Enum):
    """策略类型枚举"""
    TREND_FOLLOWING = "trend_following"
    MEAN_REVERSION = "mean_reversion"
    MOMENTUM = "momentum"
    STATISTICAL_ARBITRAGE = "statistical_arbitrage"
    PAIRS_TRADING = "pairs_trading"
    MARKET_MAKING = "market_making"
    FUNDAMENTAL = "fundamental"
    SENTIMENT_BASED = "sentiment_based"
    ENTROPY_DRIVEN = "entropy_driven"
    TERRAIN_BASED = "terrain_based"
    MIND_DRIVEN = "mind_driven"
    ADAPTIVE = "adaptive"
    MULTI_FACTOR = "multi_factor"
    RISK_PARITY = "risk_parity"
    EXPLORATORY = "exploratory"
    EVOLUTIONARY = "evolutionary"


class AgentState(str, Enum):
    """Agent状态枚举"""
    IDLE = "idle"
    OBSERVING = "observing"
    THINKING = "thinking"
    ACTING = "acting"
    LEARNING = "learning"
    ADAPTING = "adapting"
    EXPLORING = "exploring"
    EXPLOITING = "exploiting"
    PAUSED = "paused"
    ERROR = "error"


class ActionType(str, Enum):
    """动作类型枚举"""
    BUY = "buy"
    SELL = "sell"
    HOLD = "hold"
    SHORT = "short"
    COVER = "cover"
    ADJUST_POSITION = "adjust_position"
    REBALANCE = "rebalance"
    HEDGE = "hedge"
    OBSERVE = "observe"
    LEARN = "learn"
    ADAPT = "adapt"
    EXPLORE = "explore"
    WAIT = "wait"


class RiskProfile(str, Enum):
    """风险偏好枚举"""
    CONSERVATIVE = "conservative"
    MODERATE = "moderate"
    AGGRESSIVE = "aggressive"
    SPECULATIVE = "speculative"
    NEUTRAL = "neutral"


class SkillVector(BaseModel):
    """Skill向量模型"""
    vector_id: str = Field(default="")
    skill_id: str = Field(default="")
    dimensions: int = Field(default=256)
    values: List[float] = Field(default_factory=list)
    norm: float = Field(default=0.0)
    skill_type: SkillType = Field(default=SkillType.ADAPTIVE)
    effectiveness: float = Field(default=0.0, ge=0.0, le=1.0)
    efficiency: float = Field(default=0.0, ge=0.0, le=1.0)
    creativity: float = Field(default=0.0, ge=0.0, le=1.0)
    adaptability: float = Field(default=0.0, ge=0.0, le=1.0)
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True

    def to_numpy(self) -> np.ndarray:
        return np.array(self.values)

    def from_numpy(self, arr: np.ndarray) -> None:
        self.values = arr.tolist()
        self.dimensions = len(arr)
        self.norm = float(np.linalg.norm(arr))

    def cosine_similarity(self, other: "SkillVector") -> float:
        if self.dimensions != other.dimensions or self.norm == 0 or other.norm == 0:
            return 0.0
        a = self.to_numpy()
        b = other.to_numpy()
        return float(np.dot(a, b) / (self.norm * other.norm))


class Skill(BaseModel):
    """Skill模型"""
    skill_id: str = Field(default="")
    name: str = Field(default="")
    skill_type: SkillType = Field(default=SkillType.ADAPTIVE)
    description: str = Field(default="")
    vectors: Dict[str, SkillVector] = Field(default_factory=dict)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    success_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    usage_count: int = Field(default=0)
    avg_reward: float = Field(default=0.0)
    risk_level: RiskProfile = Field(default=RiskProfile.MODERATE)
    complexity: float = Field(default=0.5, ge=0.0, le=1.0)
    creativity_level: float = Field(default=0.5, ge=0.0, le=1.0)
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    version: str = Field(default="1.0.0")
    parent_skill: Optional[str] = None
    child_skills: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def get_vector(self, vector_type: str = "default") -> Optional[SkillVector]:
        return self.vectors.get(vector_type)

    def add_vector(self, vector: SkillVector, vector_type: str = "default") -> None:
        self.vectors[vector_type] = vector


class Strategy(BaseModel):
    """策略模型"""
    strategy_id: str = Field(default="")
    name: str = Field(default="")
    strategy_type: StrategyType = Field(default=StrategyType.ADAPTIVE)
    description: str = Field(default="")
    skills: List[str] = Field(default_factory=list)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    risk_profile: RiskProfile = Field(default=RiskProfile.MODERATE)
    expected_return: float = Field(default=0.0)
    expected_risk: float = Field(default=0.0)
    sharpe_ratio: float = Field(default=0.0)
    max_drawdown: float = Field(default=0.0)
    win_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    profit_factor: float = Field(default=0.0)
    performance_score: float = Field(default=0.0, ge=0.0, le=1.0)
    adaptability_score: float = Field(default=0.0, ge=0.0, le=1.0)
    entropy_level: float = Field(default=0.0, ge=0.0, le=1.0)
    strategy_vector: List[float] = Field(default_factory=list)
    backtest_results: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    version: str = Field(default="1.0.0")
    parent_strategy: Optional[str] = None
    tags: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def to_vector(self) -> np.ndarray:
        if self.strategy_vector:
            return np.array(self.strategy_vector)
        vec = np.array([
            self.expected_return,
            self.expected_risk,
            self.sharpe_ratio,
            self.max_drawdown,
            self.win_rate,
            self.profit_factor,
            self.performance_score,
            self.adaptability_score,
            self.entropy_level,
        ])
        return vec


class StrategyResult(BaseModel):
    """策略执行结果"""
    result_id: str = Field(default="")
    strategy_id: str = Field(default="")
    timestamp: datetime = Field(default_factory=datetime.now)
    actions: List[ActionType] = Field(default_factory=list)
    returns: float = Field(default=0.0)
    risk: float = Field(default=0.0)
    pnl: float = Field(default=0.0)
    success: bool = Field(default=False)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    trades_executed: int = Field(default=0)
    positions_changed: int = Field(default=0)
    observations: List[str] = Field(default_factory=list)
    lessons_learned: List[str] = Field(default_factory=list)
    entropy_change: float = Field(default=0.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Action(BaseModel):
    """动作模型"""
    action_id: str = Field(default="")
    action_type: ActionType = Field(default=ActionType.HOLD)
    target: str = Field(default="")
    parameters: Dict[str, Any] = Field(default_factory=dict)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    expected_outcome: float = Field(default=0.0)
    risk_assessment: float = Field(default=0.0)
    timestamp: datetime = Field(default_factory=datetime.now)
    skill_used: Optional[str] = None
    strategy_used: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Observation(BaseModel):
    """观察模型"""
    observation_id: str = Field(default="")
    timestamp: datetime = Field(default_factory=datetime.now)
    market_data: Dict[str, Any] = Field(default_factory=dict)
    portfolio_state: Dict[str, Any] = Field(default_factory=dict)
    terrain_state: Dict[str, Any] = Field(default_factory=dict)
    entropy_readings: Dict[str, float] = Field(default_factory=dict)
    mind_state: Dict[str, Any] = Field(default_factory=dict)
    features: List[float] = Field(default_factory=list)
    events: List[str] = Field(default_factory=list)
    novelty_score: float = Field(default=0.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Reward(BaseModel):
    """奖励模型"""
    reward_id: str = Field(default="")
    timestamp: datetime = Field(default_factory=datetime.now)
    value: float = Field(default=0.0)
    reward_type: str = Field(default="extrinsic")
    components: Dict[str, float] = Field(default_factory=dict)
    immediate_reward: float = Field(default=0.0)
    delayed_reward: float = Field(default=0.0)
    intrinsic_reward: float = Field(default=0.0)
    extrinsic_reward: float = Field(default=0.0)
    exploration_bonus: float = Field(default=0.0)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Policy(BaseModel):
    """策略/政策模型"""
    policy_id: str = Field(default="")
    name: str = Field(default="")
    policy_type: str = Field(default="stochastic")
    state_dim: int = Field(default=0)
    action_dim: int = Field(default=0)
    parameters: Dict[str, Any] = Field(default_factory=dict)
    learning_rate: float = Field(default=0.001)
    discount_factor: float = Field(default=0.99)
    epsilon: float = Field(default=0.1)
    entropy_coefficient: float = Field(default=0.01)
    value_estimate: float = Field(default=0.0)
    advantage: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class Agent(BaseModel):
    """Agent模型"""
    agent_id: str = Field(default="")
    name: str = Field(default="")
    state: AgentState = Field(default=AgentState.IDLE)
    risk_profile: RiskProfile = Field(default=RiskProfile.MODERATE)
    skills: List[str] = Field(default_factory=list)
    strategies: List[str] = Field(default_factory=list)
    current_strategy: Optional[str] = None
    balance: float = Field(default=0.0)
    initial_balance: float = Field(default=0.0)
    total_pnl: float = Field(default=0.0)
    total_trades: int = Field(default=0)
    win_rate: float = Field(default=0.0)
    current_observation: Optional[Observation] = None
    last_action: Optional[Action] = None
    last_reward: Optional[Reward] = None
    memory_size: int = Field(default=1000)
    learning_rate: float = Field(default=0.001)
    exploration_rate: float = Field(default=0.1)
    entropy_bonus: float = Field(default=0.01)
    adaptation_rate: float = Field(default=0.1)
    creativity_level: float = Field(default=0.5, ge=0.0, le=1.0)
    mind_state_vector: List[float] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    last_active: Optional[datetime] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class StrategyConfig(BaseModel):
    """策略配置模型"""
    strategy_type: StrategyType = Field(default=StrategyType.ADAPTIVE)
    risk_profile: RiskProfile = Field(default=RiskProfile.MODERATE)
    max_position_size: float = Field(default=0.1)
    rebalance_frequency: str = Field(default="daily")
    stop_loss: float = Field(default=0.05)
    take_profit: float = Field(default=0.10)
    leverage: float = Field(default=1.0)
    entropy_threshold: float = Field(default=0.5)
    adaptability_level: float = Field(default=0.5)
    exploration_rate: float = Field(default=0.1)
    use_entropy: bool = Field(default=True)
    use_terrain: bool = Field(default=True)
    use_mind: bool = Field(default=True)
    parameters: Dict[str, Any] = Field(default_factory=dict)


class AgentConfig(BaseModel):
    """Agent配置模型"""
    agent_name: str = Field(default="strategy_agent")
    initial_balance: float = Field(default=10000.0)
    risk_profile: RiskProfile = Field(default=RiskProfile.MODERATE)
    learning_rate: float = Field(default=0.001)
    exploration_rate: float = Field(default=0.1)
    exploration_decay: float = Field(default=0.995)
    min_exploration_rate: float = Field(default=0.01)
    memory_size: int = Field(default=1000)
    batch_size: int = Field(default=32)
    target_update_freq: int = Field(default=100)
    entropy_coefficient: float = Field(default=0.01)
    adaptation_rate: float = Field(default=0.1)
    creativity_level: float = Field(default=0.5)
    mind_vector_size: int = Field(default=256)
    skill_vector_size: int = Field(default=256)
    enabled_skill_types: List[SkillType] = Field(default_factory=lambda: list(SkillType))
    enabled_strategy_types: List[StrategyType] = Field(default_factory=lambda: list(StrategyType))


class SkillLibrary(BaseModel):
    """Skill库模型"""
    library_id: str = Field(default="")
    name: str = Field(default="")
    skills: Dict[str, Skill] = Field(default_factory=dict)
    skill_count: int = Field(default=0)
    skill_types: Dict[str, int] = Field(default_factory=dict)
    avg_effectiveness: float = Field(default=0.0)
    total_usage: int = Field(default=0)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_skill(self, skill: Skill) -> None:
        self.skills[skill.skill_id] = skill
        self.skill_count = len(self.skills)
        skill_type = skill.skill_type.value
        self.skill_types[skill_type] = self.skill_types.get(skill_type, 0) + 1
        self.avg_effectiveness = float(np.mean([s.success_rate for s in self.skills.values()]))

    def get_skill(self, skill_id: str) -> Optional[Skill]:
        return self.skills.get(skill_id)

    def get_skills_by_type(self, skill_type: SkillType) -> List[Skill]:
        return [s for s in self.skills.values() if s.skill_type == skill_type]

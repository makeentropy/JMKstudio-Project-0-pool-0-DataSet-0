"""
市场系统模块

提供市场模拟、价格引擎、波动率计算、市场数据流等功能。
"""

import math
import random
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple

import numpy as np

from ai_llm_agent_crawler.finance_game.models import (
    MarketData,
    MarketSnapshot,
    MarketType,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class VolatilityCalculator:
    """波动率计算器"""

    def __init__(self, window_size: int = 20, annualization_factor: float = 252.0):
        self.window_size = window_size
        self.annualization_factor = annualization_factor

    def calculate_returns(self, prices: List[float]) -> List[float]:
        returns = []
        for i in range(1, len(prices)):
            if prices[i - 1] != 0:
                returns.append((prices[i] - prices[i - 1]) / prices[i - 1])
        return returns

    def calculate_volatility(self, prices: List[float]) -> float:
        if len(prices) < 2:
            return 0.0
        returns = self.calculate_returns(prices[-self.window_size:])
        if len(returns) < 2:
            return 0.0
        return float(np.std(returns) * math.sqrt(self.annualization_factor))

    def calculate_rolling_volatility(self, prices: List[float]) -> List[float]:
        vols = []
        for i in range(len(prices)):
            window = prices[max(0, i - self.window_size + 1):i + 1]
            vols.append(self.calculate_volatility(window))
        return vols

    def calculate_atr(self, highs: List[float], lows: List[float], closes: List[float]) -> float:
        if len(highs) < 2:
            return 0.0
        trs = []
        for i in range(1, len(highs)):
            tr = max(
                highs[i] - lows[i],
                abs(highs[i] - closes[i - 1]),
                abs(lows[i] - closes[i - 1]),
            )
            trs.append(tr)
        return float(np.mean(trs[-self.window_size:])) if trs else 0.0

    def calculate_bollinger_bands(
        self, prices: List[float], num_std: float = 2.0
    ) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        if len(prices) < self.window_size:
            return None, None, None
        window = prices[-self.window_size:]
        sma = float(np.mean(window))
        std = float(np.std(window))
        upper = sma + num_std * std
        lower = sma - num_std * std
        return upper, sma, lower


class PriceEngine:
    """价格引擎 - 基于多种模型生成价格"""

    def __init__(self, initial_price: float = 100.0, volatility: float = 0.2, drift: float = 0.05):
        self.current_price = initial_price
        self.volatility = volatility
        self.drift = drift
        self.price_history: List[float] = [initial_price]
        self.timestamps: List[datetime] = [datetime.now()]
        self.volatility_calc = VolatilityCalculator()

    def next_price_gbm(self, dt: float = 1.0 / 252.0) -> float:
        z = random.gauss(0, 1)
        drift = (self.drift - 0.5 * self.volatility ** 2) * dt
        diffusion = self.volatility * math.sqrt(dt) * z
        new_price = self.current_price * math.exp(drift + diffusion)
        self.current_price = max(0.0001, new_price)
        self.price_history.append(self.current_price)
        self.timestamps.append(datetime.now())
        return self.current_price

    def next_price_mean_reverting(
        self, mean_price: float, speed: float = 0.1, dt: float = 1.0 / 252.0
    ) -> float:
        z = random.gauss(0, 1)
        drift = speed * (mean_price - self.current_price) * dt
        diffusion = self.volatility * math.sqrt(dt) * z
        new_price = self.current_price + drift + diffusion
        self.current_price = max(0.0001, new_price)
        self.price_history.append(self.current_price)
        self.timestamps.append(datetime.now())
        return self.current_price

    def next_price_jump_diffusion(
        self,
        jump_intensity: float = 0.1,
        jump_mean: float = 0.0,
        jump_std: float = 0.05,
        dt: float = 1.0 / 252.0,
    ) -> float:
        z = random.gauss(0, 1)
        drift = (self.drift - 0.5 * self.volatility ** 2) * dt
        diffusion = self.volatility * math.sqrt(dt) * z

        jump = 0.0
        if random.random() < jump_intensity * dt:
            jump = random.gauss(jump_mean, jump_std)

        new_price = self.current_price * math.exp(drift + diffusion + jump)
        self.current_price = max(0.0001, new_price)
        self.price_history.append(self.current_price)
        self.timestamps.append(datetime.now())
        return self.current_price

    def apply_entropy_perturbation(self, entropy_value: float) -> float:
        perturbation = random.uniform(-1, 1) * entropy_value * 0.1
        self.current_price *= (1 + perturbation)
        self.current_price = max(0.0001, self.current_price)
        self.price_history.append(self.current_price)
        self.timestamps.append(datetime.now())
        return self.current_price

    def get_current_volatility(self) -> float:
        return self.volatility_calc.calculate_volatility(self.price_history)

    def get_price_at_time(self, timestamp: datetime) -> Optional[float]:
        for i, ts in enumerate(reversed(self.timestamps)):
            if ts <= timestamp:
                idx = len(self.timestamps) - 1 - i
                return self.price_history[idx]
        return None


class MarketDataFeed:
    """市场数据流"""

    def __init__(self):
        self._markets: Dict[str, MarketData] = {}
        self._price_histories: Dict[str, List[float]] = {}
        self._listeners: Dict[str, List[Callable[[MarketData], None]]] = {}
        self.logger = get_logger(f"{__name__}.MarketDataFeed")

    def register_market(self, market: str, initial_price: float = 100.0) -> None:
        if market in self._markets:
            return
        self._markets[market] = MarketData(
            market=market,
            price=initial_price,
            open_24h=initial_price,
            high_24h=initial_price,
            low_24h=initial_price,
        )
        self._price_histories[market] = [initial_price]
        self._listeners[market] = []

    def subscribe(self, market: str, callback: Callable[[MarketData], None]) -> None:
        if market not in self._listeners:
            self._listeners[market] = []
        self._listeners[market].append(callback)

    def unsubscribe(self, market: str, callback: Callable[[MarketData], None]) -> None:
        if market in self._listeners and callback in self._listeners[market]:
            self._listeners[market].remove(callback)

    def update_price(self, market: str, new_price: float, volume: float = 0.0) -> Optional[MarketData]:
        if market not in self._markets:
            return None

        current = self._markets[market]
        old_price = current.price

        current.price = new_price
        current.volume_24h += volume
        current.high_24h = max(current.high_24h, new_price)
        current.low_24h = min(current.low_24h, new_price)
        current.change_24h = new_price - current.open_24h
        if current.open_24h > 0:
            current.change_percent_24h = (current.change_24h / current.open_24h) * 100
        current.timestamp = datetime.now()

        self._price_histories[market].append(new_price)

        for callback in self._listeners.get(market, []):
            try:
                callback(current)
            except Exception as e:
                self.logger.error(f"Market data listener error: {e}")

        return current

    def get_market_data(self, market: str) -> Optional[MarketData]:
        return self._markets.get(market)

    def get_all_markets(self) -> Dict[str, MarketData]:
        return self._markets.copy()

    def get_price_history(self, market: str, limit: int = 100) -> List[float]:
        history = self._price_histories.get(market, [])
        return history[-limit:] if limit else history.copy()

    def create_snapshot(self, market: str, block_height: int) -> Optional[MarketSnapshot]:
        history = self._price_histories.get(market, [])
        if not history:
            return None

        prices = history[-288:] if len(history) >= 288 else history
        vol_calc = VolatilityCalculator()
        volatility = vol_calc.calculate_volatility(prices)

        returns = vol_calc.calculate_returns(prices)
        entropy = self._calculate_shannon_entropy(returns) if returns else 0.0

        return MarketSnapshot(
            market=market,
            block_height=block_height,
            open_price=prices[0],
            close_price=prices[-1],
            high_price=max(prices),
            low_price=min(prices),
            volume=sum(abs(r) for r in returns) * 1000,
            trades_count=len(returns),
            volatility=volatility,
            entropy=entropy,
            timestamp=datetime.now(),
        )

    def _calculate_shannon_entropy(self, values: List[float], bins: int = 10) -> float:
        if not values:
            return 0.0
        hist, _ = np.histogram(values, bins=bins, density=True)
        hist = hist[hist > 0]
        if len(hist) == 0:
            return 0.0
        probs = hist / hist.sum()
        return float(-np.sum(probs * np.log2(probs)))


class MarketSimulator:
    """市场模拟器 - 模拟多个市场的价格行为"""

    def __init__(
        self,
        market_count: int = 10,
        base_price: float = 100.0,
        base_volatility: float = 0.2,
    ):
        self.market_count = market_count
        self.base_price = base_price
        self.base_volatility = base_volatility
        self.price_engines: Dict[str, PriceEngine] = {}
        self.data_feed = MarketDataFeed()
        self.volatility_calc = VolatilityCalculator()
        self.logger = get_logger(f"{__name__}.MarketSimulator")
        self._initialize_markets()

    def _initialize_markets(self) -> None:
        for i in range(self.market_count):
            symbol = f"TOKEN{i:02d}"
            volatility = self.base_volatility * (0.5 + random.random())
            drift = (random.random() - 0.5) * 0.1
            initial_price = self.base_price * (0.5 + random.random())

            self.price_engines[symbol] = PriceEngine(
                initial_price=initial_price,
                volatility=volatility,
                drift=drift,
            )
            self.data_feed.register_market(symbol, initial_price)

    def step(self, dt: float = 1.0 / 252.0, entropy_impact: float = 0.0) -> Dict[str, float]:
        prices = {}
        for symbol, engine in self.price_engines.items():
            model_choice = random.random()
            if model_choice < 0.6:
                new_price = engine.next_price_gbm(dt)
            elif model_choice < 0.85:
                mean_price = engine.price_history[0] * (1 + engine.drift * 0.1)
                new_price = engine.next_price_mean_reverting(mean_price, 0.05, dt)
            else:
                new_price = engine.next_price_jump_diffusion(0.15, 0.0, 0.08, dt)

            if entropy_impact > 0:
                new_price = engine.apply_entropy_perturbation(entropy_impact)

            self.data_feed.update_price(symbol, new_price)
            prices[symbol] = new_price

        self._apply_correlations()
        return prices

    def _apply_correlations(self) -> None:
        symbols = list(self.price_engines.keys())
        if len(symbols) < 2:
            return
        market_return = 0.0
        for symbol in symbols:
            history = self.price_engines[symbol].price_history
            if len(history) >= 2:
                market_return += (history[-1] - history[-2]) / history[-2]
        market_return /= len(symbols)

        for symbol in symbols:
            engine = self.price_engines[symbol]
            beta = 0.3 + random.random() * 1.4
            current = engine.current_price
            correlated_price = current * (1 + beta * market_return * 0.1)
            engine.current_price = (current + correlated_price) / 2

    def get_market_price(self, symbol: str) -> Optional[float]:
        engine = self.price_engines.get(symbol)
        return engine.current_price if engine else None

    def get_all_prices(self) -> Dict[str, float]:
        return {s: e.current_price for s, e in self.price_engines.items()}

    def create_all_snapshots(self, block_height: int) -> Dict[str, MarketSnapshot]:
        snapshots = {}
        for symbol in self.price_engines.keys():
            snapshot = self.data_feed.create_snapshot(symbol, block_height)
            if snapshot:
                snapshots[symbol] = snapshot
        return snapshots

    def calculate_market_entropy(self) -> float:
        entropies = []
        for symbol, engine in self.price_engines.items():
            returns = self.volatility_calc.calculate_returns(engine.price_history[-100:])
            if returns:
                hist, _ = np.histogram(returns, bins=20, density=True)
                hist = hist[hist > 0]
                if len(hist) > 0:
                    probs = hist / hist.sum()
                    entropies.append(float(-np.sum(probs * np.log2(probs))))
        return float(np.mean(entropies)) if entropies else 0.0

    def get_market_data(self, symbol: str) -> Optional[MarketData]:
        return self.data_feed.get_market_data(symbol)

    def get_all_market_data(self) -> Dict[str, MarketData]:
        return self.data_feed.get_all_markets()

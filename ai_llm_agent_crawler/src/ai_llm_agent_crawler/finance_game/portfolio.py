"""
投资组合模块

提供资产配置、风险分析、投资组合管理、再平衡等功能。
"""

import math
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from ai_llm_agent_crawler.finance_game.models import (
    Asset,
    AssetClass,
    OrderSide,
    Portfolio,
    Position,
    RiskLevel,
    RiskMetrics,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class RiskAnalyzer:
    """风险分析器"""

    def __init__(self, risk_free_rate: float = 0.02):
        self.risk_free_rate = risk_free_rate

    def calculate_returns(self, values: List[float]) -> List[float]:
        returns = []
        for i in range(1, len(values)):
            if values[i - 1] != 0:
                returns.append((values[i] - values[i - 1]) / values[i - 1])
        return returns

    def calculate_volatility(self, returns: List[float], annualize: bool = True) -> float:
        if len(returns) < 2:
            return 0.0
        vol = float(np.std(returns))
        if annualize:
            vol *= math.sqrt(252)
        return vol

    def calculate_sharpe_ratio(
        self, returns: List[float], annualize: bool = True
    ) -> float:
        if len(returns) < 2:
            return 0.0
        mean_return = float(np.mean(returns))
        vol = float(np.std(returns))
        if vol == 0:
            return 0.0
        sharpe = (mean_return - self.risk_free_rate / 252) / vol
        if annualize:
            sharpe *= math.sqrt(252)
        return sharpe

    def calculate_sortino_ratio(self, returns: List[float]) -> float:
        if len(returns) < 2:
            return 0.0
        mean_return = float(np.mean(returns))
        downside_returns = [r for r in returns if r < 0]
        if not downside_returns:
            return float("inf") if mean_return > 0 else 0.0
        downside_dev = float(np.std(downside_returns))
        if downside_dev == 0:
            return 0.0
        sortino = (mean_return - self.risk_free_rate / 252) / downside_dev
        return sortino * math.sqrt(252)

    def calculate_max_drawdown(self, values: List[float]) -> Tuple[float, int, int]:
        if not values:
            return 0.0, 0, 0

        peak = values[0]
        peak_idx = 0
        max_dd = 0.0
        max_dd_start = 0
        max_dd_end = 0

        for i, val in enumerate(values):
            if val > peak:
                peak = val
                peak_idx = i
            dd = (peak - val) / peak if peak > 0 else 0.0
            if dd > max_dd:
                max_dd = dd
                max_dd_start = peak_idx
                max_dd_end = i

        return max_dd, max_dd_start, max_dd_end

    def calculate_var(
        self, returns: List[float], confidence: float = 0.95
    ) -> float:
        if len(returns) < 10:
            return 0.0
        sorted_returns = sorted(returns)
        idx = int(len(sorted_returns) * (1 - confidence))
        return -sorted_returns[idx] if idx < len(sorted_returns) else 0.0

    def calculate_cvar(
        self, returns: List[float], confidence: float = 0.95
    ) -> float:
        if len(returns) < 10:
            return 0.0
        sorted_returns = sorted(returns)
        idx = int(len(sorted_returns) * (1 - confidence))
        tail = sorted_returns[:max(1, idx)]
        return -float(np.mean(tail)) if tail else 0.0

    def calculate_beta(
        self, portfolio_returns: List[float], market_returns: List[float]
    ) -> float:
        if len(portfolio_returns) < 2 or len(market_returns) < 2:
            return 0.0
        min_len = min(len(portfolio_returns), len(market_returns))
        p = portfolio_returns[-min_len:]
        m = market_returns[-min_len:]
        cov = float(np.cov(p, m)[0][1])
        var_m = float(np.var(m))
        return cov / var_m if var_m != 0 else 0.0

    def calculate_alpha(
        self,
        portfolio_returns: List[float],
        market_returns: List[float],
        beta: Optional[float] = None,
    ) -> float:
        if not portfolio_returns or not market_returns:
            return 0.0
        if beta is None:
            beta = self.calculate_beta(portfolio_returns, market_returns)
        portfolio_mean = float(np.mean(portfolio_returns)) * 252
        market_mean = float(np.mean(market_returns)) * 252
        return portfolio_mean - (self.risk_free_rate + beta * (market_mean - self.risk_free_rate))

    def calculate_tail_ratio(self, returns: List[float]) -> float:
        if len(returns) < 20:
            return 0.0
        sorted_returns = sorted(returns)
        tail_5pct = int(len(sorted_returns) * 0.05)
        left_tail = sorted_returns[:max(1, tail_5pct)]
        right_tail = sorted_returns[-max(1, tail_5pct):]
        left_mean = abs(float(np.mean(left_tail))) if left_tail else 1.0
        right_mean = abs(float(np.mean(right_tail))) if right_tail else 0.0
        return right_mean / left_mean if left_mean > 0 else 0.0

    def calculate_gain_loss_ratio(self, returns: List[float]) -> float:
        gains = [r for r in returns if r > 0]
        losses = [abs(r) for r in returns if r < 0]
        if not losses:
            return float("inf") if gains else 0.0
        avg_gain = float(np.mean(gains)) if gains else 0.0
        avg_loss = float(np.mean(losses))
        return avg_gain / avg_loss if avg_loss > 0 else 0.0

    def calculate_profit_factor(self, returns: List[float]) -> float:
        gross_profit = sum(r for r in returns if r > 0)
        gross_loss = abs(sum(r for r in returns if r < 0))
        return gross_profit / gross_loss if gross_loss > 0 else float("inf") if gross_profit > 0 else 0.0

    def calculate_full_metrics(
        self,
        portfolio_values: List[float],
        market_values: Optional[List[float]] = None,
    ) -> RiskMetrics:
        returns = self.calculate_returns(portfolio_values)
        if not returns:
            return RiskMetrics()

        total_return = (
            (portfolio_values[-1] - portfolio_values[0]) / portfolio_values[0]
            if portfolio_values[0] != 0 else 0.0
        )
        annualized_return = (1 + total_return) ** (252 / len(returns)) - 1 if len(returns) > 0 else 0.0

        volatility = self.calculate_volatility(returns)
        sharpe = self.calculate_sharpe_ratio(returns)
        sortino = self.calculate_sortino_ratio(returns)
        max_dd, _, dd_end = self.calculate_max_drawdown(portfolio_values)
        dd_duration = dd_end - 0

        var_95 = self.calculate_var(returns, 0.95)
        var_99 = self.calculate_var(returns, 0.99)
        cvar_95 = self.calculate_cvar(returns, 0.95)

        beta = 0.0
        alpha = 0.0
        information_ratio = 0.0
        if market_values and len(market_values) > 1:
            market_returns = self.calculate_returns(market_values)
            beta = self.calculate_beta(returns, market_returns)
            alpha = self.calculate_alpha(returns, market_returns, beta)
            if market_returns:
                active_returns = [r - m for r, m in zip(returns, market_returns)]
                active_vol = float(np.std(active_returns)) * math.sqrt(252) if active_returns else 0.0
                info_ratio_num = (float(np.mean(active_returns)) * 252) if active_returns else 0.0
                information_ratio = info_ratio_num / active_vol if active_vol > 0 else 0.0

        calmar = annualized_return / max_dd if max_dd > 0 else 0.0
        tail_ratio = self.calculate_tail_ratio(returns)
        gain_loss_ratio = self.calculate_gain_loss_ratio(returns)
        profit_factor = self.calculate_profit_factor(returns)

        return RiskMetrics(
            portfolio_value=portfolio_values[-1],
            total_return=total_return,
            annualized_return=annualized_return,
            volatility=volatility,
            sharpe_ratio=sharpe,
            sortino_ratio=sortino,
            max_drawdown=max_dd,
            max_drawdown_duration=dd_duration,
            var_95=var_95,
            var_99=var_99,
            cvar_95=cvar_95,
            beta=beta,
            alpha=alpha,
            information_ratio=information_ratio,
            calmar_ratio=calmar,
            tail_ratio=tail_ratio,
            gain_loss_ratio=gain_loss_ratio,
            profit_factor=profit_factor,
        )


class AssetAllocator:
    """资产配置器"""

    def __init__(self):
        self.logger = get_logger(f"{__name__}.AssetAllocator")

    def equal_weight(self, symbols: List[str]) -> Dict[str, float]:
        if not symbols:
            return {}
        weight = 1.0 / len(symbols)
        return {s: weight for s in symbols}

    def market_cap_weight(
        self, market_caps: Dict[str, float]
    ) -> Dict[str, float]:
        total = sum(market_caps.values())
        if total == 0:
            return self.equal_weight(list(market_caps.keys()))
        return {s: cap / total for s, cap in market_caps.items()}

    def inverse_volatility_weight(
        self, volatilities: Dict[str, float]
    ) -> Dict[str, float]:
        inv_vols = {}
        for s, vol in volatilities.items():
            inv_vols[s] = 1.0 / vol if vol > 0 else 0.0
        total = sum(inv_vols.values())
        if total == 0:
            return self.equal_weight(list(volatilities.keys()))
        return {s: iv / total for s, iv in inv_vols.items()}

    def risk_parity(
        self,
        returns: Dict[str, List[float]],
        max_iterations: int = 100,
        tolerance: float = 1e-6,
    ) -> Dict[str, float]:
        symbols = list(returns.keys())
        n = len(symbols)
        if n == 0:
            return {}
        if n == 1:
            return {symbols[0]: 1.0}

        min_len = min(len(r) for r in returns.values())
        return_matrix = np.array([returns[s][-min_len:] for s in symbols])
        cov_matrix = np.cov(return_matrix)

        weights = np.ones(n) / n
        learning_rate = 0.01

        for _ in range(max_iterations):
            portfolio_vol = np.sqrt(weights @ cov_matrix @ weights)
            if portfolio_vol == 0:
                break

            marginal_risk = (cov_matrix @ weights) / portfolio_vol
            risk_contribution = weights * marginal_risk
            target_risk = portfolio_vol / n

            gradient = risk_contribution - target_risk
            weights -= learning_rate * gradient

            weights = np.maximum(weights, 0)
            weights /= weights.sum()

            if np.max(np.abs(gradient)) < tolerance:
                break

        return {s: float(weights[i]) for i, s in enumerate(symbols)}

    def mean_variance(
        self,
        expected_returns: Dict[str, float],
        cov_matrix: np.ndarray,
        target_return: Optional[float] = None,
        risk_aversion: float = 1.0,
    ) -> Dict[str, float]:
        symbols = list(expected_returns.keys())
        n = len(symbols)
        if n == 0:
            return {}

        mu = np.array(list(expected_returns.values()))

        if target_return is None:
            inv_cov = np.linalg.pinv(cov_matrix)
            weights = inv_cov @ mu / risk_aversion
            weights = np.maximum(weights, 0)
            weights /= weights.sum() if weights.sum() > 0 else 1.0
        else:
            ones = np.ones(n)
            inv_cov = np.linalg.pinv(cov_matrix)

            a = ones @ inv_cov @ ones
            b = mu @ inv_cov @ ones
            c = mu @ inv_cov @ mu

            lambda_ = (c - target_return * b) / (a * c - b ** 2) if (a * c - b ** 2) != 0 else 0
            gamma = (target_return * a - b) / (a * c - b ** 2) if (a * c - b ** 2) != 0 else 0

            weights = inv_cov @ (lambda_ * ones + gamma * mu)
            weights = np.maximum(weights, 0)
            weights /= weights.sum() if weights.sum() > 0 else 1.0

        return {s: float(weights[i]) for i, s in enumerate(symbols)}

    def adjust_for_risk_level(
        self,
        allocation: Dict[str, float],
        risk_level: RiskLevel,
        cash_weight: float = 0.0,
    ) -> Dict[str, float]:
        risk_factors = {
            RiskLevel.CONSERVATIVE: 0.3,
            RiskLevel.MODERATE: 0.5,
            RiskLevel.BALANCED: 0.7,
            RiskLevel.AGGRESSIVE: 0.9,
            RiskLevel.SPECULATIVE: 1.0,
        }
        factor = risk_factors.get(risk_level, 0.5)
        adjusted = {s: w * (1 - cash_weight) * factor for s, w in allocation.items()}
        if cash_weight > 0:
            adjusted["CASH"] = cash_weight
        remaining = 1.0 - sum(adjusted.values())
        if remaining > 0 and "CASH" in adjusted:
            adjusted["CASH"] += remaining
        elif remaining > 0:
            adjusted["CASH"] = remaining
        return adjusted


class RebalancingEngine:
    """再平衡引擎"""

    def __init__(self, threshold: float = 0.05):
        self.threshold = threshold
        self.logger = get_logger(f"{__name__}.RebalancingEngine")

    def needs_rebalancing(
        self,
        current_allocations: Dict[str, float],
        target_allocations: Dict[str, float],
    ) -> bool:
        for symbol, target in target_allocations.items():
            current = current_allocations.get(symbol, 0.0)
            if abs(current - target) > self.threshold:
                return True
        for symbol in current_allocations:
            if symbol not in target_allocations and current_allocations[symbol] > self.threshold:
                return True
        return False

    def calculate_rebalancing_trades(
        self,
        current_allocations: Dict[str, float],
        target_allocations: Dict[str, float],
        total_value: float,
        current_prices: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        trades = []

        all_symbols = set(current_allocations.keys()) | set(target_allocations.keys())

        for symbol in all_symbols:
            current_weight = current_allocations.get(symbol, 0.0)
            target_weight = target_allocations.get(symbol, 0.0)
            weight_diff = target_weight - current_weight
            value_diff = weight_diff * total_value

            price = current_prices.get(symbol, 0.0)
            if price <= 0:
                continue

            quantity_diff = value_diff / price

            if abs(quantity_diff) > 0.0001:
                side = OrderSide.BUY if quantity_diff > 0 else OrderSide.SELL
                trades.append({
                    "symbol": symbol,
                    "side": side,
                    "quantity": abs(quantity_diff),
                    "value": abs(value_diff),
                    "price": price,
                })

        trades.sort(key=lambda t: t["value"], reverse=True)
        return trades

    def rebalance(
        self,
        portfolio: Portfolio,
        target_allocations: Dict[str, float],
        current_prices: Dict[str, float],
    ) -> Tuple[Portfolio, List[Dict[str, Any]]]:
        current_allocs = {}
        total_value = portfolio.total_value

        for asset in portfolio.assets:
            if total_value > 0:
                current_allocs[asset.symbol] = asset.market_value / total_value

        if not self.needs_rebalancing(current_allocs, target_allocations):
            return portfolio, []

        trades = self.calculate_rebalancing_trades(
            current_allocs, target_allocations, total_value, current_prices
        )

        return portfolio, trades


class PortfolioManager:
    """投资组合管理器"""

    def __init__(
        self,
        risk_analyzer: Optional[RiskAnalyzer] = None,
        asset_allocator: Optional[AssetAllocator] = None,
        rebalancing_engine: Optional[RebalancingEngine] = None,
    ):
        self.risk_analyzer = risk_analyzer or RiskAnalyzer()
        self.asset_allocator = asset_allocator or AssetAllocator()
        self.rebalancing_engine = rebalancing_engine or RebalancingEngine()
        self._portfolios: Dict[str, Portfolio] = {}
        self._value_history: Dict[str, List[float]] = {}
        self.logger = get_logger(f"{__name__}.PortfolioManager")

    def create_portfolio(
        self,
        name: str,
        user_id: str,
        account_id: str,
        risk_level: RiskLevel = RiskLevel.MODERATE,
        initial_cash: Optional[Dict[str, float]] = None,
    ) -> Portfolio:
        portfolio = Portfolio(
            name=name,
            user_id=user_id,
            account_id=account_id,
            risk_level=risk_level,
            cash_balances=initial_cash or {},
        )
        self._portfolios[portfolio.portfolio_id] = portfolio
        self._value_history[portfolio.portfolio_id] = [portfolio.total_value]
        self.logger.info(f"Portfolio created: {portfolio.portfolio_id} ({name})")
        return portfolio

    def get_portfolio(self, portfolio_id: str) -> Optional[Portfolio]:
        return self._portfolios.get(portfolio_id)

    def add_asset(
        self,
        portfolio_id: str,
        symbol: str,
        quantity: float,
        price: float,
        asset_class: AssetClass = AssetClass.CRYPTO,
        name: str = "",
    ) -> bool:
        portfolio = self._portfolios.get(portfolio_id)
        if not portfolio:
            return False

        existing = portfolio.get_asset(symbol)
        if existing:
            total_cost = existing.avg_cost * existing.quantity + price * quantity
            total_qty = existing.quantity + quantity
            existing.avg_cost = total_cost / total_qty if total_qty > 0 else 0
            existing.quantity = total_qty
            existing.current_price = price
        else:
            portfolio.assets.append(
                Asset(
                    symbol=symbol,
                    name=name or symbol,
                    asset_class=asset_class,
                    current_price=price,
                    quantity=quantity,
                    avg_cost=price,
                )
            )

        portfolio.updated_at = datetime.now()
        return True

    def remove_asset(self, portfolio_id: str, symbol: str, quantity: float) -> bool:
        portfolio = self._portfolios.get(portfolio_id)
        if not portfolio:
            return False

        existing = portfolio.get_asset(symbol)
        if not existing or existing.quantity < quantity:
            return False

        existing.quantity -= quantity
        if existing.quantity <= 0:
            portfolio.assets = [a for a in portfolio.assets if a.symbol != symbol]

        portfolio.updated_at = datetime.now()
        return True

    def update_prices(self, portfolio_id: str, prices: Dict[str, float]) -> bool:
        portfolio = self._portfolios.get(portfolio_id)
        if not portfolio:
            return False

        for asset in portfolio.assets:
            if asset.symbol in prices:
                asset.current_price = prices[asset.symbol]

        portfolio.updated_at = datetime.now()

        if portfolio_id not in self._value_history:
            self._value_history[portfolio_id] = []
        self._value_history[portfolio_id].append(portfolio.total_value)

        return True

    def update_risk_metrics(
        self,
        portfolio_id: str,
        market_values: Optional[List[float]] = None,
    ) -> Optional[RiskMetrics]:
        portfolio = self._portfolios.get(portfolio_id)
        if not portfolio:
            return None

        history = self._value_history.get(portfolio_id, [])
        if len(history) < 2:
            return None

        metrics = self.risk_analyzer.calculate_full_metrics(history, market_values)
        portfolio.risk_metrics = metrics
        return metrics

    def rebalance_portfolio(
        self,
        portfolio_id: str,
        target_allocations: Dict[str, float],
        current_prices: Dict[str, float],
    ) -> List[Dict[str, Any]]:
        portfolio = self._portfolios.get(portfolio_id)
        if not portfolio:
            return []

        _, trades = self.rebalancing_engine.rebalance(
            portfolio, target_allocations, current_prices
        )
        return trades

    def allocate_by_strategy(
        self,
        portfolio_id: str,
        strategy: str,
        symbols: List[str],
        **kwargs: Any,
    ) -> Dict[str, float]:
        strategies = {
            "equal": lambda: self.asset_allocator.equal_weight(symbols),
            "inverse_vol": lambda: self.asset_allocator.inverse_volatility_weight(
                kwargs.get("volatilities", {})
            ),
            "risk_parity": lambda: self.asset_allocator.risk_parity(
                kwargs.get("returns", {})
            ),
            "market_cap": lambda: self.asset_allocator.market_cap_weight(
                kwargs.get("market_caps", {})
            ),
        }

        alloc_fn = strategies.get(strategy)
        if not alloc_fn:
            return {}

        allocation = alloc_fn()
        portfolio = self._portfolios.get(portfolio_id)
        if portfolio:
            allocation = self.asset_allocator.adjust_for_risk_level(
                allocation, portfolio.risk_level
            )
        return allocation

    def get_portfolio_summary(self, portfolio_id: str) -> Optional[Dict[str, Any]]:
        portfolio = self._portfolios.get(portfolio_id)
        if not portfolio:
            return None

        allocations = {}
        total = portfolio.total_value
        for asset in portfolio.assets:
            allocations[asset.symbol] = asset.market_value / total if total > 0 else 0.0

        history = self._value_history.get(portfolio_id, [])

        return {
            "portfolio_id": portfolio.portfolio_id,
            "name": portfolio.name,
            "total_value": total,
            "asset_count": len(portfolio.assets),
            "allocations": allocations,
            "risk_level": portfolio.risk_level.value,
            "risk_metrics": portfolio.risk_metrics.model_dump(),
            "history_length": len(history),
        }

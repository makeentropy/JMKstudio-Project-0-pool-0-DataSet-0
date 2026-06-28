"""
存储池监控和容量管理模块

实现存储池的实时监控、容量预警、使用统计和报告生成功能。
"""

import time
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

from ai_llm_agent_crawler.storage.backends import StorageBackend, StorageInfo
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class AlertLevel(Enum):
    """告警级别"""
    INFO = "info"  # 信息级别
    WARNING = "warning"  # 警告级别
    ERROR = "error"  # 错误级别
    CRITICAL = "critical"  # 严重级别


class MetricType(Enum):
    """指标类型"""
    CAPACITY = "capacity"  # 容量指标
    PERFORMANCE = "performance"  # 性能指标
    HEALTH = "health"  # 健康指标
    USAGE = "usage"  # 使用指标
    ERROR = "error"  # 错误指标


@dataclass
class StorageMetric:
    """存储指标"""
    backend_name: str
    metric_type: MetricType
    name: str
    value: float
    unit: str
    timestamp: float
    tags: Optional[Dict[str, str]] = None


@dataclass
class Alert:
    """告警"""
    backend_name: Optional[str]  # None表示全局告警
    level: AlertLevel
    message: str
    timestamp: float
    metric_name: Optional[str] = None
    metric_value: Optional[float] = None
    threshold: Optional[float] = None
    resolved: bool = False
    resolved_at: Optional[float] = None


@dataclass
class CapacityThreshold:
    """容量阈值配置"""
    warning_percent: float = 70.0  # 警告阈值百分比
    error_percent: float = 85.0  # 错误阈值百分比
    critical_percent: float = 95.0  # 严重阈值百分比
    min_free_space_gb: float = 10.0  # 最小剩余空间（GB）
    check_interval_seconds: int = 60  # 检查间隔（秒）


@dataclass
class MonitoringReport:
    """监控报告"""
    report_time: float
    backend_count: int
    total_capacity: int
    total_used: int
    total_available: int
    average_usage_percent: float
    max_usage_backend: Optional[str]
    min_usage_backend: Optional[str]
    alerts: List[Alert]
    metrics: List[StorageMetric]
    health_status: str  # "healthy", "warning", "critical"
    recommendations: List[str]


class StorageMonitor:
    """
    存储监控器
    
    负责监控存储池的容量、性能和健康状况。
    """
    
    def __init__(
        self,
        threshold: Optional[CapacityThreshold] = None,
        alert_handlers: Optional[List[Callable[[Alert], None]]] = None,
        history_retention_hours: int = 24
    ):
        """
        初始化存储监控器
        
        Args:
            threshold: 容量阈值配置
            alert_handlers: 告警处理函数列表
            history_retention_hours: 历史数据保留时间（小时）
        """
        self.threshold = threshold or CapacityThreshold()
        self.alert_handlers = alert_handlers or []
        self.history_retention_hours = history_retention_hours
        self._backends: Dict[str, StorageBackend] = {}
        self._metrics_history: Dict[str, List[StorageMetric]] = {}  # backend_name -> metrics
        self._alerts: List[Alert] = []
        self._active_alerts: Dict[str, Alert] = {}  # alert_key -> Alert
        self._last_check_time: float = 0
        self.logger = get_logger(f"{__name__}.StorageMonitor")
    
    def register_backend(self, backend: StorageBackend) -> bool:
        """
        注册存储后端
        
        Args:
            backend: 存储后端
            
        Returns:
            注册是否成功
        """
        name = backend.config.name
        if name in self._backends:
            self.logger.warning(f"后端已注册: {name}")
            return False
        
        self._backends[name] = backend
        self._metrics_history[name] = []
        self.logger.info(f"注册后端成功: {name}")
        return True
    
    def unregister_backend(self, name: str) -> bool:
        """
        注销存储后端
        
        Args:
            name: 后端名称
            
        Returns:
            注销是否成功
        """
        if name not in self._backends:
            return False
        
        del self._backends[name]
        if name in self._metrics_history:
            del self._metrics_history[name]
        
        # 清理相关告警
        self._alerts = [a for a in self._alerts if a.backend_name != name]
        
        # 清理活跃告警
        keys_to_remove = [k for k, a in self._active_alerts.items() if a.backend_name == name]
        for key in keys_to_remove:
            del self._active_alerts[key]
        
        self.logger.info(f"注销后端: {name}")
        return True
    
    def get_backend(self, name: str) -> Optional[StorageBackend]:
        """获取指定后端"""
        return self._backends.get(name)
    
    def get_all_backends(self) -> List[StorageBackend]:
        """获取所有后端"""
        return list(self._backends.values())
    
    def check_capacity(self) -> List[Alert]:
        """
        检查容量
        
        Returns:
            告警列表
        """
        new_alerts = []
        
        for name, backend in self._backends.items():
            if not backend.is_connected():
                # 后端未连接告警
                alert = Alert(
                    backend_name=name,
                    level=AlertLevel.ERROR,
                    message=f"存储后端 {name} 未连接",
                    timestamp=time.time(),
                    metric_name="connection",
                    metric_value=0,
                    threshold=1
                )
                new_alerts.append(alert)
                continue
            
            info = backend.get_info()
            
            # 检查使用率
            usage_percent = info.usage_percent
            
            if usage_percent >= self.threshold.critical_percent:
                alert = Alert(
                    backend_name=name,
                    level=AlertLevel.CRITICAL,
                    message=f"存储后端 {name} 容量严重不足: {usage_percent:.1f}%",
                    timestamp=time.time(),
                    metric_name="usage_percent",
                    metric_value=usage_percent,
                    threshold=self.threshold.critical_percent
                )
                new_alerts.append(alert)
            elif usage_percent >= self.threshold.error_percent:
                alert = Alert(
                    backend_name=name,
                    level=AlertLevel.ERROR,
                    message=f"存储后端 {name} 容量告急: {usage_percent:.1f}%",
                    timestamp=time.time(),
                    metric_name="usage_percent",
                    metric_value=usage_percent,
                    threshold=self.threshold.error_percent
                )
                new_alerts.append(alert)
            elif usage_percent >= self.threshold.warning_percent:
                alert = Alert(
                    backend_name=name,
                    level=AlertLevel.WARNING,
                    message=f"存储后端 {name} 容量警告: {usage_percent:.1f}%",
                    timestamp=time.time(),
                    metric_name="usage_percent",
                    metric_value=usage_percent,
                    threshold=self.threshold.warning_percent
                )
                new_alerts.append(alert)
            
            # 检查最小剩余空间
            free_gb = info.available_size / (1024 ** 3)
            if free_gb < self.threshold.min_free_space_gb:
                alert = Alert(
                    backend_name=name,
                    level=AlertLevel.ERROR,
                    message=f"存储后端 {name} 剩余空间不足: {free_gb:.1f}GB",
                    timestamp=time.time(),
                    metric_name="free_space_gb",
                    metric_value=free_gb,
                    threshold=self.threshold.min_free_space_gb
                )
                new_alerts.append(alert)
            
            # 记录指标
            self._record_metrics(name, info)
        
        # 处理告警
        for alert in new_alerts:
            self._handle_alert(alert)
        
        return new_alerts
    
    def collect_metrics(self) -> List[StorageMetric]:
        """
        收集指标
        
        Returns:
            指标列表
        """
        metrics = []
        
        for name, backend in self._backends.items():
            if backend.is_connected():
                info = backend.get_info()
                metrics.extend(self._create_metrics_from_info(name, info))
        
        return metrics
    
    def get_current_status(self) -> Dict[str, Any]:
        """
        获取当前状态
        
        Returns:
            状态字典
        """
        status = {
            "timestamp": time.time(),
            "backend_count": len(self._backends),
            "connected_backends": [],
            "disconnected_backends": [],
            "total_capacity": 0,
            "total_used": 0,
            "total_available": 0,
            "backends": {},
            "active_alerts": [],
            "health_status": "healthy"
        }
        
        usage_rates = []
        
        for name, backend in self._backends.items():
            backend_status = {
                "connected": backend.is_connected(),
                "read_only": backend.config.read_only
            }
            
            if backend.is_connected():
                info = backend.get_info()
                backend_status["total_size"] = info.total_size
                backend_status["used_size"] = info.used_size
                backend_status["available_size"] = info.available_size
                backend_status["usage_percent"] = info.usage_percent
                backend_status["file_count"] = info.file_count
                backend_status["directory_count"] = info.directory_count
                
                status["total_capacity"] += info.total_size
                status["total_used"] += info.used_size
                status["total_available"] += info.available_size
                usage_rates.append(info.usage_percent)
                
                status["connected_backends"].append(name)
            else:
                status["disconnected_backends"].append(name)
            
            status["backends"][name] = backend_status
        
        # 计算平均使用率
        if usage_rates:
            status["average_usage_percent"] = sum(usage_rates) / len(usage_rates)
        else:
            status["average_usage_percent"] = 0
        
        # 确定健康状态
        active_alerts = [a for a in self._alerts if not a.resolved]
        status["active_alerts"] = [
            {
                "backend": a.backend_name,
                "level": a.level.value,
                "message": a.message,
                "timestamp": a.timestamp
            }
            for a in active_alerts
        ]
        
        critical_alerts = [a for a in active_alerts if a.level == AlertLevel.CRITICAL]
        error_alerts = [a for a in active_alerts if a.level == AlertLevel.ERROR]
        
        if critical_alerts:
            status["health_status"] = "critical"
        elif error_alerts or status["disconnected_backends"]:
            status["health_status"] = "warning"
        else:
            status["health_status"] = "healthy"
        
        return status
    
    def generate_report(self) -> MonitoringReport:
        """
        生成监控报告
        
        Returns:
            监控报告
        """
        now = time.time()
        metrics = self.collect_metrics()
        
        # 收集状态信息
        status = self.get_current_status()
        
        # 找出最大和最小使用率的后端
        max_usage_backend = None
        min_usage_backend = None
        max_usage = 0
        min_usage = 100
        
        for name, backend_status in status["backends"].items():
            if backend_status["connected"]:
                usage = backend_status["usage_percent"]
                if usage > max_usage:
                    max_usage = usage
                    max_usage_backend = name
                if usage < min_usage:
                    min_usage = usage
                    min_usage_backend = name
        
        # 生成建议
        recommendations = self._generate_recommendations(status)
        
        return MonitoringReport(
            report_time=now,
            backend_count=status["backend_count"],
            total_capacity=status["total_capacity"],
            total_used=status["total_used"],
            total_available=status["total_available"],
            average_usage_percent=status["average_usage_percent"],
            max_usage_backend=max_usage_backend,
            min_usage_backend=min_usage_backend,
            alerts=[a for a in self._alerts if not a.resolved],
            metrics=metrics,
            health_status=status["health_status"],
            recommendations=recommendations
        )
    
    def get_metrics_history(
        self,
        backend_name: Optional[str] = None,
        metric_type: Optional[MetricType] = None,
        hours: int = 1
    ) -> List[StorageMetric]:
        """
        获取历史指标
        
        Args:
            backend_name: 后端名称
            metric_type: 指标类型
            hours: 获取过去多少小时的数据
            
        Returns:
            指标列表
        """
        now = time.time()
        start_time = now - hours * 3600
        
        if backend_name:
            metrics = self._metrics_history.get(backend_name, [])
        else:
            metrics = []
            for history in self._metrics_history.values():
                metrics.extend(history)
        
        # 过滤时间范围
        filtered = [m for m in metrics if m.timestamp >= start_time]
        
        # 过滤指标类型
        if metric_type:
            filtered = [m for m in filtered if m.metric_type == metric_type]
        
        return sorted(filtered, key=lambda m: m.timestamp)
    
    def get_alerts(
        self,
        level: Optional[AlertLevel] = None,
        resolved: Optional[bool] = None,
        backend_name: Optional[str] = None,
        hours: int = 24
    ) -> List[Alert]:
        """
        获取告警
        
        Args:
            level: 告警级别
            resolved: 是否已解决
            backend_name: 后端名称
            hours: 获取过去多少小时的告警
            
        Returns:
            告警列表
        """
        now = time.time()
        start_time = now - hours * 3600
        
        alerts = [a for a in self._alerts if a.timestamp >= start_time]
        
        if level:
            alerts = [a for a in alerts if a.level == level]
        
        if resolved is not None:
            alerts = [a for a in alerts if a.resolved == resolved]
        
        if backend_name:
            alerts = [a for a in alerts if a.backend_name == backend_name]
        
        return sorted(alerts, key=lambda a: a.timestamp, reverse=True)
    
    def resolve_alert(self, alert_key: str) -> bool:
        """
        解决告警
        
        Args:
            alert_key: 告警键
            
        Returns:
            是否成功
        """
        if alert_key not in self._active_alerts:
            return False
        
        alert = self._active_alerts[alert_key]
        alert.resolved = True
        alert.resolved_at = time.time()
        
        del self._active_alerts[alert_key]
        
        self.logger.info(f"告警已解决: {alert.message}")
        return True
    
    def clear_old_metrics(self) -> int:
        """
        清理旧指标数据
        
        Returns:
            清理的数量
        """
        now = time.time()
        cutoff_time = now - self.history_retention_hours * 3600
        
        count = 0
        for name, metrics in self._metrics_history.items():
            original_count = len(metrics)
            self._metrics_history[name] = [m for m in metrics if m.timestamp >= cutoff_time]
            count += original_count - len(self._metrics_history[name])
        
        # 清理旧告警
        original_alert_count = len(self._alerts)
        self._alerts = [a for a in self._alerts if a.timestamp >= cutoff_time]
        count += original_alert_count - len(self._alerts)
        
        self.logger.debug(f"清理了 {count} 条旧数据")
        return count
    
    def add_alert_handler(self, handler: Callable[[Alert], None]) -> None:
        """
        添加告警处理函数
        
        Args:
            handler: 处理函数
        """
        self.alert_handlers.append(handler)
    
    def _record_metrics(self, backend_name: str, info: StorageInfo) -> None:
        """
        记录指标
        
        Args:
            backend_name: 后端名称
            info: 存储信息
        """
        metrics = self._create_metrics_from_info(backend_name, info)
        
        if backend_name not in self._metrics_history:
            self._metrics_history[backend_name] = []
        
        self._metrics_history[backend_name].extend(metrics)
    
    def _create_metrics_from_info(self, backend_name: str, info: StorageInfo) -> List[StorageMetric]:
        """
        从存储信息创建指标
        
        Args:
            backend_name: 后端名称
            info: 存储信息
            
        Returns:
            指标列表
        """
        now = time.time()
        
        return [
            StorageMetric(
                backend_name=backend_name,
                metric_type=MetricType.CAPACITY,
                name="total_size",
                value=info.total_size,
                unit="bytes",
                timestamp=now
            ),
            StorageMetric(
                backend_name=backend_name,
                metric_type=MetricType.CAPACITY,
                name="used_size",
                value=info.used_size,
                unit="bytes",
                timestamp=now
            ),
            StorageMetric(
                backend_name=backend_name,
                metric_type=MetricType.CAPACITY,
                name="available_size",
                value=info.available_size,
                unit="bytes",
                timestamp=now
            ),
            StorageMetric(
                backend_name=backend_name,
                metric_type=MetricType.USAGE,
                name="usage_percent",
                value=info.usage_percent,
                unit="percent",
                timestamp=now
            ),
            StorageMetric(
                backend_name=backend_name,
                metric_type=MetricType.USAGE,
                name="file_count",
                value=info.file_count,
                unit="count",
                timestamp=now
            ),
            StorageMetric(
                backend_name=backend_name,
                metric_type=MetricType.USAGE,
                name="directory_count",
                value=info.directory_count,
                unit="count",
                timestamp=now
            ),
        ]
    
    def _handle_alert(self, alert: Alert) -> None:
        """
        处理告警
        
        Args:
            alert: 告警
        """
        # 生成告警键
        alert_key = self._generate_alert_key(alert)
        
        # 检查是否已存在相同告警
        existing = self._active_alerts.get(alert_key)
        
        if existing:
            # 更新现有告警
            existing.timestamp = alert.timestamp
            existing.metric_value = alert.metric_value
        else:
            # 新告警
            self._alerts.append(alert)
            self._active_alerts[alert_key] = alert
            
            # 调用处理函数
            for handler in self.alert_handlers:
                try:
                    handler(alert)
                except Exception as e:
                    self.logger.error(f"告警处理函数失败: {e}")
            
            self.logger.warning(f"新告警: [{alert.level.value}] {alert.message}")
    
    def _generate_alert_key(self, alert: Alert) -> str:
        """
        生成告警键
        
        Args:
            alert: 告警
            
        Returns:
            告警键
        """
        return f"{alert.backend_name or 'global'}:{alert.metric_name or 'general'}:{alert.level.value}"
    
    def _generate_recommendations(self, status: Dict[str, Any]) -> List[str]:
        """
        生成建议
        
        Args:
            status: 状态字典
            
        Returns:
            建议列表
        """
        recommendations = []
        
        # 检查容量使用情况
        if status["average_usage_percent"] > self.threshold.warning_percent:
            recommendations.append("建议清理无用数据或扩展存储容量")
        
        # 检查不均衡情况
        backend_usages = [
            (name, info["usage_percent"])
            for name, info in status["backends"].items()
            if info.get("connected", False)
        ]
        
        if backend_usages:
            max_usage = max(u for _, u in backend_usages)
            min_usage = min(u for _, u in backend_usages)
            
            if max_usage - min_usage > 30:
                recommendations.append("存储使用不均衡，建议进行负载均衡或数据迁移")
        
        # 检查未连接的后端
        if status["disconnected_backends"]:
            recommendations.append(f"存在未连接的后端: {status['disconnected_backends']}")
        
        # 检查健康状态
        if status["health_status"] == "critical":
            recommendations.append("系统处于严重状态，请立即处理")
        elif status["health_status"] == "warning":
            recommendations.append("系统处于警告状态，建议尽快处理")
        
        # 检查剩余空间
        free_gb = status["total_available"] / (1024 ** 3)
        if free_gb < self.threshold.min_free_space_gb * 2:
            recommendations.append(f"剩余空间不足{free_gb:.1f}GB，建议清理或扩容")
        
        return recommendations


class CapacityManager:
    """
    容量管理器
    
    负责容量规划、清理策略和扩展管理。
    """
    
    def __init__(
        self,
        monitor: Optional[StorageMonitor] = None,
        auto_cleanup: bool = False,
        cleanup_threshold_percent: float = 90.0
    ):
        """
        初始化容量管理器
        
        Args:
            monitor: 存储监控器
            auto_cleanup: 是否自动清理
            cleanup_threshold_percent: 清理阈值百分比
        """
        self.monitor = monitor or StorageMonitor()
        self.auto_cleanup = auto_cleanup
        self.cleanup_threshold_percent = cleanup_threshold_percent
        self._cleanup_handlers: List[Callable[[str, StorageInfo], int]] = []  # 返回清理的空间大小
        self.logger = get_logger(f"{__name__}.CapacityManager")
    
    def plan_capacity(
        self,
        required_size: int,
        replicas: int = 1,
        growth_factor: float = 1.5
    ) -> Dict[str, Any]:
        """
        容量规划
        
        Args:
            required_size: 需求大小
            replicas: 副本数
            growth_factor: 增长因子
            
        Returns:
            规划结果
        """
        total_required = required_size * replicas * growth_factor
        
        status = self.monitor.get_current_status()
        available = status["total_available"]
        
        # 检查是否满足
        if available >= total_required:
            return {
                "feasible": True,
                "required": int(total_required),
                "available": available,
                "surplus": available - int(total_required),
                "message": "容量充足"
            }
        
        # 计算缺口
        deficit = int(total_required) - available
        
        return {
            "feasible": False,
            "required": int(total_required),
            "available": available,
            "deficit": deficit,
            "recommendations": self._generate_capacity_recommendations(deficit)
        }
    
    def estimate_growth(
        self,
        days: int = 30,
        based_on_history: bool = True
    ) -> Dict[str, Any]:
        """
        估算容量增长
        
        Args:
            days: 预测天数
            based_on_history: 是否基于历史数据
            
        Returns:
            估算结果
        """
        status = self.monitor.get_current_status()
        current_used = status["total_used"]
        
        if based_on_history:
            # 基于历史数据估算增长率
            metrics = self.monitor.get_metrics_history(metric_type=MetricType.CAPACITY, hours=24)
            
            if len(metrics) >= 2:
                # 计算增长率
                oldest = metrics[0]
                newest = metrics[-1]
                
                hours_elapsed = (newest.timestamp - oldest.timestamp) / 3600
                if hours_elapsed > 0:
                    growth_rate = (newest.value - oldest.value) / hours_elapsed  # bytes/hour
                    
                    # 预估未来增长
                    predicted_growth = growth_rate * days * 24
                    
                    return {
                        "current_used": current_used,
                        "growth_rate_per_hour": growth_rate,
                        "predicted_growth": int(predicted_growth),
                        "predicted_total": int(current_used + predicted_growth),
                        "days": days,
                        "confidence": "medium"  # 基于历史数据，置信度中等
                    }
        
        # 如果没有足够历史数据，使用默认增长率估算
        # 假设每天增长10%的已使用容量
        daily_growth_rate = 0.10
        predicted_growth = current_used * daily_growth_rate * days
        
        return {
            "current_used": current_used,
            "growth_rate_per_day": daily_growth_rate,
            "predicted_growth": int(predicted_growth),
            "predicted_total": int(current_used + predicted_growth),
            "days": days,
            "confidence": "low"  # 基于估算，置信度低
        }
    
    def cleanup_storage(
        self,
        backend_name: Optional[str] = None,
        force: bool = False
    ) -> Dict[str, int]:
        """
        清理存储
        
        Args:
            backend_name: 后端名称，None表示清理所有
            force: 是否强制清理
            
        Returns:
            每个后端清理的空间大小
        """
        results = {}
        
        backends_to_cleanup = []
        if backend_name:
            backend = self.monitor.get_backend(backend_name)
            if backend:
                backends_to_cleanup = [backend]
        else:
            backends_to_cleanup = self.monitor.get_all_backends()
        
        for backend in backends_to_cleanup:
            name = backend.config.name
            
            if not backend.is_connected():
                results[name] = 0
                continue
            
            info = backend.get_info()
            
            # 检查是否需要清理
            if not force and info.usage_percent < self.cleanup_threshold_percent:
                results[name] = 0
                continue
            
            # 执行清理
            cleaned = 0
            for handler in self._cleanup_handlers:
                try:
                    cleaned += handler(name, info)
                except Exception as e:
                    self.logger.error(f"清理处理函数失败 {name}: {e}")
            
            results[name] = cleaned
            
            if cleaned > 0:
                self.logger.info(f"清理了 {name} 上的 {cleaned} 字节空间")
        
        return results
    
    def add_cleanup_handler(self, handler: Callable[[str, StorageInfo], int]) -> None:
        """
        添加清理处理函数
        
        Args:
            handler: 处理函数，返回清理的空间大小
        """
        self._cleanup_handlers.append(handler)
    
    def get_capacity_summary(self) -> Dict[str, Any]:
        """
        获取容量摘要
        
        Returns:
            摘要字典
        """
        status = self.monitor.get_current_status()
        estimate = self.estimate_growth(days=30)
        
        # 计算容量状态
        usage_percent = status["average_usage_percent"]
        
        if usage_percent >= 95:
            capacity_status = "critical"
        elif usage_percent >= 85:
            capacity_status = "warning"
        elif usage_percent >= 70:
            capacity_status = "moderate"
        else:
            capacity_status = "healthy"
        
        return {
            "current": {
                "total_capacity": status["total_capacity"],
                "total_used": status["total_used"],
                "total_available": status["total_available"],
                "usage_percent": usage_percent,
                "backend_count": status["backend_count"],
                "connected_count": len(status["connected_backends"])
            },
            "prediction": {
                "growth_30_days": estimate["predicted_growth"],
                "total_after_30_days": estimate["predicted_total"],
                "confidence": estimate["confidence"]
            },
            "status": capacity_status,
            "thresholds": {
                "warning": self.monitor.threshold.warning_percent,
                "error": self.monitor.threshold.error_percent,
                "critical": self.monitor.threshold.critical_percent
            }
        }
    
    def _generate_capacity_recommendations(self, deficit: int) -> List[str]:
        """
        生成容量建议
        
        Args:
            deficit: 缺口大小
            
        Returns:
            建议列表
        """
        recommendations = []
        
        deficit_gb = deficit / (1024 ** 3)
        
        recommendations.append(f"需要增加 {deficit_gb:.1f}GB 存储容量")
        
        # 检查是否可以清理
        status = self.monitor.get_current_status()
        if status["average_usage_percent"] > self.monitor.threshold.warning_percent:
            recommendations.append("建议先清理无用数据，释放空间")
        
        # 建议添加新后端
        recommendations.append("建议添加新的存储后端或扩展现有后端")
        
        # 建议减少副本数
        recommendations.append("考虑减少副本数以节省空间（如果允许）")
        
        return recommendations
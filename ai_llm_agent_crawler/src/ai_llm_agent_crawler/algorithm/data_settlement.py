"""
数据清算分析模块

对两个数据集 (或数据版本) 进行对账/清算:
- 以主键 (key) 对账, 计算 added / removed / modified / unchanged
- 计算字段级差异 (哪些字段变化)
- 生成结算报告 (settlement report): 净变更量、变更率、一致性评分
- 支持数值字段的"余额"清算 (求和对比, 计算差额)

适用场景: 版本间数据清算、爬虫数据增量对账、训练集漂移检测、
NAS 存储池副本一致性清算。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Sequence, Set, Tuple, Union

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.logging import get_logger

if TYPE_CHECKING:
    import pandas as pd

logger = get_logger(__name__)


class SettlementStatus(str, Enum):
    """清算状态。"""

    BALANCED = "balanced"  # 平衡 (无差异或差异在容差内)
    UNBALANCED = "unbalanced"  # 不平衡 (存在差异)
    ERROR = "error"  # 错误


@dataclass
class FieldDiff:
    """字段级差异。"""

    field: str
    left_value: Any = None
    right_value: Any = None


@dataclass
class RowSettlement:
    """单行清算结果。"""

    key: Any
    status: str  # added | removed | modified | unchanged
    field_diffs: List[FieldDiff] = field(default_factory=list)


class SettlementReport(BaseModel):
    """清算报告。"""

    left_name: str = Field(default="left", description="左侧数据集名")
    right_name: str = Field(default="right", description="右侧数据集名")
    key_column: str = Field(default="id", description="对账主键列")

    # 计数
    left_count: int = Field(default=0)
    right_count: int = Field(default=0)
    added: int = Field(default=0, description="右侧新增")
    removed: int = Field(default=0, description="右侧删除")
    modified: int = Field(default=0, description="修改")
    unchanged: int = Field(default=0, description="未变")

    # 变更率
    change_rate: float = Field(default=0.0, description="变更率 (added+removed+modified)/max(left,right)")
    consistency_score: float = Field(default=0.0, description="一致性评分 (unchanged / total)")

    # 数值清算 (可选)
    numeric_clearing: Dict[str, Dict[str, float]] = Field(
        default_factory=dict,
        description="数值字段清算: {field: {left_sum, right_sum, delta}}",
    )

    status: str = Field(default=SettlementStatus.BALANCED.value)
    generated_at: datetime = Field(default_factory=datetime.now)
    details: List[Dict[str, Any]] = Field(default_factory=list, description="明细 (可选, 大数据集建议省略)")


class DataSettlement:
    """
    数据清算器

    Example:
        >>> left = pd.DataFrame({"id": [1, 2, 3], "v": [10, 20, 30]})
        >>> right = pd.DataFrame({"id": [2, 3, 4], "v": [20, 31, 40]})
        >>> settler = DataSettlement()
        >>> report = settler.settle(left, right, key="id")
        >>> print(report.status, report.change_rate)
    """

    def __init__(self, tolerance: float = 0.0, include_details: bool = False) -> None:
        """
        Args:
            tolerance: 数值字段容差 (|left-right| <= tolerance 视为 unchanged)
            include_details: 是否在报告中包含逐行明细
        """
        self.tolerance = tolerance
        self.include_details = include_details

    def settle(
        self,
        left: pd.DataFrame,
        right: pd.DataFrame,
        key: str = "id",
        left_name: str = "left",
        right_name: str = "right",
        numeric_fields: Optional[List[str]] = None,
    ) -> SettlementReport:
        """
        执行清算。

        Args:
            left: 左侧 (基准) 数据集
            right: 右侧 (对照) 数据集
            key: 对账主键列
            left_name / right_name: 名称标签
            numeric_fields: 需要求和清算的数值字段 (None 则自动选数值列交集)
        """
        if key not in left.columns or key not in right.columns:
            raise ValueError(f"主键列 '{key}' 必须在两侧均存在")

        left_keys: Set[Any] = set(left[key].tolist())
        right_keys: Set[Any] = set(right[key].tolist())
        common = left_keys & right_keys
        added = right_keys - left_keys
        removed = left_keys - right_keys

        # 索引化便于查找
        left_indexed = left.set_index(key)
        right_indexed = right.set_index(key)

        # 公共列比较
        common_cols = [c for c in left.columns if c in right.columns and c != key]

        modified = 0
        unchanged = 0
        details: List[Dict[str, Any]] = []
        row_settlements: List[RowSettlement] = []

        for k in common:
            lrow = left_indexed.loc[k]
            rrow = right_indexed.loc[k]
            field_diffs: List[FieldDiff] = []
            is_modified = False
            for col in common_cols:
                lv = lrow[col] if col in lrow.index else None
                rv = rrow[col] if col in rrow.index else None
                if not _values_equal(lv, rv, self.tolerance):
                    is_modified = True
                    field_diffs.append(FieldDiff(field=col, left_value=lv, right_value=rv))
            status = "modified" if is_modified else "unchanged"
            if is_modified:
                modified += 1
            else:
                unchanged += 1
            row_settlements.append(RowSettlement(key=k, status=status, field_diffs=field_diffs))
            if self.include_details:
                details.append({
                    "key": k,
                    "status": status,
                    "diffs": [
                        {"field": d.field, "left": d.left_value, "right": d.right_value}
                        for d in field_diffs
                    ],
                })

        max_count = max(len(left_keys), len(right_keys)) or 1
        total = len(common) or 1
        change_rate = (len(added) + len(removed) + modified) / max_count
        consistency = unchanged / total

        # 数值清算
        import pandas as pd  # 延迟导入, 避免未使用清算功能时强依赖 pandas

        numeric_clearing: Dict[str, Dict[str, float]] = {}
        if numeric_fields is None:
            numeric_cols_left = set(left.select_dtypes(include="number").columns) - {key}
            numeric_cols_right = set(right.select_dtypes(include="number").columns) - {key}
            numeric_fields = list(numeric_cols_left & numeric_cols_right)
        for fld in numeric_fields:
            if fld in left.columns and fld in right.columns:
                lsum = float(pd.to_numeric(left[fld], errors="coerce").fillna(0).sum())
                rsum = float(pd.to_numeric(right[fld], errors="coerce").fillna(0).sum())
                numeric_clearing[fld] = {
                    "left_sum": lsum,
                    "right_sum": rsum,
                    "delta": rsum - lsum,
                }

        status = SettlementStatus.BALANCED.value
        if (len(added) + len(removed) + modified) > 0:
            status = SettlementStatus.UNBALANCED.value

        report = SettlementReport(
            left_name=left_name,
            right_name=right_name,
            key_column=key,
            left_count=len(left_keys),
            right_count=len(right_keys),
            added=len(added),
            removed=len(removed),
            modified=modified,
            unchanged=unchanged,
            change_rate=change_rate,
            consistency_score=consistency,
            numeric_clearing=numeric_clearing,
            status=status,
            details=details,
        )
        logger.info(
            f"数据清算完成: {left_name} vs {right_name} "
            f"(added={len(added)} removed={len(removed)} modified={modified} unchanged={unchanged})"
        )
        return report

    def settle_files(
        self,
        left_path: str,
        right_path: str,
        key: str = "id",
        **read_kwargs: Any,
    ) -> SettlementReport:
        """从文件加载并清算 (支持 csv/parquet, 按扩展名判断)。"""
        left = _load_table(left_path, **read_kwargs)
        right = _load_table(right_path, **read_kwargs)
        return self.settle(left, right, key=key, left_name=left_path, right_name=right_path)

    def summary(self, report: SettlementReport) -> str:
        """人类可读的清算摘要。"""
        lines = [
            f"=== 数据清算报告: {report.left_name} vs {report.right_name} ===",
            f"主键: {report.key_column}",
            f"左侧行数: {report.left_count} | 右侧行数: {report.right_count}",
            f"新增: {report.added} | 删除: {report.removed} | 修改: {report.modified} | 未变: {report.unchanged}",
            f"变更率: {report.change_rate:.2%} | 一致性: {report.consistency_score:.2%}",
            f"状态: {report.status}",
        ]
        for fld, vals in report.numeric_clearing.items():
            lines.append(
                f"  数值清算[{fld}]: 左={vals['left_sum']} 右={vals['right_sum']} 差额={vals['delta']}"
            )
        return "\n".join(lines)


# ---------- 辅助函数 ----------

def _values_equal(a: Any, b: Any, tolerance: float) -> bool:
    """值比较, 支持数值容差。"""
    if a is None and b is None:
        return True
    if a is None or b is None:
        return False
    try:
        fa = float(a)
        fb = float(b)
        return abs(fa - fb) <= tolerance
    except (TypeError, ValueError):
        return a == b


def _load_table(path: str, **kwargs: Any) -> "pd.DataFrame":
    """按扩展名加载表格。"""
    import pandas as pd  # 延迟导入

    p = str(path).lower()
    if p.endswith(".parquet"):
        return pd.read_parquet(path, **kwargs)
    if p.endswith((".xlsx", ".xls")):
        return pd.read_excel(path, **kwargs)
    return pd.read_csv(path, **kwargs)


__all__ = [
    "SettlementStatus",
    "FieldDiff",
    "RowSettlement",
    "SettlementReport",
    "DataSettlement",
]

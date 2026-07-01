"""
DataSciTalk 数据对话模块

提供自然语言与数据集交互的能力，支持：
- 自然语言数据查询
- 智能数据分析
- 可视化建议
- 数据洞察生成
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Union

import pandas as pd
from pydantic import BaseModel, Field

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class ChatRole(str, Enum):
    """对话角色"""

    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class QueryType(str, Enum):
    """查询类型"""

    DATA_RETRIEVAL = "data_retrieval"
    STATISTICAL_ANALYSIS = "statistical_analysis"
    VISUALIZATION = "visualization"
    DATA_CLEANING = "data_cleaning"
    FEATURE_ENGINEERING = "feature_engineering"
    MODEL_TRAINING = "model_training"
    INSIGHT_DISCOVERY = "insight_discovery"
    GENERAL_QUESTION = "general_question"


class ChatMessage(BaseModel):
    """对话消息"""

    message_id: str = Field(default_factory=lambda: f"msg_{uuid.uuid4().hex[:8]}")
    role: str
    content: str
    timestamp: datetime = Field(default_factory=datetime.now)
    query_type: Optional[str] = None
    tool_calls: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class ChatContext(BaseModel):
    """对话上下文"""

    conversation_id: str = Field(default_factory=lambda: f"conv_{uuid.uuid4().hex[:8]}")
    messages: List[ChatMessage] = Field(default_factory=list)
    dataset_refs: List[str] = Field(default_factory=list)
    current_dataset: Optional[str] = None
    variables: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    last_updated: datetime = Field(default_factory=datetime.now)

    class Config:
        arbitrary_types_allowed = True


class DataSciTalkConfig(BaseModel):
    """DataSciTalk 配置"""

    max_history_messages: int = 50
    enable_code_execution: bool = True
    enable_visualization: bool = True
    enable_auto_insight: bool = True
    max_query_retries: int = 3
    response_timeout_seconds: int = 60
    default_language: str = "zh-CN"

    class Config:
        arbitrary_types_allowed = True


class QueryIntent(BaseModel):
    """查询意图"""

    query_type: str
    confidence: float = 0.0
    entities: Dict[str, Any] = Field(default_factory=dict)
    target_columns: List[str] = Field(default_factory=list)
    target_metrics: List[str] = Field(default_factory=list)
    filters: Dict[str, Any] = Field(default_factory=dict)
    raw_query: str = ""


class QueryResult(BaseModel):
    """查询结果"""

    success: bool
    query: str
    query_type: Optional[str] = None
    result_data: Any = None
    result_summary: str = ""
    visualization_suggestions: List[Dict[str, Any]] = Field(default_factory=list)
    insights: List[str] = Field(default_factory=list)
    error_message: Optional[str] = None
    execution_time_seconds: float = 0.0
    follow_up_questions: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        arbitrary_types_allowed = True


class IntentRecognizer:
    """
    意图识别器

    识别用户自然语言查询的意图和实体。
    """

    def __init__(self):
        """初始化意图识别器"""
        self.logger = get_logger(f"{__name__}.IntentRecognizer")
        self._keyword_mappings = self._build_keyword_mappings()

    def _build_keyword_mappings(self) -> Dict[str, List[str]]:
        """构建关键词映射"""
        return {
            QueryType.DATA_RETRIEVAL: [
                "查询", "获取", "查看", "显示", "列出", "检索", "找", "筛选",
                "select", "get", "list", "show", "find", "filter", "retrieve",
            ],
            QueryType.STATISTICAL_ANALYSIS: [
                "统计", "分析", "计算", "平均值", "中位数", "标准差", "方差",
                "相关", "分布", "频率", "汇总", "描述",
                "stat", "statistics", "analyze", "average", "mean", "median",
                "correlation", "distribution",
            ],
            QueryType.VISUALIZATION: [
                "图表", "可视化", "画图", "绘图", "折线图", "柱状图", "饼图",
                "散点图", "热力图", "直方图",
                "chart", "plot", "graph", "visualize", "visualization",
                "bar", "line", "pie", "scatter", "histogram",
            ],
            QueryType.DATA_CLEANING: [
                "清洗", "去重", "缺失值", "空值", "异常值", "预处理", "清理",
                "clean", "preprocess", "missing", "duplicate", "outlier",
                "null", "nan",
            ],
            QueryType.FEATURE_ENGINEERING: [
                "特征", "工程", "转换", "编码", "标准化", "归一化", "降维",
                "feature", "engineering", "transform", "encode", "normalize",
                "standardize", "dimensionality",
            ],
            QueryType.MODEL_TRAINING: [
                "训练", "模型", "预测", "分类", "回归", "聚类", "机器学习",
                "train", "model", "predict", "classify", "regression",
                "cluster", "ml", "machine learning",
            ],
            QueryType.INSIGHT_DISCOVERY: [
                "洞察", "发现", "规律", "趋势", "异常", "模式", "关键",
                "insight", "discover", "pattern", "trend", "anomaly",
                "key", "important",
            ],
        }

    def recognize(self, query: str, context: Optional[ChatContext] = None) -> QueryIntent:
        """
        识别查询意图

        Args:
            query: 用户查询
            context: 对话上下文

        Returns:
            查询意图
        """
        query_lower = query.lower()
        scores: Dict[str, int] = {}

        for query_type, keywords in self._keyword_mappings.items():
            score = sum(1 for kw in keywords if kw.lower() in query_lower)
            if score > 0:
                scores[query_type] = score

        if scores:
            best_type = max(scores, key=scores.get)
            max_score = scores[best_type]
            total_score = sum(scores.values())
            confidence = max_score / total_score if total_score > 0 else 0.0
        else:
            best_type = QueryType.GENERAL_QUESTION
            confidence = 0.5

        entities = self._extract_entities(query)
        target_columns = self._extract_column_names(query)

        intent = QueryIntent(
            query_type=best_type,
            confidence=confidence,
            entities=entities,
            target_columns=target_columns,
            raw_query=query,
        )

        self.logger.debug(f"意图识别: {best_type} (置信度={confidence:.2f})")
        return intent

    def _extract_entities(self, query: str) -> Dict[str, Any]:
        """提取实体"""
        entities = {}

        import re

        number_pattern = r'\d+\.?\d*'
        numbers = re.findall(number_pattern, query)
        if numbers:
            entities["numbers"] = [float(n) if '.' in n else int(n) for n in numbers]

        date_pattern = r'\d{4}[-/年]\d{1,2}[-/月]\d{1,2}[日号]?'
        dates = re.findall(date_pattern, query)
        if dates:
            entities["dates"] = dates

        return entities

    def _extract_column_names(self, query: str) -> List[str]:
        """提取可能的列名"""
        import re

        quoted_pattern = r'["\']([^"\']+)["\']'
        quoted = re.findall(quoted_pattern, query)

        return list(set(quoted))


class DataQueryEngine:
    """
    数据查询引擎

    根据意图执行实际的数据查询和分析。
    """

    def __init__(self):
        """初始化数据查询引擎"""
        self.logger = get_logger(f"{__name__}.DataQueryEngine")
        self._datasets: Dict[str, pd.DataFrame] = {}
        self._schemas: Dict[str, Any] = {}

    def register_dataset(self, name: str, dataset: pd.DataFrame, schema: Any = None) -> None:
        """
        注册数据集

        Args:
            name: 数据集名称
            dataset: 数据集
            schema: 数据集模式
        """
        self._datasets[name] = dataset
        if schema:
            self._schemas[name] = schema
        self.logger.info(f"数据集已注册到 DataSciTalk: {name} ({len(dataset)} 行)")

    def execute_query(
        self,
        intent: QueryIntent,
        dataset_name: Optional[str] = None,
    ) -> QueryResult:
        """
        执行查询

        Args:
            intent: 查询意图
            dataset_name: 目标数据集名称

        Returns:
            查询结果
        """
        start_time = datetime.now()

        try:
            if dataset_name and dataset_name in self._datasets:
                df = self._datasets[dataset_name]
            elif self._datasets:
                dataset_name = next(iter(self._datasets))
                df = self._datasets[dataset_name]
            else:
                return QueryResult(
                    success=False,
                    query=intent.raw_query,
                    query_type=intent.query_type,
                    error_message="No dataset available",
                )

            result_data = None
            summary = ""
            insights = []
            viz_suggestions = []

            if intent.query_type == QueryType.DATA_RETRIEVAL:
                result_data = self._retrieve_data(df, intent)
                summary = f"查询到 {len(result_data) if hasattr(result_data, '__len__') else 'N/A'} 条记录"

            elif intent.query_type == QueryType.STATISTICAL_ANALYSIS:
                result_data = self._statistical_analysis(df, intent)
                summary = "统计分析完成"
                insights = self._generate_statistics_insights(df, result_data)

            elif intent.query_type == QueryType.DATA_CLEANING:
                result_data = self._clean_data(df, intent)
                summary = f"数据清洗完成，处理了 {len(df)} 条记录"

            elif intent.query_type == QueryType.INSIGHT_DISCOVERY:
                result_data, insights = self._discover_insights(df, intent)
                summary = f"发现 {len(insights)} 条洞察"

            else:
                result_data = df.describe()
                summary = "已生成数据集基本描述"

            viz_suggestions = self._suggest_visualizations(df, intent)

            follow_ups = self._generate_follow_up_questions(intent, df)

            return QueryResult(
                success=True,
                query=intent.raw_query,
                query_type=intent.query_type,
                result_data=result_data,
                result_summary=summary,
                visualization_suggestions=viz_suggestions,
                insights=insights,
                execution_time_seconds=(datetime.now() - start_time).total_seconds(),
                follow_up_questions=follow_ups,
            )

        except Exception as e:
            self.logger.error(f"查询执行失败: {e}", exc_info=True)
            return QueryResult(
                success=False,
                query=intent.raw_query,
                query_type=intent.query_type,
                error_message=str(e),
                execution_time_seconds=(datetime.now() - start_time).total_seconds(),
            )

    def _retrieve_data(self, df: pd.DataFrame, intent: QueryIntent) -> pd.DataFrame:
        """数据检索"""
        result = df.head(20)
        return result

    def _statistical_analysis(self, df: pd.DataFrame, intent: QueryIntent) -> Dict[str, Any]:
        """统计分析"""
        stats = {}
        numeric_cols = df.select_dtypes(include=['number']).columns

        for col in numeric_cols[:5]:
            stats[col] = {
                "count": int(df[col].count()),
                "mean": float(df[col].mean()) if df[col].count() > 0 else 0,
                "std": float(df[col].std()) if df[col].count() > 1 else 0,
                "min": float(df[col].min()) if df[col].count() > 0 else 0,
                "max": float(df[col].max()) if df[col].count() > 0 else 0,
                "median": float(df[col].median()) if df[col].count() > 0 else 0,
            }

        return stats

    def _clean_data(self, df: pd.DataFrame, intent: QueryIntent) -> pd.DataFrame:
        """数据清洗"""
        cleaned = df.copy()
        cleaned = cleaned.drop_duplicates()
        return cleaned

    def _discover_insights(
        self,
        df: pd.DataFrame,
        intent: QueryIntent,
    ) -> tuple:
        """发现洞察"""
        insights = []
        result_data = {}

        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            for col in numeric_cols[:3]:
                if df[col].count() > 0:
                    mean_val = df[col].mean()
                    insights.append(f"列 '{col}' 的平均值为 {mean_val:.2f}")

        categorical_cols = df.select_dtypes(include=['object', 'category']).columns
        if len(categorical_cols) > 0:
            for col in categorical_cols[:2]:
                unique_count = df[col].nunique()
                insights.append(f"列 '{col}' 有 {unique_count} 个不同值")

        result_data["insight_count"] = len(insights)
        return result_data, insights

    def _generate_statistics_insights(
        self,
        df: pd.DataFrame,
        stats: Dict[str, Any],
    ) -> List[str]:
        """生成统计洞察"""
        insights = []
        for col, col_stats in stats.items():
            if col_stats.get("std", 0) > col_stats.get("mean", 1) * 0.5:
                insights.append(f"列 '{col}' 数据分布较分散（标准差较大）")
        return insights

    def _suggest_visualizations(
        self,
        df: pd.DataFrame,
        intent: QueryIntent,
    ) -> List[Dict[str, Any]]:
        """建议可视化方案"""
        suggestions = []
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()

        if len(numeric_cols) >= 2:
            suggestions.append({
                "type": "scatter",
                "name": "散点图",
                "x": numeric_cols[0],
                "y": numeric_cols[1],
                "purpose": "查看两个数值变量之间的关系",
            })

        if len(numeric_cols) >= 1:
            suggestions.append({
                "type": "histogram",
                "name": "直方图",
                "column": numeric_cols[0],
                "purpose": "查看数值分布",
            })

        if len(categorical_cols) >= 1 and len(numeric_cols) >= 1:
            suggestions.append({
                "type": "bar",
                "name": "柱状图",
                "x": categorical_cols[0],
                "y": numeric_cols[0],
                "purpose": "按类别比较数值",
            })

        return suggestions

    def _generate_follow_up_questions(
        self,
        intent: QueryIntent,
        df: pd.DataFrame,
    ) -> List[str]:
        """生成后续问题建议"""
        questions = []

        if intent.query_type == QueryType.DATA_RETRIEVAL:
            questions.append("需要进行统计分析吗？")
            questions.append("要查看数据可视化吗？")
        elif intent.query_type == QueryType.STATISTICAL_ANALYSIS:
            questions.append("需要生成可视化图表吗？")
            questions.append("要进一步探索数据洞察吗？")
        elif intent.query_type == QueryType.VISUALIZATION:
            questions.append("需要保存图表吗？")
            questions.append("还需要其他类型的图表吗？")

        return questions[:3]


class DataSciTalkAgent:
    """
    DataSciTalk 数据对话 Agent

    提供自然语言与数据集交互的完整功能。
    """

    def __init__(self, config: Optional[DataSciTalkConfig] = None):
        """
        初始化 DataSciTalk Agent

        Args:
            config: 配置
        """
        self.config = config or DataSciTalkConfig()
        self.intent_recognizer = IntentRecognizer()
        self.query_engine = DataQueryEngine()
        self._conversations: Dict[str, ChatContext] = {}
        self.logger = get_logger(f"{__name__}.DataSciTalkAgent")

    def start_conversation(
        self,
        dataset_name: Optional[str] = None,
    ) -> ChatContext:
        """
        开始新对话

        Args:
            dataset_name: 关联的数据集名称

        Returns:
            对话上下文
        """
        context = ChatContext()
        if dataset_name:
            context.dataset_refs.append(dataset_name)
            context.current_dataset = dataset_name

        self._conversations[context.conversation_id] = context

        system_msg = ChatMessage(
            role=ChatRole.SYSTEM,
            content="你好！我是数据科学助手。你可以用自然语言询问关于数据集的问题，我会帮你分析和可视化数据。",
        )
        context.messages.append(system_msg)

        self.logger.info(f"新对话已开始: {context.conversation_id}")
        return context

    def chat(
        self,
        conversation_id: str,
        user_message: str,
        dataset_name: Optional[str] = None,
    ) -> ChatMessage:
        """
        发送消息并获取回复

        Args:
            conversation_id: 对话 ID
            user_message: 用户消息
            dataset_name: 指定数据集

        Returns:
            回复消息
        """
        context = self._conversations.get(conversation_id)
        if not context:
            context = self.start_conversation(dataset_name)

        if dataset_name and dataset_name not in context.dataset_refs:
            context.dataset_refs.append(dataset_name)
            context.current_dataset = dataset_name

        user_msg = ChatMessage(
            role=ChatRole.USER,
            content=user_message,
        )
        context.messages.append(user_msg)

        intent = self.intent_recognizer.recognize(user_message, context)
        user_msg.query_type = intent.query_type

        target_ds = dataset_name or context.current_dataset
        query_result = self.query_engine.execute_query(intent, target_ds)

        reply_content = self._build_reply(query_result)

        assistant_msg = ChatMessage(
            role=ChatRole.ASSISTANT,
            content=reply_content,
            query_type=intent.query_type,
            metadata={"query_result": query_result.model_dump(mode="json") if hasattr(query_result, 'model_dump') else str(query_result)},
        )
        context.messages.append(assistant_msg)

        if len(context.messages) > self.config.max_history_messages:
            context.messages = context.messages[-self.config.max_history_messages:]

        context.last_updated = datetime.now()

        self.logger.info(f"对话回复: {conversation_id}, 意图={intent.query_type}")
        return assistant_msg

    def _build_reply(self, result: QueryResult) -> str:
        """构建回复内容"""
        if not result.success:
            return f"抱歉，处理你的查询时出现错误：{result.error_message}"

        parts = [result.result_summary]

        if result.insights:
            parts.append("\n🔍 关键洞察：")
            for i, insight in enumerate(result.insights[:5], 1):
                parts.append(f"  {i}. {insight}")

        if result.visualization_suggestions:
            parts.append("\n📊 可视化建议：")
            for viz in result.visualization_suggestions[:3]:
                parts.append(f"  - {viz['name']}: {viz.get('purpose', '')}")

        if result.follow_up_questions:
            parts.append("\n💡 你可能还想知道：")
            for q in result.follow_up_questions:
                parts.append(f"  - {q}")

        return "\n".join(parts)

    def register_dataset(self, name: str, dataset: pd.DataFrame, schema: Any = None) -> None:
        """注册数据集"""
        self.query_engine.register_dataset(name, dataset, schema)

    def get_conversation(self, conversation_id: str) -> Optional[ChatContext]:
        """获取对话上下文"""
        return self._conversations.get(conversation_id)

    def list_conversations(self) -> List[Dict[str, Any]]:
        """列出所有对话"""
        return [
            {
                "conversation_id": c.conversation_id,
                "message_count": len(c.messages),
                "datasets": c.dataset_refs,
                "created_at": c.created_at,
                "last_updated": c.last_updated,
            }
            for c in self._conversations.values()
        ]

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "total_conversations": len(self._conversations),
            "total_messages": sum(len(c.messages) for c in self._conversations.values()),
            "datasets_registered": len(self.query_engine._datasets),
            "config": self.config.model_dump(mode="json") if hasattr(self.config, 'model_dump') else {},
        }

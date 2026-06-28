"""
微信数据爬取模块（模拟方式）

本模块设计用于研究微信数据采集的架构和技术方案。
重要说明：
- 本模块采用模拟方式实现，不实际爬取微信数据
- 微信数据爬取涉及用户隐私和法律风险
- 实际使用应遵循微信平台政策和相关法律法规
- 建议使用官方授权的数据接口或用户授权的方式获取数据

提供：
- 微信聊天记录爬取架构（模拟）
- 微信公众号文章爬取（公开网页抓取）
"""

import asyncio
import hashlib
import random
import re
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, Union

from pydantic import BaseModel, Field

from ai_llm_agent_crawler.crawler.base import (
    CrawlerCapability,
    CrawlerConfig,
    CrawlError,
    CrawlResult,
    DataSourceType,
    SourceSpecificCrawler,
)
from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class WeChatMessageType(str, Enum):
    """微信消息类型枚举"""
    
    TEXT = "text"                    # 文本消息
    IMAGE = "image"                  # 图片消息
    VOICE = "voice"                  # 语音消息
    VIDEO = "video"                  # 视频消息
    FILE = "file"                    # 文件消息
    LOCATION = "location"            # 位置消息
    LINK = "link"                    # 链接消息
    CARD = "card"                    # 名片消息
    EMOJI = "emoji"                  # 表情消息
    SYSTEM = "system"                # 系统消息
    RECALL = "recall"                # 撤回消息


class WeChatChatType(str, Enum):
    """聊天类型枚举"""
    
    PRIVATE = "private"              # 私聊
    GROUP = "group"                  # 聊
    OFFICIAL_ACCOUNT = "official"    # 公众号


class WeChatMessage(BaseModel):
    """微信消息模型（模拟数据结构）"""
    
    # 消息标识
    message_id: str = Field(description="消息ID")
    sequence_id: int = Field(default=0, description="消息序号")
    
    # 消息类型
    message_type: WeChatMessageType = Field(description="消息类型")
    chat_type: WeChatChatType = Field(default=WeChatChatType.PRIVATE, description="聊天类型")
    
    # 发送者信息
    sender_id: str = Field(description="发送者ID")
    sender_name: str = Field(default="", description="发送者昵称")
    sender_avatar: Optional[str] = Field(default=None, description="发送者头像URL")
    
    # 接收者信息
    receiver_id: str = Field(description="接收者ID")
    receiver_name: str = Field(default="", description="接收者昵称")
    
    # 聊天信息（群聊）
    chat_id: Optional[str] = Field(default=None, description="聊天/群ID")
    chat_name: Optional[str] = Field(default=None, description="聊天/群名称")
    
    # 消息内容
    content: str = Field(default="", description="消息内容")
    content_url: Optional[str] = Field(default=None, description="内容链接（图片、视频等）")
    content_thumbnail: Optional[str] = Field(default=None, description="内容缩略图")
    
    # 链接消息额外信息
    link_title: Optional[str] = Field(default=None, description="链接标题")
    link_description: Optional[str] = Field(default=None, description="链接描述")
    link_url: Optional[str] = Field(default=None, description="链接URL")
    
    # 时间信息
    send_time: str = Field(description="发送时间")
    create_time: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="创建时间",
    )
    
    # 元数据
    extra_info: Dict[str, Any] = Field(default_factory=dict, description="额外信息")
    
    # 数据来源标记
    source_type: DataSourceType = Field(
        default=DataSourceType.WECHAT_CHAT,
        description="数据源类型",
    )
    is_simulated: bool = Field(default=True, description="是否为模拟数据")
    
    class Config:
        use_enum_values = True


class WeChatChatSession(BaseModel):
    """微信聊天会话模型"""
    
    # 会话标识
    session_id: str = Field(description="会话ID")
    chat_type: WeChatChatType = Field(description="聊天类型")
    
    # 会话信息
    chat_name: str = Field(default="", description="聊天名称")
    chat_avatar: Optional[str] = Field(default=None, description="聊天头像")
    
    # 参与者
    participants: List[str] = Field(default_factory=list, description="参与者ID列表")
    participant_count: int = Field(default=2, description="参与者数量")
    
    # 统计信息
    message_count: int = Field(default=0, description="消息总数")
    last_message_time: Optional[str] = Field(default=None, description="最后消息时间")
    
    # 数据来源标记
    source_type: DataSourceType = Field(
        default=DataSourceType.WECHAT_CHAT,
        description="数据源类型",
    )
    is_simulated: bool = Field(default=True, description="是否为模拟数据")


class WeChatChatCrawlerConfig(CrawlerConfig):
    """微信聊天爬虫配置"""
    
    # 数据源配置
    source_type: DataSourceType = Field(
        default=DataSourceType.WECHAT_CHAT,
        description="数据源类型",
    )
    
    # 模拟配置
    simulation_mode: bool = Field(default=True, description="模拟模式（不实际爬取）")
    simulate_data_size: int = Field(default=100, description="模拟数据大小")
    
    # 安全配置
    encrypt_data: bool = Field(default=True, description="加密数据")
    anonymize_users: bool = Field(default=True, description="匿名化用户信息")
    
    # 合规配置
    require_user_consent: bool = Field(default=True, description="需要用户授权")
    data_retention_days: int = Field(default=30, description="数据保留天数")
    
    # 爬取范围配置
    max_messages_per_session: int = Field(default=1000, description="每会话最大消息数")
    include_media_messages: bool = Field(default=False, description="包含媒体消息")
    
    # 过滤配置
    filter_keywords: List[str] = Field(default_factory=list, description="过滤关键词")
    exclude_system_messages: bool = Field(default=True, description="排除系统消息")


class WeChatChatCrawler(SourceSpecificCrawler[WeChatMessage]):
    """
    微信聊天记录爬虫（模拟实现）
    
    重要说明：
    - 本爬虫仅提供数据结构和接口设计
    - 实际数据获取应使用用户授权的合法方式
    - 微信数据受隐私保护，未经授权爬取违反法律
    - 本实现使用模拟数据用于研究和测试
    
    合法数据获取方式建议：
    1. 使用微信官方数据导出功能（用户自行操作）
    2. 使用微信企业版API（企业授权）
    3. 用户手动导出数据后导入系统
    """
    
    supported_source_types = [DataSourceType.WECHAT_CHAT]
    capabilities = [
        CrawlerCapability.AUTH_REQUIRED,    # 需要用户授权
        CrawlerCapability.RATE_LIMIT,       # 需要速率限制
    ]
    
    # 合规声明
    COMPLIANCE_NOTICE = """
    重要合规声明：
    
    1. 微信聊天数据属于用户隐私，未经授权采集违反法律
    2. 本爬虫仅用于架构设计研究，不实际爬取数据
    3. 实际数据获取应遵循：
       - 微信平台用户协议
       - 《网络安全法》《个人信息保护法》
       - 用户知情同意原则
    4. 建议数据获取方式：
       - 用户自行导出数据
       - 使用官方授权接口
       - 企业版微信API（需企业授权）
    """
    
    def __init__(self, config: Optional[WeChatChatCrawlerConfig] = None):
        super().__init__(config or WeChatChatCrawlerConfig(), DataSourceType.WECHAT_CHAT)
        self._user_consent_obtained = False
        self._data_export_mode = False
    
    def _on_start(self) -> None:
        """启动时的合规检查"""
        logger.warning(self.COMPLIANCE_NOTICE)
        if self.config.simulation_mode:
            logger.info("WeChatChatCrawler已启动（模拟模式）")
        else:
            logger.warning("警告：非模拟模式需要用户授权和合法数据获取方式")
    
    def _on_stop(self) -> None:
        """停止时清理"""
        logger.info("WeChatChatCrawler已停止")
    
    def request_user_consent(self) -> bool:
        """
        请求用户授权
        
        实际应用中应通过UI界面或授权流程获取用户同意。
        本模拟实现返回模拟授权状态。
        
        Returns:
            是否获得授权
        """
        logger.info("请求用户授权...")
        # 模拟授权流程
        self._user_consent_obtained = self.config.simulation_mode
        return self._user_consent_obtained
    
    def set_data_export_mode(self, enabled: bool = True) -> None:
        """
        设置数据导出模式
        
        数据导出模式表示数据由用户手动导出后导入系统，
        不涉及爬取操作。
        
        Args:
            enabled: 是否启用数据导出模式
        """
        self._data_export_mode = enabled
        if enabled:
            logger.info("启用数据导出模式 - 数据由用户手动导入")
    
    async def fetch(self, url: str, **kwargs) -> CrawlResult:
        """
        获取数据
        
        微信聊天数据不支持URL方式获取。
        应使用crawl_session或import_data方法。
        
        Args:
            url: 不适用于微信聊天数据
            
        Returns:
            爬取结果（模拟）
        """
        return CrawlResult(
            url=url,
            status_code=400,
            content="微信聊天数据不支持URL方式获取。请使用crawl_session或import_data方法。",
            success=False,
            error_message="不支持的获取方式",
            source_type=DataSourceType.WECHAT_CHAT,
        )
    
    async def fetch_many(self, urls: List[str], **kwargs) -> List[CrawlResult]:
        """
        批量获取（不支持）
        
        Args:
            urls: URL列表
            
        Returns:
            爬取结果列表
        """
        return [
            CrawlResult(
                url=url,
                status_code=400,
                success=False,
                error_message="不支持的获取方式",
                source_type=DataSourceType.WECHAT_CHAT,
            )
            for url in urls
        ]
    
    async def crawl(self, target: str, **kwargs) -> WeChatMessage:
        """
        执行爬取任务
        
        Args:
            target: 会话ID或标识
            
        Returns:
            模拟的微信消息
        """
        messages = await self.crawl_session(target, limit=1)
        if messages:
            return messages[0]
        raise CrawlError("无消息数据", source_type=DataSourceType.WECHAT_CHAT)
    
    async def crawl_session(
        self,
        session_id: str,
        limit: Optional[int] = None,
        **kwargs,
    ) -> List[WeChatMessage]:
        """
        爬取指定会话的消息（模拟实现）
        
        Args:
            session_id: 会话ID
            limit: 最大消息数
            **kwargs: 额外参数
            
        Returns:
            模拟的消息列表
        """
        # 合规检查
        if not self.config.simulation_mode and not self._user_consent_obtained:
            raise CrawlError(
                "需要用户授权才能获取微信聊天数据",
                source_type=DataSourceType.WECHAT_CHAT,
            )
        
        if not self.config.simulation_mode:
            raise CrawlError(
                "非模拟模式需要使用合法数据获取方式（如用户导出数据）",
                source_type=DataSourceType.WECHAT_CHAT,
            )
        
        # 模拟数据生成
        limit = limit or self.config.max_messages_per_session
        messages = self._generate_simulated_messages(session_id, limit)
        
        self._record_success()
        logger.info(f"生成模拟消息 {len(messages)} 条（会话: {session_id}）")
        
        return messages
    
    def _generate_simulated_messages(
        self,
        session_id: str,
        count: int,
    ) -> List[WeChatMessage]:
        """
        生成模拟消息数据
        
        Args:
            session_id: 会话ID
            count: 消息数量
            
        Returns:
            模拟消息列表
        """
        messages = []
        base_time = datetime.now()
        
        # 模拟参与者
        participants = ["user_001", "user_002"]
        chat_type = WeChatChatType.PRIVATE
        
        for i in range(min(count, self.config.simulate_data_size)):
            # 随机消息类型
            msg_type = random.choice([
                WeChatMessageType.TEXT,
                WeChatMessageType.IMAGE,
                WeChatMessageType.LINK,
            ])
            
            # 随机发送者
            sender_id = random.choice(participants)
            receiver_id = participants[0] if sender_id == participants[1] else participants[1]
            
            # 模拟时间（随机间隔）
            send_time = base_time - timedelta(minutes=random.randint(0, 1000))
            
            # 生成消息ID（哈希模拟）
            msg_id = hashlib.md5(f"{session_id}_{i}_{send_time}".encode()).hexdigest()[:16]
            
            # 根据类型生成内容
            content = ""
            content_url = None
            link_title = None
            
            if msg_type == WeChatMessageType.TEXT:
                content = self._generate_simulated_text()
            elif msg_type == WeChatMessageType.IMAGE:
                content = "[图片]"
                content_url = f"https://example.com/image_{i}.jpg"
            elif msg_type == WeChatMessageType.LINK:
                link_title = self._generate_simulated_title()
                link_url = f"https://mp.weixin.qq.com/s/{msg_id}"
            
            # 应用过滤规则
            if self.config.exclude_system_messages and msg_type == WeChatMessageType.SYSTEM:
                continue
            
            if self.config.filter_keywords:
                skip = False
                for keyword in self.config.filter_keywords:
                    if keyword in content:
                        skip = True
                        break
                if skip:
                    continue
            
            # 创建消息对象
            message = WeChatMessage(
                message_id=msg_id,
                sequence_id=i,
                message_type=msg_type,
                chat_type=chat_type,
                sender_id=self._anonymize_user(sender_id) if self.config.anonymize_users else sender_id,
                sender_name=f"用户{sender_id[-3:]}" if self.config.anonymize_users else f"昵称_{sender_id}",
                receiver_id=self._anonymize_user(receiver_id) if self.config.anonymize_users else receiver_id,
                chat_id=session_id,
                content=content,
                content_url=content_url,
                link_title=link_title,
                link_url=link_url,
                send_time=send_time.isoformat(),
                is_simulated=True,
            )
            
            messages.append(message)
        
        # 按时间排序
        messages.sort(key=lambda m: m.send_time, reverse=True)
        
        return messages
    
    def _generate_simulated_text(self) -> str:
        """生成模拟文本内容"""
        templates = [
            "这是一条模拟的聊天消息",
            "明天见面讨论一下项目进展",
            "收到，我会尽快处理",
            "文件已发送，请查收",
            "周末有空吗？一起吃饭",
            "方案已经修改好了",
            "会议时间改到下午三点",
            "好的，没问题",
            "感谢您的帮助！",
            "稍后回复您",
        ]
        return random.choice(templates)
    
    def _generate_simulated_title(self) -> str:
        """生成模拟标题"""
        templates = [
            "微信公众号文章示例标题",
            "技术研究报告",
            "项目进展更新",
            "行业动态分析",
            "产品发布公告",
        ]
        return random.choice(templates)
    
    def _anonymize_user(self, user_id: str) -> str:
        """
        匿名化用户ID
        
        Args:
            user_id: 原始用户ID
            
        Returns:
            匿名化后的用户ID
        """
        return hashlib.md5(user_id.encode()).hexdigest()[:8]
    
    async def get_sessions(self) -> List[WeChatChatSession]:
        """
        获取会话列表（模拟）
        
        Returns:
            模拟的会话列表
        """
        # 模拟会话数据
        sessions = [
            WeChatChatSession(
                session_id="session_001",
                chat_type=WeChatChatType.PRIVATE,
                chat_name="模拟私聊",
                participants=["user_001", "user_002"],
                message_count=50,
                last_message_time=datetime.now().isoformat(),
                is_simulated=True,
            ),
            WeChatChatSession(
                session_id="group_001",
                chat_type=WeChatChatType.GROUP,
                chat_name="模拟群聊",
                participants=["user_001", "user_002", "user_003"],
                participant_count=3,
                message_count=100,
                last_message_time=datetime.now().isoformat(),
                is_simulated=True,
            ),
        ]
        
        return sessions
    
    async def search_messages(
        self,
        query: str,
        session_id: Optional[str] = None,
        **kwargs,
    ) -> List[WeChatMessage]:
        """
        搜索消息（模拟）
        
        Args:
            query: 搜索关键词
            session_id: 限定会话ID
            **kwargs: 额外参数
            
        Returns:
            匹配的消息列表
        """
        # 模拟搜索
        if session_id:
            messages = await self.crawl_session(session_id)
        else:
            sessions = await self.get_sessions()
            all_messages = []
            for session in sessions:
                msgs = await self.crawl_session(session.session_id, limit=10)
                all_messages.extend(msgs)
            messages = all_messages
        
        # 模拟过滤
        results = [
            msg for msg in messages
            if query.lower() in msg.content.lower()
            or (msg.link_title and query.lower() in msg.link_title.lower())
        ]
        
        return results[:self.config.max_messages_per_session]
    
    def import_user_data(
        self,
        data: Union[Dict, List[Dict]],
        data_format: str = "json",
    ) -> List[WeChatMessage]:
        """
        导入用户导出的数据
        
        这是合法获取数据的方式：用户自行导出数据后导入系统。
        
        Args:
            data: 用户导出的数据
            data_format: 数据格式
            
        Returns:
            解析后的消息列表
        """
        logger.info("导入用户数据（合法方式）")
        
        messages = []
        
        if isinstance(data, list):
            for item in data:
                message = self._parse_imported_message(item)
                if message:
                    message.is_simulated = False  # 标记为真实数据
                    messages.append(message)
        elif isinstance(data, dict):
            message = self._parse_imported_message(data)
            if message:
                message.is_simulated = False
                messages.append(message)
        
        logger.info(f"成功导入 {len(messages)} 条消息")
        return messages
    
    def _parse_imported_message(self, data: Dict) -> Optional[WeChatMessage]:
        """
        解析导入的消息数据
        
        Args:
            data: 原始数据
            
        Returns:
            解析后的消息对象
        """
        try:
            # 支持多种数据格式
            return WeChatMessage(
                message_id=data.get("id", data.get("message_id", "")),
                message_type=data.get("type", data.get("message_type", "text")),
                sender_id=data.get("sender", data.get("sender_id", "")),
                receiver_id=data.get("receiver", data.get("receiver_id", "")),
                content=data.get("content", data.get("text", "")),
                send_time=data.get("time", data.get("send_time", datetime.now().isoformat())),
                is_simulated=False,
                extra_info=data.get("extra", {}),
            )
        except Exception as e:
            logger.warning(f"解析消息失败: {e}")
            return None
    
    def get_compliance_report(self) -> Dict[str, Any]:
        """
        获取合规报告
        
        Returns:
            合规状态和相关信息
        """
        return {
            "crawler_type": "WeChatChatCrawler",
            "simulation_mode": self.config.simulation_mode,
            "user_consent_obtained": self._user_consent_obtained,
            "data_export_mode": self._data_export_mode,
            "compliance_notice": self.COMPLIANCE_NOTICE,
            "legal_data_sources": [
                "用户自行导出数据",
                "微信企业版API（需授权）",
                "用户授权的数据采集",
            ],
            "warnings": [
                "未经授权爬取微信数据违法",
                "需遵守《个人信息保护法》",
                "需遵循微信平台用户协议",
            ],
        }


# ==================== 微信公众号文章爬虫 ====================


class WeChatArticle(BaseModel):
    """微信公众号文章模型"""
    
    # 文章标识
    article_id: str = Field(description="文章ID")
    url: str = Field(description="文章URL")
    
    # 基本信息
    title: str = Field(description="标题")
    author: Optional[str] = Field(default=None, description="作者")
    summary: Optional[str] = Field(default=None, description="摘要")
    content: Optional[str] = Field(default=None, description="正文内容")
    
    # 公众号信息
    account_name: str = Field(default="", description="公众号名称")
    account_id: str = Field(default="", description="公众号ID")
    account_avatar: Optional[str] = Field(default=None, description="公众号头像")
    
    # 时间信息
    publish_time: Optional[str] = Field(default=None, description="发布时间")
    crawled_time: str = Field(
        default_factory=lambda: datetime.now().isoformat(),
        description="爬取时间",
    )
    
    # 元数据
    read_count: Optional[int] = Field(default=None, description="阅读数")
    like_count: Optional[int] = Field(default=None, description="点赞数")
    comment_count: Optional[int] = Field(default=None, description="评论数")
    
    # 图片信息
    cover_image: Optional[str] = Field(default=None, description="封面图片")
    images: List[str] = Field(default_factory=list, description="文章图片列表")
    
    # 其他信息
    source_url: Optional[str] = Field(default=None, description="原文链接")
    copyright_info: Optional[str] = Field(default=None, description="版权信息")
    
    # 数据来源
    source_type: DataSourceType = Field(
        default=DataSourceType.WECHAT_ARTICLE,
        description="数据源类型",
    )
    
    # 原始数据
    raw_html: Optional[str] = Field(default=None, description="原始HTML")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="其他元数据")
    
    class Config:
        use_enum_values = True


class WeChatArticleCrawlerConfig(CrawlerConfig):
    """微信公众号文章爬虫配置"""
    
    # 数据源配置
    source_type: DataSourceType = Field(
        default=DataSourceType.WECHAT_ARTICLE,
        description="数据源类型",
    )
    
    # 爬取配置
    extract_full_content: bool = Field(default=True, description="提取完整内容")
    extract_images: bool = Field(default=True, description="提取图片")
    extract_metadata: bool = Field(default=True, description="提取元数据")
    
    # 内容清洗配置
    clean_html_tags: bool = Field(default=True, description="清理HTML标签")
    remove_ads: bool = Field(default=True, description="移除广告内容")
    preserve_formatting: bool = Field(default=True, description="保留格式")
    
    # 代理配置（公众号文章常有反爬）
    use_wechat_proxy: bool = Field(default=False, description="使用微信专用代理")
    
    # 内容存储配置
    max_content_length: int = Field(default=100000, description="最大内容长度")
    
    # 搜索配置
    search_keywords: List[str] = Field(default_factory=list, description="搜索关键词")
    target_accounts: List[str] = Field(default_factory=list, description="目标公众号列表")


class WeChatArticleCrawler(SourceSpecificCrawler[WeChatArticle]):
    """
    微信公众号文章爬虫
    
    说明：
    - 微信公众号文章是公开内容，可以通过网页方式获取
    - 但微信公众号有反爬机制，需要谨慎处理
    - 本爬虫仅用于合法研究目的，不用于大规模爬取
    - 建议使用官方订阅方式获取文章
    
    特点：
    1. 支持通过URL直接爬取文章
    2. 支持文章内容解析和提取
    3. 支持元数据提取（作者、时间等）
    4. 内置反爬机制应对策略
    """
    
    supported_source_types = [DataSourceType.WECHAT_ARTICLE]
    capabilities = [
        CrawlerCapability.ASYNC_FETCH,
        CrawlerCapability.BATCH_FETCH,
        CrawlerCapability.RATE_LIMIT,
        CrawlerCapability.PROXY_SUPPORT,
    ]
    
    # 微信公众号文章URL特征
    WECHAT_ARTICLE_PATTERN = re.compile(
        r"https?://mp\.weixin\.qq\.com/s/[a-zA-Z0-9_-]+"
    )
    
    # 常用User-Agent池（微信公众号会检查UA）
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (iPhone; CPU iPhone OS 16_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Mobile/15E148 Safari/604.1",
        "Mozilla/5.0 (Linux; Android 13; Pixel 7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36",
    ]
    
    # 公众号常见请求头
    COMMON_HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }
    
    def __init__(self, config: Optional[WeChatArticleCrawlerConfig] = None):
        super().__init__(config or WeChatArticleCrawlerConfig(), DataSourceType.WECHAT_ARTICLE)
        self._session: Optional[Any] = None
        self._last_request_time: float = 0
        self._request_interval: float = 2.0  # 微信公众号建议间隔
    
    def _on_start(self) -> None:
        """启动爬虫"""
        logger.info("WeChatArticleCrawler已启动")
    
    def _on_stop(self) -> None:
        """停止爬虫"""
        logger.info("WeChatArticleCrawler已停止")
    
    def is_wechat_article_url(self, url: str) -> bool:
        """
        判断是否为微信公众号文章URL
        
        Args:
            url: 待判断的URL
            
        Returns:
            是否为公众号文章URL
        """
        return bool(self.WECHAT_ARTICLE_PATTERN.match(url))
    
    def _get_random_user_agent(self) -> str:
        """获取随机User-Agent"""
        return random.choice(self.USER_AGENTS)
    
    def _get_headers(self) -> Dict[str, str]:
        """获取请求头"""
        headers = dict(self.COMMON_HEADERS)
        headers["User-Agent"] = self._get_random_user_agent()
        
        # 添加额外配置的请求头
        headers.update(self.config.headers)
        
        return headers
    
    async def _wait_for_rate_limit(self) -> None:
        """等待速率限制"""
        elapsed = time.time() - self._last_request_time
        if elapsed < self._request_interval:
            await asyncio.sleep(self._request_interval - elapsed)
        self._last_request_time = time.time()
    
    async def fetch(self, url: str, **kwargs) -> CrawlResult:
        """
        获取微信公众号文章
        
        Args:
            url: 文章URL
            **kwargs: 额外参数
            
        Returns:
            爬取结果
        """
        # 验证URL
        if not self.is_wechat_article_url(url):
            return CrawlResult(
                url=url,
                status_code=400,
                content="",
                success=False,
                error_message="非微信公众号文章URL",
                source_type=DataSourceType.WECHAT_ARTICLE,
            )
        
        # 等待速率限制
        await self._wait_for_rate_limit()
        
        try:
            import aiohttp
            
            # 构建请求
            headers = self._get_headers()
            
            # 使用代理（如果配置）
            proxy = kwargs.get("proxy", self.config.proxy)
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    url,
                    headers=headers,
                    proxy=proxy,
                    timeout=aiohttp.ClientTimeout(total=self.config.timeout),
                    allow_redirects=True,
                ) as response:
                    content = await response.text()
                    
                    self._record_success()
                    
                    return CrawlResult(
                        url=str(response.url),
                        status_code=response.status,
                        content=content,
                        headers=dict(response.headers),
                        source_type=DataSourceType.WECHAT_ARTICLE,
                        elapsed_time=response.elapsed.total_seconds() if hasattr(response, 'elapsed') else 0.0,
                        success=response.status == 200,
                    )
                    
        except Exception as e:
            self._record_error()
            logger.error(f"获取文章失败: {url}, 错误: {e}")
            
            return CrawlResult(
                url=url,
                status_code=500,
                content="",
                success=False,
                error_message=str(e),
                source_type=DataSourceType.WECHAT_ARTICLE,
            )
    
    async def fetch_many(self, urls: List[str], **kwargs) -> List[CrawlResult]:
        """
        批量获取文章
        
        Args:
            urls: 文章URL列表
            **kwargs: 额外参数
            
        Returns:
            爬取结果列表
        """
        results = []
        for url in urls:
            result = await self.fetch(url, **kwargs)
            results.append(result)
            # 微信公众号需要较长间隔
            await asyncio.sleep(self._request_interval)
        
        return results
    
    async def crawl(self, target: str, **kwargs) -> WeChatArticle:
        """
        爬取单篇文章
        
        Args:
            target: 文章URL
            
        Returns:
            文章对象
        """
        articles = await self.crawl_articles([target])
        if articles:
            return articles[0]
        raise CrawlError(f"爬取文章失败: {target}", source_type=DataSourceType.WECHAT_ARTICLE)
    
    async def crawl_articles(
        self,
        urls: List[str],
        **kwargs,
    ) -> List[WeChatArticle]:
        """
        爬取多篇文章
        
        Args:
            urls: 文章URL列表
            **kwargs: 额外参数
            
        Returns:
            文章列表
        """
        articles = []
        
        for url in urls:
            result = await self.fetch(url, **kwargs)
            
            if result.success and result.content:
                article = self._parse_article(url, result.content)
                if article:
                    articles.append(article)
            
            # 等待间隔
            await asyncio.sleep(self._request_interval)
        
        return articles
    
    def _parse_article(self, url: str, html_content: str) -> Optional[WeChatArticle]:
        """
        解析文章内容
        
        Args:
            url: 文章URL
            html_content: HTML内容
            
        Returns:
            解析后的文章对象
        """
        try:
            # 使用正则表达式提取关键信息
            # 提取文章ID
            article_id = url.split("/")[-1] if "/" in url else ""
            
            # 提取标题
            title_match = re.search(
                r'<meta property="og:title" content="([^"]+)"',
                html_content,
            )
            title = title_match.group(1) if title_match else ""
            
            if not title:
                # 尝试另一种方式提取标题
                title_match = re.search(
                    r'<h1[^>]*class="rich_media_title"[^>]*>([^<]+)</h1>',
                    html_content,
                )
                title = title_match.group(1).strip() if title_match else ""
            
            # 提取作者
            author_match = re.search(
                r'<a[^>]*id="js_name"[^>]*>([^<]+)</a>',
                html_content,
            )
            account_name = author_match.group(1).strip() if author_match else ""
            
            # 提取正文内容
            content_match = re.search(
                r'<div[^>]*id="js_content"[^>]*>(.*?)</div>',
                html_content,
                re.DOTALL,
            )
            content_html = content_match.group(1) if content_match else ""
            
            # 清理HTML内容
            if self.config.clean_html_tags:
                content = self._clean_html_content(content_html)
            else:
                content = content_html
            
            # 提取发布时间
            publish_time_match = re.search(
                r'publish_time\s*=\s*"(\d+)"',
                html_content,
            )
            if publish_time_match:
                timestamp = int(publish_time_match.group(1))
                publish_time = datetime.fromtimestamp(timestamp).isoformat()
            else:
                publish_time = None
            
            # 提取封面图片
            cover_match = re.search(
                r'<meta property="og:image" content="([^"]+)"',
                html_content,
            )
            cover_image = cover_match.group(1) if cover_match else None
            
            # 提取文章图片
            images = []
            if self.config.extract_images:
                img_matches = re.findall(
                    r'<img[^>]*data-src="([^"]+)"',
                    content_html,
                )
                images = list(set(img_matches))[:20]  # 最多20张图片
            
            # 截断过长内容
            if len(content) > self.config.max_content_length:
                content = content[:self.config.max_content_length]
            
            return WeChatArticle(
                article_id=article_id,
                url=url,
                title=title,
                account_name=account_name,
                content=content,
                publish_time=publish_time,
                cover_image=cover_image,
                images=images,
                source_type=DataSourceType.WECHAT_ARTICLE,
                raw_html=html_content if len(html_content) < 50000 else None,
            )
            
        except Exception as e:
            logger.warning(f"解析文章失败: {url}, 错误: {e}")
            return None
    
    def _clean_html_content(self, html: str) -> str:
        """
        清理HTML内容
        
        Args:
            html: 原始HTML
            
        Returns:
            清理后的文本
        """
        # 移除script标签
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        
        # 移除style标签
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL)
        
        # 移除广告内容（常见的广告div）
        ad_patterns = [
            r'<div[^>]*class="rich_media_ad[^>]*>.*?</div>',
            r'<div[^>]*id="js_ad[^>]*>.*?</div>',
        ]
        for pattern in ad_patterns:
            html = re.sub(pattern, '', html, flags=re.DOTALL)
        
        # 保留段落结构
        if self.config.preserve_formatting:
            # 将p标签转换为换行
            html = re.sub(r'<p[^>]*>', '\n', html)
            html = re.sub(r'</p>', '\n', html)
            # 将br标签转换为换行
            html = re.sub(r'<br[^>]*>', '\n', html)
        else:
            # 移除所有标签
            html = re.sub(r'<[^>]+>', '', html)
        
        # 清理多余空白
        html = re.sub(r'\n\s*\n', '\n\n', html)
        html = re.sub(r'  +', ' ', html)
        
        return html.strip()
    
    async def search_articles(
        self,
        keyword: str,
        limit: int = 10,
        **kwargs,
    ) -> List[WeChatArticle]:
        """
        搜索微信公众号文章（通过搜索引擎）
        
        说明：微信公众号没有官方搜索API，
        需要通过搜索引擎间接搜索。
        
        Args:
            keyword: 搜索关键词
            limit: 最大结果数
            **kwargs: 额外参数
            
        Returns:
            搜索结果文章列表
        """
        # 使用Internet API搜索爬虫
        from ai_llm_agent_crawler.crawler.internet_api_crawler import (
            InternetAPICrawler,
            SearchEngineType,
        )
        
        # 创建搜索爬虫
        search_crawler = InternetAPICrawler()
        search_crawler.start()
        
        # 搜索公众号文章（添加site:mp.weixin.qq.com限定）
        query = f"{keyword} site:mp.weixin.qq.com"
        response = await search_crawler.search(query, engine=SearchEngineType.DUCKDUCKGO)
        
        search_crawler.stop()
        
        # 从搜索结果中提取公众号文章URL
        article_urls = [
            result.url
            for result in response.results
            if self.is_wechat_article_url(result.url)
        ]
        
        # 爬取文章内容
        articles = await self.crawl_articles(article_urls[:limit])
        
        return articles
    
    async def get_account_articles(
        self,
        account_name: str,
        limit: int = 20,
        **kwargs,
    ) -> List[WeChatArticle]:
        """
        获取指定公众号的文章
        
        说明：通过搜索引擎搜索指定公众号的文章
        
        Args:
            account_name: 公众号名称
            limit: 最大结果数
            **kwargs: 额外参数
            
        Returns:
            文章列表
        """
        # 构建搜索查询
        query = f"{account_name} site:mp.weixin.qq.com"
        
        articles = await self.search_articles(query, limit=limit, **kwargs)
        
        # 过滤确保来自指定公众号
        filtered_articles = [
            article
            for article in articles
            if account_name.lower() in article.account_name.lower()
        ]
        
        return filtered_articles


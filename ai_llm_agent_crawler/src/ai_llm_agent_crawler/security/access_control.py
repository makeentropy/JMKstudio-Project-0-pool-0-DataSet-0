"""
访问控制和权限管理模块

提供基于角色的访问控制（RBAC）功能，包括用户管理、角色定义、权限分配和访问验证。
"""

import hashlib
import json
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum, Flag, auto
from typing import Any, Callable, Dict, List, Optional, Set, Union

from ai_llm_agent_crawler.utils.logging import get_logger

logger = get_logger(__name__)


class Permission(Flag):
    """权限枚举（使用位标志）"""
    NONE = 0
    READ = auto()  # 读取权限
    WRITE = auto()  # 写入权限
    DELETE = auto()  # 删除权限
    CREATE = auto()  # 创建权限
    UPDATE = auto()  # 更新权限
    EXECUTE = auto()  # 执行权限
    ADMIN = auto()  # 管理员权限
    SUPER_ADMIN = auto()  # 超级管理员权限

    # 组合权限
    READ_WRITE = READ | WRITE
    READ_WRITE_DELETE = READ | WRITE | DELETE
    FULL = READ | WRITE | DELETE | CREATE | UPDATE | EXECUTE
    ALL = FULL | ADMIN | SUPER_ADMIN


class ResourceType(Enum):
    """资源类型枚举"""
    DATA = "data"
    FILE = "file"
    API = "api"
    SERVICE = "service"
    MODULE = "module"
    SYSTEM = "system"
    USER = "user"
    ROLE = "role"
    CERTIFICATE = "certificate"
    KEY = "key"
    CONFIGURATION = "configuration"
    LOG = "log"
    ALL = "all"


class AccessDecision(Enum):
    """访问决策枚举"""
    ALLOWED = "allowed"
    DENIED = "denied"
    NOT_AUTHORIZED = "not_authorized"
    INSUFFICIENT_PERMISSIONS = "insufficient_permissions"
    RESOURCE_NOT_FOUND = "resource_not_found"
    TIME_RESTRICTED = "time_restricted"
    IP_RESTRICTED = "ip_restricted"


@dataclass
class User:
    """用户数据类"""
    user_id: str
    username: str
    email: str
    password_hash: str
    salt: str
    roles: List[str] = field(default_factory=list)
    permissions: Permission = Permission.NONE
    is_active: bool = True
    is_locked: bool = False
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    last_login: Optional[float] = None
    login_count: int = 0
    failed_login_count: int = 0
    max_failed_login: int = 5
    lock_until: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "password_hash": self.password_hash,
            "salt": self.salt,
            "roles": self.roles,
            "permissions": self.permissions.value,
            "is_active": self.is_active,
            "is_locked": self.is_locked,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "last_login": self.last_login,
            "login_count": self.login_count,
            "failed_login_count": self.failed_login_count,
            "max_failed_login": self.max_failed_login,
            "lock_until": self.lock_until,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "User":
        """从字典创建"""
        return cls(
            user_id=data["user_id"],
            username=data["username"],
            email=data["email"],
            password_hash=data["password_hash"],
            salt=data["salt"],
            roles=data.get("roles", []),
            permissions=Permission(data.get("permissions", 0)),
            is_active=data.get("is_active", True),
            is_locked=data.get("is_locked", False),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            last_login=data.get("last_login"),
            login_count=data.get("login_count", 0),
            failed_login_count=data.get("failed_login_count", 0),
            max_failed_login=data.get("max_failed_login", 5),
            lock_until=data.get("lock_until"),
            metadata=data.get("metadata", {}),
        )

    def has_permission(self, permission: Permission) -> bool:
        """检查是否拥有权限"""
        return (self.permissions & permission) == permission

    def add_permission(self, permission: Permission) -> None:
        """添加权限"""
        self.permissions |= permission
        self.updated_at = time.time()

    def remove_permission(self, permission: Permission) -> None:
        """移除权限"""
        self.permissions &= ~permission
        self.updated_at = time.time()

    def is_account_locked(self) -> bool:
        """检查账户是否被锁定"""
        if self.is_locked:
            if self.lock_until and time.time() > self.lock_until:
                self.is_locked = False
                self.lock_until = None
                self.failed_login_count = 0
                return False
            return True
        return False


@dataclass
class Role:
    """角色数据类"""
    role_id: str
    name: str
    description: str
    permissions: Permission = Permission.NONE
    parent_roles: List[str] = field(default_factory=list)
    users: List[str] = field(default_factory=list)
    resource_types: List[ResourceType] = field(default_factory=lambda: [ResourceType.ALL])
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    is_active: bool = True
    priority: int = 0  # 角色优先级
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "role_id": self.role_id,
            "name": self.name,
            "description": self.description,
            "permissions": self.permissions.value,
            "parent_roles": self.parent_roles,
            "users": self.users,
            "resource_types": [rt.value for rt in self.resource_types],
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "is_active": self.is_active,
            "priority": self.priority,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Role":
        """从字典创建"""
        return cls(
            role_id=data["role_id"],
            name=data["name"],
            description=data["description"],
            permissions=Permission(data.get("permissions", 0)),
            parent_roles=data.get("parent_roles", []),
            users=data.get("users", []),
            resource_types=[ResourceType(rt) for rt in data.get("resource_types", ["all"])],
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            is_active=data.get("is_active", True),
            priority=data.get("priority", 0),
            metadata=data.get("metadata", {}),
        )

    def has_permission(self, permission: Permission) -> bool:
        """检查是否拥有权限"""
        return (self.permissions & permission) == permission

    def add_permission(self, permission: Permission) -> None:
        """添加权限"""
        self.permissions |= permission
        self.updated_at = time.time()

    def remove_permission(self, permission: Permission) -> None:
        """移除权限"""
        self.permissions &= ~permission
        self.updated_at = time.time()

    def has_resource_type(self, resource_type: ResourceType) -> bool:
        """检查是否拥有资源类型"""
        return ResourceType.ALL in self.resource_types or resource_type in self.resource_types


@dataclass
class Resource:
    """资源数据类"""
    resource_id: str
    resource_type: ResourceType
    name: str
    description: str
    owner: str  # 资源所有者用户ID
    allowed_roles: List[str] = field(default_factory=list)
    allowed_users: List[str] = field(default_factory=list)
    denied_roles: List[str] = field(default_factory=list)
    denied_users: List[str] = field(default_factory=list)
    required_permissions: Permission = Permission.READ
    is_public: bool = False
    is_active: bool = True
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "resource_id": self.resource_id,
            "resource_type": self.resource_type.value,
            "name": self.name,
            "description": self.description,
            "owner": self.owner,
            "allowed_roles": self.allowed_roles,
            "allowed_users": self.allowed_users,
            "denied_roles": self.denied_roles,
            "denied_users": self.denied_users,
            "required_permissions": self.required_permissions.value,
            "is_public": self.is_public,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Resource":
        """从字典创建"""
        return cls(
            resource_id=data["resource_id"],
            resource_type=ResourceType(data["resource_type"]),
            name=data["name"],
            description=data["description"],
            owner=data["owner"],
            allowed_roles=data.get("allowed_roles", []),
            allowed_users=data.get("allowed_users", []),
            denied_roles=data.get("denied_roles", []),
            denied_users=data.get("denied_users", []),
            required_permissions=Permission(data.get("required_permissions", 1)),
            is_public=data.get("is_public", False),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at", time.time()),
            updated_at=data.get("updated_at", time.time()),
            metadata=data.get("metadata", {}),
        )


@dataclass
class AccessPolicy:
    """访问策略"""
    policy_id: str
    name: str
    description: str
    effect: str  # "allow" or "deny"
    subjects: List[str]  # 用户或角色列表
    resources: List[str]  # 资源列表
    actions: List[str]  # 操作列表
    conditions: Dict[str, Any] = field(default_factory=dict)
    priority: int = 0
    is_active: bool = True
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "policy_id": self.policy_id,
            "name": self.name,
            "description": self.description,
            "effect": self.effect,
            "subjects": self.subjects,
            "resources": self.resources,
            "actions": self.actions,
            "conditions": self.conditions,
            "priority": self.priority,
            "is_active": self.is_active,
            "created_at": self.created_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AccessPolicy":
        """从字典创建"""
        return cls(
            policy_id=data["policy_id"],
            name=data["name"],
            description=data["description"],
            effect=data["effect"],
            subjects=data["subjects"],
            resources=data["resources"],
            actions=data["actions"],
            conditions=data.get("conditions", {}),
            priority=data.get("priority", 0),
            is_active=data.get("is_active", True),
            created_at=data.get("created_at", time.time()),
        )


@dataclass
class Session:
    """用户会话"""
    session_id: str
    user_id: str
    created_at: float = field(default_factory=time.time)
    expires_at: float = field(default_factory=lambda: time.time() + 3600)
    last_activity: float = field(default_factory=time.time)
    ip_address: Optional[str] = None
    device_info: Optional[str] = None
    is_active: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "last_activity": self.last_activity,
            "ip_address": self.ip_address,
            "device_info": self.device_info,
            "is_active": self.is_active,
            "metadata": self.metadata,
        }

    def is_expired(self) -> bool:
        """检查会话是否过期"""
        return time.time() > self.expires_at

    def refresh(self, duration: int = 3600) -> None:
        """刷新会话"""
        self.last_activity = time.time()
        self.expires_at = time.time() + duration


class UserManager:
    """
    用户管理器

    管理用户的创建、认证、权限分配等。
    """

    def __init__(self):
        """初始化用户管理器"""
        self._users: Dict[str, User] = {}
        self._sessions: Dict[str, Session] = {}
        self._password_hasher = self._hash_password

    def _hash_password(self, password: str, salt: str) -> str:
        """哈希密码"""
        return hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt.encode("utf-8"),
            100000
        ).hex()

    def create_user(
        self,
        username: str,
        email: str,
        password: str,
        roles: Optional[List[str]] = None,
        permissions: Permission = Permission.NONE,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> User:
        """
        创建用户

        Args:
            username: 用户名
            email: 邮箱
            password: 密码
            roles: 角色列表
            permissions: 权限
            metadata: 元数据

        Returns:
            创建的用户对象
        """
        # 检查用户名是否已存在
        for user in self._users.values():
            if user.username == username:
                raise ValueError(f"用户名已存在: {username}")
            if user.email == email:
                raise ValueError(f"邮箱已存在: {email}")

        # 生成用户ID
        user_id = secrets.token_hex(8)

        # 生成盐和密码哈希
        salt = secrets.token_hex(16)
        password_hash = self._password_hasher(password, salt)

        # 创建用户
        user = User(
            user_id=user_id,
            username=username,
            email=email,
            password_hash=password_hash,
            salt=salt,
            roles=roles or [],
            permissions=permissions,
            metadata=metadata or {},
        )

        self._users[user_id] = user
        logger.info(f"创建用户: {username} (ID: {user_id})")

        return user

    def authenticate(
        self,
        username: str,
        password: str,
        ip_address: Optional[str] = None,
        device_info: Optional[str] = None,
    ) -> tuple[Optional[Session], AccessDecision]:
        """
        认证用户

        Args:
            username: 用户名
            password: 密码
            ip_address: IP地址
            device_info: 设备信息

        Returns:
            (会话对象, 认证结果) 元组
        """
        # 查找用户
        user = None
        for u in self._users.values():
            if u.username == username:
                user = u
                break

        if not user:
            logger.warning(f"用户不存在: {username}")
            return None, AccessDecision.NOT_AUTHORIZED

        # 检查账户状态
        if not user.is_active:
            logger.warning(f"账户已禁用: {username}")
            return None, AccessDecision.DENIED

        if user.is_account_locked():
            logger.warning(f"账户已锁定: {username}")
            return None, AccessDecision.DENIED

        # 验证密码
        password_hash = self._password_hasher(password, user.salt)
        if password_hash != user.password_hash:
            user.failed_login_count += 1
            user.updated_at = time.time()

            if user.failed_login_count >= user.max_failed_login:
                user.is_locked = True
                user.lock_until = time.time() + 3600  # 锁定1小时
                logger.warning(f"账户锁定: {username}")

            logger.warning(f"密码错误: {username}")
            return None, AccessDecision.NOT_AUTHORIZED

        # 登录成功，更新用户状态
        user.failed_login_count = 0
        user.last_login = time.time()
        user.login_count += 1
        user.updated_at = time.time()

        # 创建会话
        session_id = secrets.token_hex(16)
        session = Session(
            session_id=session_id,
            user_id=user.user_id,
            ip_address=ip_address,
            device_info=device_info,
        )

        self._sessions[session_id] = session
        logger.info(f"用户登录成功: {username}, 会话ID: {session_id}")

        return session, AccessDecision.ALLOWED

    def logout(self, session_id: str) -> bool:
        """
        用户登出

        Args:
            session_id: 会话ID

        Returns:
            是否登出成功
        """
        if session_id in self._sessions:
            session = self._sessions[session_id]
            session.is_active = False
            del self._sessions[session_id]

            user = self._users.get(session.user_id)
            if user:
                logger.info(f"用户登出: {user.username}")

            return True

        return False

    def get_user(self, user_id: str) -> Optional[User]:
        """获取用户"""
        return self._users.get(user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """根据用户名获取用户"""
        for user in self._users.values():
            if user.username == username:
                return user
        return None

    def update_user(self, user_id: str, **kwargs: Any) -> Optional[User]:
        """
        更新用户信息

        Args:
            user_id: 用户ID
            **kwargs: 要更新的字段

        Returns:
            更新后的用户对象
        """
        user = self._users.get(user_id)
        if not user:
            return None

        for key, value in kwargs.items():
            if hasattr(user, key):
                setattr(user, key, value)

        user.updated_at = time.time()
        logger.info(f"更新用户: {user.username}")

        return user

    def delete_user(self, user_id: str) -> bool:
        """删除用户"""
        if user_id in self._users:
            user = self._users[user_id]
            del self._users[user_id]

            # 删除相关会话
            for session_id, session in list(self._sessions.items()):
                if session.user_id == user_id:
                    del self._sessions[session_id]

            logger.info(f"删除用户: {user.username}")
            return True

        return False

    def change_password(
        self,
        user_id: str,
        old_password: str,
        new_password: str,
    ) -> bool:
        """
        更改密码

        Args:
            user_id: 用户ID
            old_password: 旧密码
            new_password: 新密码

        Returns:
            是否更改成功
        """
        user = self._users.get(user_id)
        if not user:
            return False

        # 验证旧密码
        old_hash = self._password_hasher(old_password, user.salt)
        if old_hash != user.password_hash:
            return False

        # 生成新盐和密码哈希
        new_salt = secrets.token_hex(16)
        new_hash = self._password_hasher(new_password, new_salt)

        user.salt = new_salt
        user.password_hash = new_hash
        user.updated_at = time.time()

        logger.info(f"用户更改密码: {user.username}")
        return True

    def get_session(self, session_id: str) -> Optional[Session]:
        """获取会话"""
        return self._sessions.get(session_id)

    def validate_session(self, session_id: str) -> tuple[Optional[User], AccessDecision]:
        """
        验证会话

        Args:
            session_id: 会话ID

        Returns:
            (用户对象, 验证结果) 元组
        """
        session = self._sessions.get(session_id)
        if not session:
            return None, AccessDecision.NOT_AUTHORIZED

        if session.is_expired():
            del self._sessions[session_id]
            return None, AccessDecision.TIME_RESTRICTED

        if not session.is_active:
            return None, AccessDecision.DENIED

        user = self._users.get(session.user_id)
        if not user or not user.is_active:
            return None, AccessDecision.DENIED

        # 刷新会话
        session.refresh()

        return user, AccessDecision.ALLOWED

    def list_users(self) -> List[User]:
        """列出所有用户"""
        return list(self._users.values())

    def list_active_sessions(self) -> List[Session]:
        """列出所有活跃会话"""
        return [s for s in self._sessions.values() if s.is_active and not s.is_expired()]


class RoleManager:
    """
    角色管理器

    管理角色的创建、权限分配等。
    """

    def __init__(self):
        """初始化角色管理器"""
        self._roles: Dict[str, Role] = {}

        # 创建默认角色
        self._create_default_roles()

    def _create_default_roles(self) -> None:
        """创建默认角色"""
        # 超级管理员角色
        self.create_role(
            name="super_admin",
            description="超级管理员角色，拥有所有权限",
            permissions=Permission.ALL,
            priority=100,
        )

        # 管理员角色
        self.create_role(
            name="admin",
            description="管理员角色",
            permissions=Permission.FULL | Permission.ADMIN,
            priority=80,
        )

        # 用户角色
        self.create_role(
            name="user",
            description="普通用户角色",
            permissions=Permission.READ_WRITE,
            priority=50,
        )

        # 访客角色
        self.create_role(
            name="guest",
            description="访客角色，只有读取权限",
            permissions=Permission.READ,
            priority=10,
        )

    def create_role(
        self,
        name: str,
        description: str,
        permissions: Permission = Permission.NONE,
        parent_roles: Optional[List[str]] = None,
        resource_types: Optional[List[ResourceType]] = None,
        priority: int = 0,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Role:
        """
        创建角色

        Args:
            name: 角色名称
            description: 角色描述
            permissions: 权限
            parent_roles: 父角色列表
            resource_types: 资源类型列表
            priority: 优先级
            metadata: 元数据

        Returns:
            创建的角色对象
        """
        # 检查角色名是否已存在
        for role in self._roles.values():
            if role.name == name:
                raise ValueError(f"角色名已存在: {name}")

        # 生成角色ID
        role_id = secrets.token_hex(8)

        # 创建角色
        role = Role(
            role_id=role_id,
            name=name,
            description=description,
            permissions=permissions,
            parent_roles=parent_roles or [],
            resource_types=resource_types or [ResourceType.ALL],
            priority=priority,
            metadata=metadata or {},
        )

        self._roles[role_id] = role
        logger.info(f"创建角色: {name} (ID: {role_id})")

        return role

    def get_role(self, role_id: str) -> Optional[Role]:
        """获取角色"""
        return self._roles.get(role_id)

    def get_role_by_name(self, name: str) -> Optional[Role]:
        """根据角色名获取角色"""
        for role in self._roles.values():
            if role.name == name:
                return role
        return None

    def update_role(self, role_id: str, **kwargs: Any) -> Optional[Role]:
        """更新角色"""
        role = self._roles.get(role_id)
        if not role:
            return None

        for key, value in kwargs.items():
            if hasattr(role, key):
                setattr(role, key, value)

        role.updated_at = time.time()
        logger.info(f"更新角色: {role.name}")

        return role

    def delete_role(self, role_id: str) -> bool:
        """删除角色"""
        if role_id in self._roles:
            role = self._roles[role_id]
            del self._roles[role_id]
            logger.info(f"删除角色: {role.name}")
            return True

        return False

    def assign_user(self, role_id: str, user_id: str) -> bool:
        """
        将角色分配给用户

        Args:
            role_id: 角色ID
            user_id: 用户ID

        Returns:
            是否分配成功
        """
        role = self._roles.get(role_id)
        if not role:
            return False

        if user_id not in role.users:
            role.users.append(user_id)
            role.updated_at = time.time()
            logger.info(f"将角色 {role.name} 分配给用户 {user_id}")

        return True

    def revoke_user(self, role_id: str, user_id: str) -> bool:
        """
        从用户撤销角色

        Args:
            role_id: 角色ID
            user_id: 用户ID

        Returns:
            是否撤销成功
        """
        role = self._roles.get(role_id)
        if not role:
            return False

        if user_id in role.users:
            role.users.remove(user_id)
            role.updated_at = time.time()
            logger.info(f"从用户 {user_id} 撤销角色 {role.name}")

        return True

    def get_role_permissions(self, role_id: str) -> Permission:
        """
        获取角色的所有权限（包括继承的）

        Args:
            role_id: 角色ID

        Returns:
            权限集合
        """
        role = self._roles.get(role_id)
        if not role:
            return Permission.NONE

        permissions = role.permissions

        # 合并父角色权限
        for parent_id in role.parent_roles:
            parent_perms = self.get_role_permissions(parent_id)
            permissions |= parent_perms

        return permissions

    def list_roles(self) -> List[Role]:
        """列出所有角色"""
        return list(self._roles.values())


class ResourceManager:
    """
    资源管理器

    管理资源和资源权限。
    """

    def __init__(self):
        """初始化资源管理器"""
        self._resources: Dict[str, Resource] = {}

    def create_resource(
        self,
        resource_type: ResourceType,
        name: str,
        description: str,
        owner: str,
        required_permissions: Permission = Permission.READ,
        is_public: bool = False,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Resource:
        """
        创建资源

        Args:
            resource_type: 资源类型
            name: 资源名称
            description: 资源描述
            owner: 所有者用户ID
            required_permissions: 所需权限
            is_public: 是否公开
            metadata: 元数据

        Returns:
            创建的资源对象
        """
        # 生成资源ID
        resource_id = secrets.token_hex(8)

        # 创建资源
        resource = Resource(
            resource_id=resource_id,
            resource_type=resource_type,
            name=name,
            description=description,
            owner=owner,
            required_permissions=required_permissions,
            is_public=is_public,
            metadata=metadata or {},
        )

        self._resources[resource_id] = resource
        logger.info(f"创建资源: {name} (ID: {resource_id}, 类型: {resource_type.value})")

        return resource

    def get_resource(self, resource_id: str) -> Optional[Resource]:
        """获取资源"""
        return self._resources.get(resource_id)

    def update_resource(self, resource_id: str, **kwargs: Any) -> Optional[Resource]:
        """更新资源"""
        resource = self._resources.get(resource_id)
        if not resource:
            return None

        for key, value in kwargs.items():
            if hasattr(resource, key):
                setattr(resource, key, value)

        resource.updated_at = time.time()
        logger.info(f"更新资源: {resource.name}")

        return resource

    def delete_resource(self, resource_id: str) -> bool:
        """删除资源"""
        if resource_id in self._resources:
            resource = self._resources[resource_id]
            del self._resources[resource_id]
            logger.info(f"删除资源: {resource.name}")
            return True

        return False

    def list_resources(
        self,
        resource_type: Optional[ResourceType] = None,
        owner: Optional[str] = None,
    ) -> List[Resource]:
        """
        列出资源

        Args:
            resource_type: 资源类型过滤
            owner: 所有者过滤

        Returns:
            资源列表
        """
        resources = list(self._resources.values())

        if resource_type:
            resources = [r for r in resources if r.resource_type == resource_type]
        if owner:
            resources = [r for r in resources if r.owner == owner]

        return resources

    def grant_access(
        self,
        resource_id: str,
        user_ids: Optional[List[str]] = None,
        role_ids: Optional[List[str]] = None,
    ) -> bool:
        """
        授予资源访问权限

        Args:
            resource_id: 资源ID
            user_ids: 用户ID列表
            role_ids: 角色ID列表

        Returns:
            是否授予成功
        """
        resource = self._resources.get(resource_id)
        if not resource:
            return False

        if user_ids:
            for user_id in user_ids:
                if user_id not in resource.allowed_users:
                    resource.allowed_users.append(user_id)

        if role_ids:
            for role_id in role_ids:
                if role_id not in resource.allowed_roles:
                    resource.allowed_roles.append(role_id)

        resource.updated_at = time.time()
        logger.info(f"授予资源 {resource.name} 的访问权限")

        return True

    def deny_access(
        self,
        resource_id: str,
        user_ids: Optional[List[str]] = None,
        role_ids: Optional[List[str]] = None,
    ) -> bool:
        """
        拒绝资源访问权限

        Args:
            resource_id: 资源ID
            user_ids: 用户ID列表
            role_ids: 角色ID列表

        Returns:
            是否拒绝成功
        """
        resource = self._resources.get(resource_id)
        if not resource:
            return False

        if user_ids:
            for user_id in user_ids:
                if user_id not in resource.denied_users:
                    resource.denied_users.append(user_id)
                if user_id in resource.allowed_users:
                    resource.allowed_users.remove(user_id)

        if role_ids:
            for role_id in role_ids:
                if role_id not in resource.denied_roles:
                    resource.denied_roles.append(role_id)
                if role_id in resource.allowed_roles:
                    resource.allowed_roles.remove(role_id)

        resource.updated_at = time.time()
        logger.info(f"拒绝资源 {resource.name} 的访问权限")

        return True


class AccessController:
    """
    访问控制器

    控制用户对资源的访问，实现RBAC逻辑。
    """

    def __init__(
        self,
        user_manager: Optional[UserManager] = None,
        role_manager: Optional[RoleManager] = None,
        resource_manager: Optional[ResourceManager] = None,
    ):
        """
        初始化访问控制器

        Args:
            user_manager: 用户管理器
            role_manager: 角色管理器
            resource_manager: 资源管理器
        """
        self.user_manager = user_manager or UserManager()
        self.role_manager = role_manager or RoleManager()
        self.resource_manager = resource_manager or ResourceManager()
        self._policies: Dict[str, AccessPolicy] = {}
        self._access_hooks: List[Callable[[str, str, Permission], None]] = []

    def add_access_hook(self, hook: Callable[[str, str, Permission], None]) -> None:
        """
        添加访问钩子

        Args:
            hook: 钩子函数 (user_id, resource_id, permission)
        """
        self._access_hooks.append(hook)

    def check_access(
        self,
        user_id: str,
        resource_id: str,
        permission: Permission,
    ) -> AccessDecision:
        """
        检查访问权限

        Args:
            user_id: 用户ID
            resource_id: 资源ID
            permission: 请求的权限

        Returns:
            访问决策
        """
        # 获取用户
        user = self.user_manager.get_user(user_id)
        if not user:
            return AccessDecision.NOT_AUTHORIZED

        if not user.is_active:
            return AccessDecision.DENIED

        if user.is_account_locked():
            return AccessDecision.DENIED

        # 获取资源
        resource = self.resource_manager.get_resource(resource_id)
        if not resource:
            return AccessDecision.RESOURCE_NOT_FOUND

        if not resource.is_active:
            return AccessDecision.DENIED

        # 检查是否是资源所有者
        if resource.owner == user_id:
            return AccessDecision.ALLOWED

        # 检查公开资源
        if resource.is_public and permission == Permission.READ:
            return AccessDecision.ALLOWED

        # 检查黑名单
        if user_id in resource.denied_users:
            return AccessDecision.DENIED

        for role_id in user.roles:
            if role_id in resource.denied_roles:
                return AccessDecision.DENIED

        # 检查白名单
        if user_id in resource.allowed_users:
            if self._check_user_permissions(user, permission, resource):
                return AccessDecision.ALLOWED

        # 检查角色权限
        for role_id in user.roles:
            role = self.role_manager.get_role(role_id)
            if role:
                if role_id in resource.allowed_roles:
                    if self._check_role_permissions(role, permission, resource):
                        return AccessDecision.ALLOWED

        # 检查用户直接权限
        if self._check_user_permissions(user, permission, resource):
            return AccessDecision.ALLOWED

        # 检查角色继承权限
        for role_id in user.roles:
            role_permissions = self.role_manager.get_role_permissions(role_id)
            if (role_permissions & permission) == permission:
                role = self.role_manager.get_role(role_id)
                if role and role.has_resource_type(resource.resource_type):
                    return AccessDecision.ALLOWED

        return AccessDecision.INSUFFICIENT_PERMISSIONS

    def _check_user_permissions(
        self,
        user: User,
        permission: Permission,
        resource: Resource,
    ) -> bool:
        """检查用户权限"""
        # 检查用户是否拥有所需权限
        if not user.has_permission(permission):
            return False

        # 检查资源所需权限
        if (user.permissions & resource.required_permissions) != resource.required_permissions:
            return False

        return True

    def _check_role_permissions(
        self,
        role: Role,
        permission: Permission,
        resource: Resource,
    ) -> bool:
        """检查角色权限"""
        # 获取角色完整权限（包括继承）
        role_permissions = self.role_manager.get_role_permissions(role.role_id)

        # 检查角色是否拥有所需权限
        if (role_permissions & permission) != permission:
            return False

        # 检查资源类型
        if not role.has_resource_type(resource.resource_type):
            return False

        # 检查资源所需权限
        if (role_permissions & resource.required_permissions) != resource.required_permissions:
            return False

        return True

    def grant_permission(
        self,
        user_id: str,
        permission: Permission,
    ) -> bool:
        """
        授予用户权限

        Args:
            user_id: 用户ID
            permission: 权限

        Returns:
            是否授予成功
        """
        user = self.user_manager.get_user(user_id)
        if not user:
            return False

        user.add_permission(permission)
        logger.info(f"授予用户 {user.username} 权限: {permission.name}")

        return True

    def revoke_permission(
        self,
        user_id: str,
        permission: Permission,
    ) -> bool:
        """
        撤销用户权限

        Args:
            user_id: 用户ID
            permission: 权限

        Returns:
            是否撤销成功
        """
        user = self.user_manager.get_user(user_id)
        if not user:
            return False

        user.remove_permission(permission)
        logger.info(f"撤销用户 {user.username} 权限: {permission.name}")

        return True

    def assign_role(
        self,
        user_id: str,
        role_id: str,
    ) -> bool:
        """
        给用户分配角色

        Args:
            user_id: 用户ID
            role_id: 角色ID

        Returns:
            是否分配成功
        """
        user = self.user_manager.get_user(user_id)
        role = self.role_manager.get_role(role_id)

        if not user or not role:
            return False

        if role_id not in user.roles:
            user.roles.append(role_id)
            user.updated_at = time.time()

            # 将用户添加到角色
            self.role_manager.assign_user(role_id, user_id)

            logger.info(f"给用户 {user.username} 分配角色: {role.name}")

        return True

    def revoke_role(
        self,
        user_id: str,
        role_id: str,
    ) -> bool:
        """
        从用户撤销角色

        Args:
            user_id: 用户ID
            role_id: 角色ID

        Returns:
            是否撤销成功
        """
        user = self.user_manager.get_user(user_id)
        role = self.role_manager.get_role(role_id)

        if not user or not role:
            return False

        if role_id in user.roles:
            user.roles.remove(role_id)
            user.updated_at = time.time()

            # 从角色移除用户
            self.role_manager.revoke_user(role_id, user_id)

            logger.info(f"从用户 {user.username} 撤销角色: {role.name}")

        return True

    def create_policy(
        self,
        name: str,
        effect: str,
        subjects: List[str],
        resources: List[str],
        actions: List[str],
        conditions: Optional[Dict[str, Any]] = None,
        priority: int = 0,
    ) -> AccessPolicy:
        """
        创建访问策略

        Args:
            name: 策略名称
            effect: 效果 (allow/deny)
            subjects: 主体（用户或角色）
            resources: 资源
            actions: 操作
            conditions: 条件
            priority: 优先级

        Returns:
            创建的策略
        """
        policy_id = secrets.token_hex(8)

        policy = AccessPolicy(
            policy_id=policy_id,
            name=name,
            description=f"访问策略: {name}",
            effect=effect,
            subjects=subjects,
            resources=resources,
            actions=actions,
            conditions=conditions or {},
            priority=priority,
        )

        self._policies[policy_id] = policy
        logger.info(f"创建访问策略: {name}")

        return policy

    def evaluate_policies(
        self,
        user_id: str,
        resource_id: str,
        action: str,
    ) -> AccessDecision:
        """
        根据策略评估访问

        Args:
            user_id: 用户ID
            resource_id: 资源ID
            action: 操作

        Returns:
            访问决策
        """
        user = self.user_manager.get_user(user_id)
        if not user:
            return AccessDecision.NOT_AUTHORIZED

        # 收集用户的主体标识
        subjects = [user_id] + user.roles

        # 按优先级排序策略
        policies = sorted(
            self._policies.values(),
            key=lambda p: p.priority,
            reverse=True
        )

        for policy in policies:
            if not policy.is_active:
                continue

            # 检查主体匹配
            if not any(s in policy.subjects for s in subjects):
                continue

            # 检查资源匹配
            if resource_id not in policy.resources and "*" not in policy.resources:
                continue

            # 检查操作匹配
            if action not in policy.actions and "*" not in policy.actions:
                continue

            # 检查条件
            if policy.conditions:
                if not self._evaluate_conditions(policy.conditions, user):
                    continue

            # 返回策略效果
            if policy.effect == "allow":
                return AccessDecision.ALLOWED
            else:
                return AccessDecision.DENIED

        # 默认拒绝
        return AccessDecision.INSUFFICIENT_PERMISSIONS

    def _evaluate_conditions(
        self,
        conditions: Dict[str, Any],
        user: User,
    ) -> bool:
        """评估策略条件"""
        # 时间条件
        if "time_range" in conditions:
            time_range = conditions["time_range"]
            now = datetime.now()
            start = datetime.strptime(time_range["start"], "%H:%M")
            end = datetime.strptime(time_range["end"], "%H:%M")
            current_time = datetime.strptime(now.strftime("%H:%M"), "%H:%M")

            if not (start <= current_time <= end):
                return False

        # IP条件
        if "allowed_ips" in conditions:
            allowed_ips = conditions["allowed_ips"]
            if user.metadata.get("ip_address") not in allowed_ips:
                return False

        return True

    def get_user_permissions(self, user_id: str) -> Permission:
        """
        获取用户的所有权限

        Args:
            user_id: 用户ID

        Returns:
            权限集合
        """
        user = self.user_manager.get_user(user_id)
        if not user:
            return Permission.NONE

        # 合并用户直接权限
        permissions = user.permissions

        # 合并角色权限
        for role_id in user.roles:
            role_permissions = self.role_manager.get_role_permissions(role_id)
            permissions |= role_permissions

        return permissions

    def export_config(self) -> Dict[str, Any]:
        """导出配置"""
        return {
            "users": [u.to_dict() for u in self.user_manager.list_users()],
            "roles": [r.to_dict() for r in self.role_manager.list_roles()],
            "resources": [r.to_dict() for r in self.resource_manager.list_resources()],
            "policies": [p.to_dict() for p in self._policies.values()],
        }

    def import_config(self, config: Dict[str, Any]) -> None:
        """导入配置"""
        # 导入用户
        for user_data in config.get("users", []):
            user = User.from_dict(user_data)
            self.user_manager._users[user.user_id] = user

        # 导入角色
        for role_data in config.get("roles", []):
            role = Role.from_dict(role_data)
            self.role_manager._roles[role.role_id] = role

        # 导入资源
        for resource_data in config.get("resources", []):
            resource = Resource.from_dict(resource_data)
            self.resource_manager._resources[resource.resource_id] = resource

        # 导入策略
        for policy_data in config.get("policies", []):
            policy = AccessPolicy.from_dict(policy_data)
            self._policies[policy.policy_id] = policy

        logger.info("导入访问控制配置完成")
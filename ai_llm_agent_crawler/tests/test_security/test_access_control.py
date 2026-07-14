"""
访问控制和权限管理测试
"""

import pytest
from ai_llm_agent_crawler.security.access_control import (
    Permission,
    ResourceType,
    AccessDecision,
    UserManager,
    RoleManager,
    ResourceManager,
    AccessController,
)


class TestUserManager:
    """测试用户管理器"""

    def test_create_user(self):
        """测试创建用户"""
        manager = UserManager()
        user = manager.create_user(
            username="test_user",
            email="test@example.com",
            password="password123",
            permissions=Permission.READ_WRITE,
        )

        assert user.username == "test_user"
        assert user.email == "test@example.com"
        assert user.has_permission(Permission.READ)
        assert user.has_permission(Permission.WRITE)

    def test_authenticate_success(self):
        """测试认证成功"""
        manager = UserManager()
        manager.create_user(
            username="test_user",
            email="test@example.com",
            password="password123",
        )

        session, decision = manager.authenticate("test_user", "password123")

        assert session is not None
        assert decision == AccessDecision.ALLOWED

    def test_authenticate_wrong_password(self):
        """测试密码错误"""
        manager = UserManager()
        manager.create_user(
            username="test_user",
            email="test@example.com",
            password="password123",
        )

        session, decision = manager.authenticate("test_user", "wrong_password")

        assert session is None
        assert decision == AccessDecision.NOT_AUTHORIZED

    def test_authenticate_nonexistent_user(self):
        """测试用户不存在"""
        manager = UserManager()
        session, decision = manager.authenticate("nonexistent", "password")

        assert session is None
        assert decision == AccessDecision.NOT_AUTHORIZED

    def test_logout(self):
        """测试登出"""
        manager = UserManager()
        manager.create_user(
            username="test_user",
            email="test@example.com",
            password="password123",
        )

        session, _ = manager.authenticate("test_user", "password123")
        assert manager.logout(session.session_id)
        assert manager.get_session(session.session_id) is None

    def test_change_password(self):
        """测试更改密码"""
        manager = UserManager()
        user = manager.create_user(
            username="test_user",
            email="test@example.com",
            password="old_password",
        )

        assert manager.change_password(user.user_id, "old_password", "new_password")

        # 使用新密码认证
        session, decision = manager.authenticate("test_user", "new_password")
        assert decision == AccessDecision.ALLOWED

    def test_validate_session(self):
        """测试验证会话"""
        manager = UserManager()
        manager.create_user(
            username="test_user",
            email="test@example.com",
            password="password123",
        )

        session, _ = manager.authenticate("test_user", "password123")
        user, decision = manager.validate_session(session.session_id)

        assert user is not None
        assert decision == AccessDecision.ALLOWED

    def test_user_permissions(self):
        """测试用户权限操作"""
        user = UserManager().create_user(
            username="test_user",
            email="test@example.com",
            password="password123",
            permissions=Permission.READ,
        )

        assert user.has_permission(Permission.READ)
        assert not user.has_permission(Permission.WRITE)

        user.add_permission(Permission.WRITE)
        assert user.has_permission(Permission.WRITE)

        user.remove_permission(Permission.WRITE)
        assert not user.has_permission(Permission.WRITE)


class TestRoleManager:
    """测试角色管理器"""

    def test_create_role(self):
        """测试创建角色"""
        manager = RoleManager()
        role = manager.create_role(
            name="test_role",
            description="Test role",
            permissions=Permission.READ_WRITE,
        )

        assert role.name == "test_role"
        assert role.has_permission(Permission.READ)
        assert role.has_permission(Permission.WRITE)

    def test_get_role_by_name(self):
        """测试根据名称获取角色"""
        manager = RoleManager()
        manager.create_role(
            name="test_role",
            description="Test role",
        )

        role = manager.get_role_by_name("test_role")
        assert role is not None
        assert role.name == "test_role"

    def test_assign_user(self):
        """测试分配用户到角色"""
        manager = RoleManager()
        role = manager.create_role(
            name="test_role",
            description="Test role",
        )

        assert manager.assign_user(role.role_id, "user1")
        assert "user1" in role.users

    def test_revoke_user(self):
        """测试从角色撤销用户"""
        manager = RoleManager()
        role = manager.create_role(
            name="test_role",
            description="Test role",
        )

        manager.assign_user(role.role_id, "user1")
        assert manager.revoke_user(role.role_id, "user1")
        assert "user1" not in role.users

    def test_default_roles(self):
        """测试默认角色"""
        manager = RoleManager()

        super_admin = manager.get_role_by_name("super_admin")
        admin = manager.get_role_by_name("admin")
        user = manager.get_role_by_name("user")
        guest = manager.get_role_by_name("guest")

        assert super_admin is not None
        assert admin is not None
        assert user is not None
        assert guest is not None

        assert super_admin.permissions == Permission.ALL
        assert guest.permissions == Permission.READ

    def test_role_permissions_inheritance(self):
        """测试角色权限继承"""
        manager = RoleManager()

        parent_role = manager.create_role(
            name="parent_role",
            description="Parent role",
            permissions=Permission.READ,
        )

        child_role = manager.create_role(
            name="child_role",
            description="Child role",
            permissions=Permission.WRITE,
            parent_roles=[parent_role.role_id],
        )

        # 子角色应该继承父角色的权限
        child_permissions = manager.get_role_permissions(child_role.role_id)
        assert (child_permissions & Permission.READ) == Permission.READ
        assert (child_permissions & Permission.WRITE) == Permission.WRITE


class TestResourceManager:
    """测试资源管理器"""

    def test_create_resource(self):
        """测试创建资源"""
        manager = ResourceManager()
        resource = manager.create_resource(
            resource_type=ResourceType.DATA,
            name="test_resource",
            description="Test resource",
            owner="user1",
            required_permissions=Permission.READ,
        )

        assert resource.name == "test_resource"
        assert resource.resource_type == ResourceType.DATA
        assert resource.owner == "user1"

    def test_grant_access(self):
        """测试授予访问权限"""
        manager = ResourceManager()
        resource = manager.create_resource(
            resource_type=ResourceType.DATA,
            name="test_resource",
            description="Test resource",
            owner="user1",
        )

        assert manager.grant_access(
            resource.resource_id,
            user_ids=["user2", "user3"],
            role_ids=["role1"],
        )

        assert "user2" in resource.allowed_users
        assert "role1" in resource.allowed_roles

    def test_deny_access(self):
        """测试拒绝访问权限"""
        manager = ResourceManager()
        resource = manager.create_resource(
            resource_type=ResourceType.DATA,
            name="test_resource",
            description="Test resource",
            owner="user1",
        )

        manager.grant_access(resource.resource_id, user_ids=["user2"])
        manager.deny_access(resource.resource_id, user_ids=["user2"])

        assert "user2" in resource.denied_users
        assert "user2" not in resource.allowed_users

    def test_list_resources(self):
        """测试列出资源"""
        manager = ResourceManager()

        manager.create_resource(ResourceType.DATA, "resource1", "Desc", "user1")
        manager.create_resource(ResourceType.FILE, "resource2", "Desc", "user1")
        manager.create_resource(ResourceType.API, "resource3", "Desc", "user2")

        data_resources = manager.list_resources(resource_type=ResourceType.DATA)
        assert len(data_resources) == 1

        user1_resources = manager.list_resources(owner="user1")
        assert len(user1_resources) == 2


class TestAccessController:
    """测试访问控制器"""

    def setup_method(self):
        """设置测试方法"""
        self.access_controller = AccessController()
        self.user_manager = self.access_controller.user_manager
        self.role_manager = self.access_controller.role_manager
        self.resource_manager = self.access_controller.resource_manager

    def test_check_access_owner(self):
        """测试资源所有者访问"""
        user = self.user_manager.create_user("owner", "owner@test.com", "password")
        resource = self.resource_manager.create_resource(
            ResourceType.DATA, "resource", "Desc", user.user_id
        )

        decision = self.access_controller.check_access(
            user.user_id, resource.resource_id, Permission.READ
        )

        assert decision == AccessDecision.ALLOWED

    def test_check_access_with_permission(self):
        """测试有权限的用户访问"""
        owner = self.user_manager.create_user("owner", "owner@test.com", "password")
        user = self.user_manager.create_user("user", "user@test.com", "password")

        resource = self.resource_manager.create_resource(
            ResourceType.DATA, "resource", "Desc", owner.user_id
        )

        # 授予访问权限
        self.resource_manager.grant_access(resource.resource_id, user_ids=[user.user_id])

        # 授予用户权限
        user.add_permission(Permission.READ)

        decision = self.access_controller.check_access(
            user.user_id, resource.resource_id, Permission.READ
        )

        assert decision == AccessDecision.ALLOWED

    def test_check_access_without_permission(self):
        """测试无权限的用户访问"""
        owner = self.user_manager.create_user("owner", "owner@test.com", "password")
        user = self.user_manager.create_user("user", "user@test.com", "password")

        resource = self.resource_manager.create_resource(
            ResourceType.DATA, "resource", "Desc", owner.user_id
        )

        decision = self.access_controller.check_access(
            user.user_id, resource.resource_id, Permission.READ
        )

        assert decision == AccessDecision.INSUFFICIENT_PERMISSIONS

    def test_check_access_with_role(self):
        """测试角色访问"""
        owner = self.user_manager.create_user("owner", "owner@test.com", "password")
        user = self.user_manager.create_user("user", "user@test.com", "password")

        role = self.role_manager.create_role("test_role", "Test", Permission.READ)

        resource = self.resource_manager.create_resource(
            ResourceType.DATA, "resource", "Desc", owner.user_id
        )

        # 分配角色给用户
        self.access_controller.assign_role(user.user_id, role.role_id)

        # 授予角色访问
        self.resource_manager.grant_access(resource.resource_id, role_ids=[role.role_id])

        decision = self.access_controller.check_access(
            user.user_id, resource.resource_id, Permission.READ
        )

        assert decision == AccessDecision.ALLOWED

    def test_grant_revoke_permission(self):
        """测试授予和撤销权限"""
        user = self.user_manager.create_user("user", "user@test.com", "password")

        assert self.access_controller.grant_permission(user.user_id, Permission.WRITE)
        assert user.has_permission(Permission.WRITE)

        assert self.access_controller.revoke_permission(user.user_id, Permission.WRITE)
        assert not user.has_permission(Permission.WRITE)

    def test_assign_revoke_role(self):
        """测试分配和撤销角色"""
        user = self.user_manager.create_user("user", "user@test.com", "password")
        role = self.role_manager.create_role("test_role", "Test", Permission.READ)

        assert self.access_controller.assign_role(user.user_id, role.role_id)
        assert role.role_id in user.roles

        assert self.access_controller.revoke_role(user.user_id, role.role_id)
        assert role.role_id not in user.roles

    def test_create_policy(self):
        """测试创建策略"""
        policy = self.access_controller.create_policy(
            name="test_policy",
            effect="allow",
            subjects=["user1"],
            resources=["resource1"],
            actions=["read"],
        )

        assert policy.name == "test_policy"
        assert policy.effect == "allow"

    def test_evaluate_policies(self):
        """测试策略评估"""
        user = self.user_manager.create_user("user", "user@test.com", "password")
        resource = self.resource_manager.create_resource(
            ResourceType.DATA, "resource", "Desc", "owner"
        )

        # 创建允许策略
        self.access_controller.create_policy(
            name="allow_policy",
            effect="allow",
            subjects=[user.user_id],
            resources=[resource.resource_id],
            actions=["read"],
        )

        decision = self.access_controller.evaluate_policies(
            user.user_id, resource.resource_id, "read"
        )

        assert decision == AccessDecision.ALLOWED

    def test_public_resource(self):
        """测试公开资源"""
        owner = self.user_manager.create_user("owner", "owner@test.com", "password")
        user = self.user_manager.create_user("user", "user@test.com", "password")

        resource = self.resource_manager.create_resource(
            ResourceType.DATA, "public_resource", "Desc", owner.user_id, is_public=True
        )

        decision = self.access_controller.check_access(
            user.user_id, resource.resource_id, Permission.READ
        )

        assert decision == AccessDecision.ALLOWED

    def test_get_user_permissions(self):
        """测试获取用户权限"""
        user = self.user_manager.create_user(
            "user", "user@test.com", "password", permissions=Permission.READ
        )

        role = self.role_manager.create_role("role", "Role", Permission.WRITE)
        self.access_controller.assign_role(user.user_id, role.role_id)

        permissions = self.access_controller.get_user_permissions(user.user_id)

        assert (permissions & Permission.READ) == Permission.READ
        assert (permissions & Permission.WRITE) == Permission.WRITE

    def test_export_import_config(self):
        """测试导出导入配置"""
        # 创建一些数据
        user = self.user_manager.create_user("user", "user@test.com", "password")
        role = self.role_manager.create_role("role", "Role", Permission.READ)
        resource = self.resource_manager.create_resource(
            ResourceType.DATA, "resource", "Desc", user.user_id
        )

        # 导出配置
        config = self.access_controller.export_config()

        # 导入到新的控制器
        new_controller = AccessController()
        new_controller.import_config(config)

        # 验证导入的数据
        assert len(new_controller.user_manager.list_users()) == 1
        assert len(new_controller.role_manager.list_roles()) > 0
        assert len(new_controller.resource_manager.list_resources()) == 1


class TestPermissionFlag:
    """测试权限标志"""

    def test_permission_combination(self):
        """测试权限组合"""
        perms = Permission.READ | Permission.WRITE

        assert (perms & Permission.READ) == Permission.READ
        assert (perms & Permission.WRITE) == Permission.WRITE
        assert not (perms & Permission.DELETE) == Permission.DELETE

    def test_permission_contains(self):
        """测试权限包含"""
        full = Permission.FULL

        assert (full & Permission.READ) == Permission.READ
        assert (full & Permission.WRITE) == Permission.WRITE
        assert (full & Permission.DELETE) == Permission.DELETE
        assert (full & Permission.CREATE) == Permission.CREATE

    def test_permission_all(self):
        """测试所有权限"""
        all_perms = Permission.ALL

        assert (all_perms & Permission.ADMIN) == Permission.ADMIN
        assert (all_perms & Permission.SUPER_ADMIN) == Permission.SUPER_ADMIN
        assert (all_perms & Permission.FULL) == Permission.FULL
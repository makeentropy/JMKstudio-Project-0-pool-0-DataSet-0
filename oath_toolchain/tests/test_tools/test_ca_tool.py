"""CA体系主工具单元测试。"""
import pytest

from oath_toolchain.tools.ca_system.tool import CASystemTool
from oath_toolchain.core.registry import ToolRegistry
from oath_toolchain.core.exceptions import ValidationError


class TestCASystemTool:
    """测试CASystemTool类。"""

    def setup_method(self):
        """每个测试前的设置。"""
        self.tool = CASystemTool()

    def test_initialization(self):
        """测试初始化。"""
        assert self.tool.name == "ca_system"
        assert self.tool.description == "JMKstudio CA证书体系工具"
        assert self.tool.version == "0.1.0"
        assert self.tool.category == "crypto"
        assert "crypto" in self.tool.tags
        assert "ca" in self.tool.tags

    def test_registry_integration(self):
        """测试工具注册集成。"""
        ToolRegistry.reset_instance()
        import importlib
        import oath_toolchain.tools.ca_system.tool as tool_module
        importlib.reload(tool_module)

        registry = ToolRegistry()
        assert "ca_system" in registry
        tool_class = registry.get_tool("ca_system")
        assert tool_class.__name__ == "CASystemTool"

    def test_create_tool_from_registry(self):
        """测试从注册表创建工具。"""
        ToolRegistry.reset_instance()
        import importlib
        import oath_toolchain.tools.ca_system.tool as tool_module
        importlib.reload(tool_module)

        registry = ToolRegistry()
        tool = registry.create_tool("ca_system")
        assert tool.name == "ca_system"
        assert tool.description == "JMKstudio CA证书体系工具"

    def test_execute_missing_action(self):
        """测试缺少action参数。"""
        with pytest.raises(ValidationError):
            self.tool.execute({})

    def test_execute_invalid_action(self):
        """测试无效的action参数。"""
        with pytest.raises(ValidationError):
            self.tool.execute({"action": "invalid_action"})

    def test_action_init_root(self):
        """测试init_root操作。"""
        result = self.tool.execute({
            "action": "init_root",
            "ca_name": "Test CA",
            "key_size": 2048,
            "validity_days": 365,
        })

        assert result["success"] is True
        assert result["action"] == "init_root"
        assert result["ca_name"] == "Test CA"
        assert "certificate" in result
        assert "private_key" in result
        assert "BEGIN CERTIFICATE" in result["certificate"]
        assert "BEGIN PRIVATE KEY" in result["private_key"]

    def test_action_create_intermediate(self):
        """测试create_intermediate操作。"""
        self.tool.execute({"action": "init_root", "key_size": 2048})

        result = self.tool.execute({
            "action": "create_intermediate",
            "ca_name": "Test Intermediate CA",
            "ca_type": "intermediate_ca",
            "validity_days": 365,
        })

        assert result["success"] is True
        assert result["action"] == "create_intermediate"
        assert result["ca_name"] == "Test Intermediate CA"
        assert "certificate" in result
        assert "private_key" in result

    def test_action_create_intermediate_fbi(self):
        """测试创建FBI中间CA。"""
        self.tool.execute({"action": "init_root", "key_size": 2048})

        result = self.tool.execute({
            "action": "create_intermediate",
            "ca_name": "FBI CA",
            "ca_type": "fbi_ca",
        })

        assert result["success"] is True
        assert result["ca_type"] == "fbi_ca"

    def test_action_create_intermediate_cia(self):
        """测试创建CIA中间CA。"""
        self.tool.execute({"action": "init_root", "key_size": 2048})

        result = self.tool.execute({
            "action": "create_intermediate",
            "ca_name": "CIA CA",
            "ca_type": "cia_ca",
        })

        assert result["success"] is True
        assert result["ca_type"] == "cia_ca"

    def test_action_issue_cert(self):
        """测试issue_cert操作。"""
        self.tool.execute({"action": "init_root", "key_size": 2048})

        result = self.tool.execute({
            "action": "issue_cert",
            "subject": "test.example.com",
            "cert_type": "end_entity",
            "issuer_ca": "root",
            "validity_days": 365,
            "key_size": 2048,
        })

        assert result["success"] is True
        assert result["action"] == "issue_cert"
        assert result["subject"] == "test.example.com"
        assert "certificate" in result
        assert "private_key" in result

    def test_action_issue_warship_cert(self):
        """测试签发战舰证书。"""
        self.tool.execute({"action": "init_root", "key_size": 2048})

        result = self.tool.execute({
            "action": "issue_cert",
            "subject": "USS Enterprise",
            "cert_type": "warship_cert",
            "issuer_ca": "root",
            "key_size": 2048,
            "extensions": {
                "ship_id": "WARSHIP-001",
                "clearance_level": "top_secret",
                "valid_sectors": ["alpha", "beta"],
                "weapon_system_auth": True,
            },
        })

        assert result["success"] is True
        assert result["cert_type"] == "warship_cert"

    def test_action_issue_science_cert(self):
        """测试签发科学证书。"""
        self.tool.execute({"action": "init_root", "key_size": 2048})

        result = self.tool.execute({
            "action": "issue_cert",
            "subject": "Dr. Scientist",
            "cert_type": "science_cert",
            "issuer_ca": "root",
            "key_size": 2048,
            "extensions": {
                "institution": "JMK Research Lab",
                "research_field": "physics",
                "clearance_level": "level-3",
                "project_ids": ["proj-001"],
            },
        })

        assert result["success"] is True
        assert result["cert_type"] == "science_cert"

    def test_action_verify_cert_valid(self):
        """测试verify_cert操作（有效证书）。"""
        self.tool.execute({"action": "init_root", "key_size": 2048})

        issue_result = self.tool.execute({
            "action": "issue_cert",
            "subject": "verify-test.example.com",
            "cert_type": "end_entity",
            "key_size": 2048,
        })

        result = self.tool.execute({
            "action": "verify_cert",
            "certificate": issue_result["certificate"],
        })

        assert result["success"] is True
        assert result["valid"] is True

    def test_action_verify_chain(self):
        """测试verify_chain操作。"""
        self.tool.execute({"action": "init_root", "key_size": 2048})

        self.tool.execute({
            "action": "create_intermediate",
            "ca_name": "Intermediate CA",
            "ca_type": "intermediate_ca",
        })

        issue_result = self.tool.execute({
            "action": "issue_cert",
            "subject": "chain-test.example.com",
            "cert_type": "end_entity",
            "issuer_ca": "Intermediate CA",
            "key_size": 2048,
        })

        intermediate_cert = self.tool._ca.get_ca_certificate("Intermediate CA")

        result = self.tool.execute({
            "action": "verify_chain",
            "certificate": issue_result["certificate"],
            "intermediate_certs": [intermediate_cert.decode("utf-8")],
        })

        assert result["success"] is True
        assert "chain_depth" in result
        assert "chain_info" in result

    def test_action_revoke_cert(self):
        """测试revoke_cert操作。"""
        self.tool.execute({"action": "init_root", "key_size": 2048})

        issue_result = self.tool.execute({
            "action": "issue_cert",
            "subject": "revoke-test.example.com",
            "cert_type": "end_entity",
            "key_size": 2048,
        })

        cert_info = self.tool.execute({
            "action": "cert_info",
            "certificate": issue_result["certificate"],
        })

        serial_number = cert_info["info"]["serial_number"]

        result = self.tool.execute({
            "action": "revoke_cert",
            "serial_number": serial_number,
            "reason": "key_compromise",
        })

        assert result["success"] is True
        assert result["revoked"] is True

    def test_action_revoked_cert_verify_fails(self):
        """测试已吊销证书验证失败。"""
        self.tool.execute({"action": "init_root", "key_size": 2048})

        issue_result = self.tool.execute({
            "action": "issue_cert",
            "subject": "revoked-verify.example.com",
            "cert_type": "end_entity",
            "key_size": 2048,
        })

        cert_info = self.tool.execute({
            "action": "cert_info",
            "certificate": issue_result["certificate"],
        })

        serial_number = cert_info["info"]["serial_number"]

        self.tool.execute({
            "action": "revoke_cert",
            "serial_number": serial_number,
            "reason": "key_compromise",
        })

        verify_result = self.tool.execute({
            "action": "verify_cert",
            "certificate": issue_result["certificate"],
        })

        assert verify_result["success"] is True
        assert verify_result["valid"] is False

    def test_action_renew_cert(self):
        """测试renew_cert操作。"""
        self.tool.execute({"action": "init_root", "key_size": 2048})

        issue_result = self.tool.execute({
            "action": "issue_cert",
            "subject": "renew-test.example.com",
            "cert_type": "end_entity",
            "validity_days": 30,
            "key_size": 2048,
        })

        result = self.tool.execute({
            "action": "renew_cert",
            "certificate": issue_result["certificate"],
            "private_key": issue_result["private_key"],
            "new_validity_days": 365,
        })

        assert result["success"] is True
        assert "certificate" in result
        assert "private_key" in result

    def test_action_list_certs(self):
        """测试list_certs操作。"""
        self.tool.execute({"action": "init_root", "key_size": 2048})

        self.tool.execute({
            "action": "issue_cert",
            "subject": "list1.example.com",
            "cert_type": "end_entity",
            "key_size": 2048,
        })

        self.tool.execute({
            "action": "issue_cert",
            "subject": "list2.example.com",
            "cert_type": "end_entity",
            "key_size": 2048,
        })

        result = self.tool.execute({
            "action": "list_certs",
        })

        assert result["success"] is True
        assert result["count"] >= 3  # root + 2 issued
        assert isinstance(result["certificates"], list)

    def test_action_cert_info(self):
        """测试cert_info操作。"""
        self.tool.execute({"action": "init_root", "key_size": 2048})

        issue_result = self.tool.execute({
            "action": "issue_cert",
            "subject": "info-test.example.com",
            "cert_type": "end_entity",
            "key_size": 2048,
        })

        result = self.tool.execute({
            "action": "cert_info",
            "certificate": issue_result["certificate"],
        })

        assert result["success"] is True
        assert "info" in result
        assert result["info"]["subject"] == "info-test.example.com"
        assert result["info"]["cert_type"] == "end_entity"

    def test_action_generate_crl(self):
        """测试generate_crl操作。"""
        self.tool.execute({"action": "init_root", "key_size": 2048})

        result = self.tool.execute({
            "action": "generate_crl",
            "next_update_days": 30,
        })

        assert result["success"] is True
        assert "crl" in result
        assert "BEGIN X509 CRL" in result["crl"]

    def test_validate_params_missing_action(self):
        """测试参数验证：缺少action。"""
        with pytest.raises(ValidationError):
            self.tool.validate_params({})

    def test_validate_params_invalid_action(self):
        """测试参数验证：无效action。"""
        with pytest.raises(ValidationError):
            self.tool.validate_params({"action": "invalid"})

    def test_validate_params_valid_action(self):
        """测试参数验证：有效action。"""
        assert self.tool.validate_params({"action": "init_root"}) is True

    def test_metadata(self):
        """测试工具元数据。"""
        metadata = self.tool.metadata
        assert metadata["name"] == "ca_system"
        assert metadata["description"] == "JMKstudio CA证书体系工具"
        assert metadata["version"] == "0.1.0"
        assert metadata["category"] == "crypto"
        assert isinstance(metadata["tags"], list)

    def test_tool_repr(self):
        """测试工具的字符串表示。"""
        repr_str = repr(self.tool)
        assert "CASystemTool" in repr_str
        assert "ca_system" in repr_str

    def test_tool_str(self):
        """测试工具的可读字符串。"""
        str_repr = str(self.tool)
        assert "ca_system" in str_repr
        assert "JMKstudio CA证书体系工具" in str_repr

    def test_three_level_chain_full_test(self):
        """测试完整的三级证书链流程。"""
        self.tool.execute({
            "action": "init_root",
            "ca_name": "JMKstudio Root CA",
            "key_size": 2048,
        })

        self.tool.execute({
            "action": "create_intermediate",
            "ca_name": "FBI Intermediate CA",
            "ca_type": "fbi_ca",
        })

        issue_result = self.tool.execute({
            "action": "issue_cert",
            "subject": "Agent Smith",
            "cert_type": "end_entity",
            "issuer_ca": "FBI Intermediate CA",
            "key_size": 2048,
        })

        fbi_ca_cert = self.tool._ca.get_ca_certificate("FBI Intermediate CA")

        verify_result = self.tool.execute({
            "action": "verify_chain",
            "certificate": issue_result["certificate"],
            "intermediate_certs": [fbi_ca_cert.decode("utf-8")],
        })

        assert verify_result["success"] is True
        assert verify_result["chain_depth"] >= 3
        assert len(verify_result["chain_info"]) >= 3

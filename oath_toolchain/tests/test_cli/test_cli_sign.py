"""签名验证CLI命令测试。"""
import os
import tempfile

import pytest
from click.testing import CliRunner

from oath_toolchain.cli.main import cli


class TestCLISignVerify:
    """签名验证命令测试类。"""

    @pytest.fixture
    def runner(self):
        """创建CLI测试运行器。"""
        return CliRunner()

    @pytest.fixture
    def tmpdir(self):
        """创建临时目录。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            yield tmpdir

    def test_sign_rsa(self, runner, tmpdir):
        """测试RSA签名。"""
        input_file = os.path.join(tmpdir, "input.txt")
        key_file = os.path.join(tmpdir, "key.pem")
        sig_file = os.path.join(tmpdir, "sig.bin")

        with open(input_file, "w", encoding="utf-8") as f:
            f.write("Hello, Oath!")

        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        with open(key_file, "wb") as f:
            f.write(pem)

        result = runner.invoke(cli, [
            "sign", "rsa",
            "-i", input_file,
            "-k", key_file,
            "-o", sig_file,
        ])

        assert result.exit_code == 0
        assert os.path.exists(sig_file)
        assert os.path.getsize(sig_file) > 0

    def test_verify_rsa(self, runner, tmpdir):
        """测试RSA验证。"""
        input_file = os.path.join(tmpdir, "input.txt")
        key_file = os.path.join(tmpdir, "key.pem")
        pubkey_file = os.path.join(tmpdir, "pubkey.pem")
        sig_file = os.path.join(tmpdir, "sig.bin")

        with open(input_file, "w", encoding="utf-8") as f:
            f.write("Hello, Oath!")

        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization
        from cryptography.hazmat.primitives import hashes
        from cryptography.hazmat.primitives.asymmetric import padding

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        with open(key_file, "wb") as f:
            f.write(pem)

        pub_pem = private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        with open(pubkey_file, "wb") as f:
            f.write(pub_pem)

        with open(input_file, "rb") as f:
            data = f.read()
        signature = private_key.sign(data, padding.PKCS1v15(), hashes.SHA256())
        with open(sig_file, "wb") as f:
            f.write(signature)

        result = runner.invoke(cli, [
            "verify", "rsa",
            "-i", input_file,
            "-k", pubkey_file,
            "-s", sig_file,
        ])

        assert result.exit_code == 0
        assert "valid" in result.output.lower() or "成功" in result.output

    def test_sign_hmac(self, runner, tmpdir):
        """测试HMAC签名。"""
        input_file = os.path.join(tmpdir, "input.txt")
        key_file = os.path.join(tmpdir, "key.bin")
        sig_file = os.path.join(tmpdir, "sig.bin")

        with open(input_file, "w", encoding="utf-8") as f:
            f.write("Hello, Oath!")

        import os as _os
        with open(key_file, "wb") as f:
            f.write(_os.urandom(32))

        result = runner.invoke(cli, [
            "sign", "hmac",
            "-i", input_file,
            "-k", key_file,
            "-o", sig_file,
        ])

        assert result.exit_code == 0
        assert os.path.exists(sig_file)
        assert os.path.getsize(sig_file) > 0

    def test_verify_hmac(self, runner, tmpdir):
        """测试HMAC验证。"""
        input_file = os.path.join(tmpdir, "input.txt")
        key_file = os.path.join(tmpdir, "key.bin")
        sig_file = os.path.join(tmpdir, "sig.bin")

        with open(input_file, "w", encoding="utf-8") as f:
            f.write("Hello, Oath!")

        import os as _os
        key_data = _os.urandom(32)
        with open(key_file, "wb") as f:
            f.write(key_data)

        result = runner.invoke(cli, [
            "sign", "hmac",
            "-i", input_file,
            "-k", key_file,
            "-o", sig_file,
        ])
        assert result.exit_code == 0

        result = runner.invoke(cli, [
            "verify", "hmac",
            "-i", input_file,
            "-k", key_file,
            "-s", sig_file,
        ])

        assert result.exit_code == 0
        assert "valid" in result.output.lower() or "成功" in result.output

    def test_sign_geometric(self, runner, tmpdir):
        """测试几何证明签名。"""
        input_file = os.path.join(tmpdir, "input.txt")
        sig_file = os.path.join(tmpdir, "proof.json")

        with open(input_file, "w", encoding="utf-8") as f:
            f.write("Hello, Oath!")

        result = runner.invoke(cli, [
            "sign", "geometric",
            "-i", input_file,
            "-k", "my_secret_key",
            "-o", sig_file,
        ])

        assert result.exit_code == 0
        assert os.path.exists(sig_file)

    def test_verify_geometric(self, runner, tmpdir):
        """测试几何证明验证。"""
        input_file = os.path.join(tmpdir, "input.txt")
        sig_file = os.path.join(tmpdir, "proof.json")

        with open(input_file, "w", encoding="utf-8") as f:
            f.write("Hello, Oath!")

        result = runner.invoke(cli, [
            "sign", "geometric",
            "-i", input_file,
            "-k", "my_secret_key",
            "-o", sig_file,
        ])
        assert result.exit_code == 0

        result = runner.invoke(cli, [
            "verify", "geometric",
            "-i", input_file,
            "-s", sig_file,
        ])

        assert result.exit_code == 0

    def test_sign_help(self, runner):
        """测试sign帮助信息。"""
        result = runner.invoke(cli, ["sign", "--help"])
        assert result.exit_code == 0
        assert "签名" in result.output or "sign" in result.output.lower()

    def test_verify_help(self, runner):
        """测试verify帮助信息。"""
        result = runner.invoke(cli, ["verify", "--help"])
        assert result.exit_code == 0
        assert "验证" in result.output or "verify" in result.output.lower()

    def test_sign_rsa_help(self, runner):
        """测试sign rsa帮助信息。"""
        result = runner.invoke(cli, ["sign", "rsa", "--help"])
        assert result.exit_code == 0

    def test_sign_hmac_help(self, runner):
        """测试sign hmac帮助信息。"""
        result = runner.invoke(cli, ["sign", "hmac", "--help"])
        assert result.exit_code == 0

    def test_sign_geometric_help(self, runner):
        """测试sign geometric帮助信息。"""
        result = runner.invoke(cli, ["sign", "geometric", "--help"])
        assert result.exit_code == 0

    def test_sign_multi_help(self, runner):
        """测试sign multi帮助信息。"""
        result = runner.invoke(cli, ["sign", "multi", "--help"])
        assert result.exit_code == 0

    def test_verify_rsa_help(self, runner):
        """测试verify rsa帮助信息。"""
        result = runner.invoke(cli, ["verify", "rsa", "--help"])
        assert result.exit_code == 0

    def test_verify_hmac_help(self, runner):
        """测试verify hmac帮助信息。"""
        result = runner.invoke(cli, ["verify", "hmac", "--help"])
        assert result.exit_code == 0

    def test_verify_geometric_help(self, runner):
        """测试verify geometric帮助信息。"""
        result = runner.invoke(cli, ["verify", "geometric", "--help"])
        assert result.exit_code == 0

    def test_verify_multi_help(self, runner):
        """测试verify multi帮助信息。"""
        result = runner.invoke(cli, ["verify", "multi", "--help"])
        assert result.exit_code == 0

    def test_verify_cert_help(self, runner):
        """测试verify cert帮助信息。"""
        result = runner.invoke(cli, ["verify", "cert", "--help"])
        assert result.exit_code == 0

    def test_sign_missing_input(self, runner, tmpdir):
        """测试缺少输入文件。"""
        key_file = os.path.join(tmpdir, "key.bin")
        with open(key_file, "wb") as f:
            f.write(b"key")

        result = runner.invoke(cli, [
            "sign", "rsa",
            "-i", "/nonexistent/file.txt",
            "-k", key_file,
        ])
        assert result.exit_code != 0

    def test_verify_cert(self, runner, tmpdir):
        """测试证书验证命令。"""
        from cryptography import x509
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.x509.oid import NameOID
        from datetime import datetime, timedelta, timezone

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "Test CA"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(private_key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now(timezone.utc))
            .not_valid_after(datetime.now(timezone.utc) + timedelta(days=365))
            .sign(private_key, hashes.SHA256())
        )

        cert_file = os.path.join(tmpdir, "cert.pem")
        with open(cert_file, "wb") as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))

        result = runner.invoke(cli, [
            "verify", "cert",
            "-c", cert_file,
        ])

        assert result.exit_code == 0

    def test_sign_rsa_json(self, runner, tmpdir):
        """测试JSON格式的RSA签名。"""
        input_file = os.path.join(tmpdir, "input.txt")
        key_file = os.path.join(tmpdir, "key.pem")
        sig_file = os.path.join(tmpdir, "sig.bin")

        with open(input_file, "w", encoding="utf-8") as f:
            f.write("Hello, Oath!")

        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.primitives import serialization

        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        with open(key_file, "wb") as f:
            f.write(pem)

        result = runner.invoke(cli, [
            "-o", "json",
            "sign", "rsa",
            "-i", input_file,
            "-k", key_file,
            "-o", sig_file,
        ])

        assert result.exit_code == 0

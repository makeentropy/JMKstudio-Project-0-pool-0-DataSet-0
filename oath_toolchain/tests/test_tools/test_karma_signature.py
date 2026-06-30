"""标签签名与验证单元测试。"""
import pytest

from oath_toolchain.tools.karma_tags.karma_tag import KarmaTag
from oath_toolchain.tools.karma_tags.tag_signature import TagSigner
from oath_toolchain.core.crypto.primitives import RSACipher


class TestTagSigner:
    """测试TagSigner类。"""

    def setup_method(self):
        """每个测试前的设置。"""
        self.private_key, self.public_key = RSACipher.generate_keypair(key_size=2048)
        self.private_key_pem = RSACipher.serialize_private_key(self.private_key)
        self.public_key_pem = RSACipher.serialize_public_key(self.public_key)

    def test_initialization_with_private_key(self):
        """测试使用私钥初始化。"""
        signer = TagSigner(private_key_pem=self.private_key_pem)
        assert signer._private_key is not None
        assert signer._public_key is not None

    def test_initialization_with_public_key(self):
        """测试使用公钥初始化。"""
        signer = TagSigner(public_key_pem=self.public_key_pem)
        assert signer._private_key is None
        assert signer._public_key is not None

    def test_initialization_with_both(self):
        """测试使用两者初始化。"""
        signer = TagSigner(
            private_key_pem=self.private_key_pem,
            public_key_pem=self.public_key_pem,
        )
        assert signer._private_key is not None
        assert signer._public_key is not None

    def test_initialization_empty(self):
        """测试空初始化。"""
        signer = TagSigner()
        assert signer._private_key is None
        assert signer._public_key is None

    def test_sign_gpgca(self):
        """测试GPG CA签名。"""
        signer = TagSigner(private_key_pem=self.private_key_pem)
        tag = KarmaTag(
            datafor="签名测试",
            datefor="20240101",
            datatag=["test"],
        )
        assert tag.gpgca == ""
        signed_tag = signer.sign_tag(tag, signer="gpgca")
        assert signed_tag.gpgca != ""
        assert signed_tag is tag

    def test_sign_jmkca(self):
        """测试JMK CA签名。"""
        signer = TagSigner(private_key_pem=self.private_key_pem)
        tag = KarmaTag(
            datafor="签名测试",
            datefor="20240101",
        )
        assert tag.jmkca == ""
        signed_tag = signer.sign_tag(tag, signer="jmkca")
        assert signed_tag.jmkca != ""

    def test_sign_custom(self):
        """测试自定义签名。"""
        signer = TagSigner(private_key_pem=self.private_key_pem)
        tag = KarmaTag(
            datafor="签名测试",
            datefor="20240101",
        )
        signed_tag = signer.sign_tag(tag, signer="custom")
        assert signed_tag.get_custom_field("custom_signature") is not None

    def test_sign_invalid_signer(self):
        """测试无效签名者。"""
        signer = TagSigner(private_key_pem=self.private_key_pem)
        tag = KarmaTag(datafor="test", datefor="20240101")
        with pytest.raises(ValueError, match="不支持的签名者"):
            signer.sign_tag(tag, signer="invalid")

    def test_sign_no_private_key(self):
        """测试没有私钥时签名。"""
        signer = TagSigner(public_key_pem=self.public_key_pem)
        tag = KarmaTag(datafor="test", datefor="20240101")
        with pytest.raises(ValueError, match="签名需要私钥"):
            signer.sign_tag(tag)

    def test_verify_gpgca_valid(self):
        """测试验证有效的GPG CA签名。"""
        signer = TagSigner(private_key_pem=self.private_key_pem)
        tag = KarmaTag(
            datafor="验证测试",
            datefor="20240101",
            datatag=["test"],
        )
        signer.sign_tag(tag, signer="gpgca")
        valid = signer.verify_tag(tag, signer="gpgca")
        assert valid is True

    def test_verify_jmkca_valid(self):
        """测试验证有效的JMK CA签名。"""
        signer = TagSigner(private_key_pem=self.private_key_pem)
        tag = KarmaTag(
            datafor="验证测试",
            datefor="20240101",
        )
        signer.sign_tag(tag, signer="jmkca")
        valid = signer.verify_tag(tag, signer="jmkca")
        assert valid is True

    def test_verify_custom_valid(self):
        """测试验证有效的自定义签名。"""
        signer = TagSigner(private_key_pem=self.private_key_pem)
        tag = KarmaTag(
            datafor="验证测试",
            datefor="20240101",
        )
        signer.sign_tag(tag, signer="custom")
        valid = signer.verify_tag(tag, signer="custom")
        assert valid is True

    def test_verify_tampered_data(self):
        """测试验证被篡改的数据。"""
        signer = TagSigner(private_key_pem=self.private_key_pem)
        tag = KarmaTag(
            datafor="原始数据",
            datefor="20240101",
        )
        signer.sign_tag(tag, signer="gpgca")
        tag.datafor = "篡改后的数据"
        valid = signer.verify_tag(tag, signer="gpgca")
        assert valid is False

    def test_verify_no_signature(self):
        """测试验证没有签名的标签。"""
        signer = TagSigner(public_key_pem=self.public_key_pem)
        tag = KarmaTag(
            datafor="无签名",
            datefor="20240101",
        )
        valid = signer.verify_tag(tag, signer="gpgca")
        assert valid is False

    def test_verify_invalid_signer(self):
        """测试验证无效签名者。"""
        signer = TagSigner(public_key_pem=self.public_key_pem)
        tag = KarmaTag(datafor="test", datefor="20240101")
        with pytest.raises(ValueError, match="不支持的签名者"):
            signer.verify_tag(tag, signer="invalid")

    def test_verify_no_public_key(self):
        """测试没有公钥时验证。"""
        signer = TagSigner()
        tag = KarmaTag(datafor="test", datefor="20240101")
        with pytest.raises(ValueError, match="验证需要公钥"):
            signer.verify_tag(tag)

    def test_sign_with_cert(self):
        """测试使用证书签名。"""
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        import datetime

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "Test CA"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(self.public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.UTC))
            .not_valid_after(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365))
            .sign(self.private_key, hashes.SHA256())
        )
        cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)

        signer = TagSigner()
        tag = KarmaTag(datafor="证书签名测试", datefor="20240101")
        signed_tag = signer.sign_with_cert(tag, cert_pem, self.private_key_pem)
        assert signed_tag.get_custom_field("custom_signature") is not None
        assert signed_tag.get_custom_field("signer_cert") is not None

    def test_verify_with_cert_valid(self):
        """测试使用证书验证有效签名。"""
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        import datetime

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "Test CA"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(self.public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.UTC))
            .not_valid_after(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365))
            .sign(self.private_key, hashes.SHA256())
        )
        cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)

        signer = TagSigner()
        tag = KarmaTag(datafor="证书验证测试", datefor="20240101")
        signer.sign_with_cert(tag, cert_pem, self.private_key_pem)
        valid = signer.verify_with_cert(tag, cert_pem)
        assert valid is True

    def test_verify_with_cert_tampered(self):
        """测试使用证书验证被篡改的数据。"""
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        import datetime

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, "Test CA"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(self.public_key)
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.now(datetime.UTC))
            .not_valid_after(datetime.datetime.now(datetime.UTC) + datetime.timedelta(days=365))
            .sign(self.private_key, hashes.SHA256())
        )
        cert_pem = cert.public_bytes(encoding=serialization.Encoding.PEM)

        signer = TagSigner()
        tag = KarmaTag(datafor="原始数据", datefor="20240101")
        signer.sign_with_cert(tag, cert_pem, self.private_key_pem)
        tag.datafor = "篡改后的数据"
        valid = signer.verify_with_cert(tag, cert_pem)
        assert valid is False

    def test_get_signers_empty(self):
        """测试获取空标签的签名者。"""
        signer = TagSigner()
        tag = KarmaTag(datafor="test", datefor="20240101")
        signers = signer.get_signers(tag)
        assert signers == []

    def test_get_signers_gpgca(self):
        """测试获取GPG CA签名者。"""
        signer = TagSigner(private_key_pem=self.private_key_pem)
        tag = KarmaTag(datafor="test", datefor="20240101")
        signer.sign_tag(tag, signer="gpgca")
        signers = signer.get_signers(tag)
        assert "gpgca" in signers
        assert len(signers) == 1

    def test_get_signers_multiple(self):
        """测试获取多个签名者。"""
        signer = TagSigner(private_key_pem=self.private_key_pem)
        tag = KarmaTag(datafor="test", datefor="20240101")
        signer.sign_tag(tag, signer="gpgca")
        signer.sign_tag(tag, signer="jmkca")
        signer.sign_tag(tag, signer="custom")
        signers = signer.get_signers(tag)
        assert "gpgca" in signers
        assert "jmkca" in signers
        assert "custom" in signers
        assert len(signers) == 3

    def test_set_private_key(self):
        """测试设置私钥。"""
        signer = TagSigner()
        assert signer._private_key is None
        signer.set_private_key(self.private_key_pem)
        assert signer._private_key is not None
        assert signer._public_key is not None

    def test_set_public_key(self):
        """测试设置公钥。"""
        signer = TagSigner()
        assert signer._public_key is None
        signer.set_public_key(self.public_key_pem)
        assert signer._public_key is not None

    def test_full_sign_verify_flow(self):
        """测试完整的签名验证流程。"""
        signer = TagSigner(private_key_pem=self.private_key_pem)
        tag = KarmaTag(
            datafor="完整流程测试",
            datefor="20240630",
            datatag=["important", "test"],
            tag=["verified"],
            encrypt_xor=False,
            stego_dim=2,
            custom_info="自定义信息",
        )

        signed_tag = signer.sign_tag(tag, signer="gpgca")
        assert signed_tag.gpgca != ""

        valid = signer.verify_tag(signed_tag, signer="gpgca")
        assert valid is True

        tag_json = signed_tag.to_json()
        restored_tag = KarmaTag.from_json(tag_json)
        assert restored_tag.gpgca == signed_tag.gpgca
        valid_restored = signer.verify_tag(restored_tag, signer="gpgca")
        assert valid_restored is True

    def test_different_keys_fail_verify(self):
        """测试不同密钥对验证失败。"""
        private_key1, public_key1 = RSACipher.generate_keypair(key_size=2048)
        private_key2, public_key2 = RSACipher.generate_keypair(key_size=2048)
        private_pem1 = RSACipher.serialize_private_key(private_key1)
        public_pem2 = RSACipher.serialize_public_key(public_key2)

        signer1 = TagSigner(private_key_pem=private_pem1)
        signer2 = TagSigner(public_key_pem=public_pem2)

        tag = KarmaTag(datafor="test", datefor="20240101")
        signer1.sign_tag(tag, signer="gpgca")
        valid = signer2.verify_tag(tag, signer="gpgca")
        assert valid is False

"""
BaseXOR 探针测试

覆盖：
- BaseXOR 编解码器（往返、密钥不匹配、魔数校验）
- 代码签名凭据签发
- 数据块签名与校验往返
- 篡改检测（数据块/签名被篡改）
- 合法合规矩阵聚合
- 清单信封往返
- APT 联络线配置
"""

import base64
import hashlib
import json

import pytest
from click.testing import CliRunner

from ai_llm_agent_crawler.cli import basexor
from ai_llm_agent_crawler.security.basexor import (
    APTContactLine,
    BaseXORCodec,
    BaseXORProbe,
    CodeSigningCredential,
    ComplianceCheck,
    ComplianceMatrix,
    ComplianceVerdict,
    MANIFEST_FORMAT,
    build_deb_package,
    decode_manifest_envelope,
    encode_manifest_envelope,
)
from ai_llm_agent_crawler.security.ca_system import CertificateAuthority
from ai_llm_agent_crawler.security.datachain_compression import DataBlock


# ---------------------------------------------------------------------------
# 测试夹具
# ---------------------------------------------------------------------------


@pytest.fixture
def ca():
    ca = CertificateAuthority(name="Test BaseXOR CA", key_size=2048)
    ca.initialize()
    return ca


@pytest.fixture
def credential(ca):
    return CodeSigningCredential.issue(ca, common_name="basexor-probe-test")


@pytest.fixture
def probe(ca, credential):
    return BaseXORProbe(ca=ca, credential=credential, probe_id="bx-test")


@pytest.fixture
def blocks():
    return [
        DataBlock(block_id="blk-001", data=b"first block payload " * 8, sequence_number=1),
        DataBlock(block_id="blk-002", data=b"second block payload " * 8, sequence_number=2),
    ]


# ---------------------------------------------------------------------------
# BaseXOR 编解码器
# ---------------------------------------------------------------------------


class TestBaseXORCodec:
    def test_round_trip(self):
        codec = BaseXORCodec("secret-key")
        data = b"hello basexor \x00\x01\xff" * 10
        encoded = codec.encode(data)
        assert encoded != data.decode("latin1", errors="ignore")
        assert codec.decode(encoded) == data

    def test_encode_is_base64_text(self):
        codec = BaseXORCodec("k")
        encoded = codec.encode(b"abc")
        # 应为合法 base64 文本
        base64.b64decode(encoded.encode("ascii"))

    def test_magic_header(self):
        codec = BaseXORCodec("k")
        encoded = codec.encode(b"x")
        raw = base64.b64decode(encoded.encode("ascii"))
        assert raw[:3] == BaseXORCodec.MAGIC

    def test_wrong_key_rejected(self):
        codec_a = BaseXORCodec("key-a")
        codec_b = BaseXORCodec("key-b")
        encoded = codec_a.encode(b"secret")
        with pytest.raises(ValueError, match="密钥不匹配"):
            codec_b.decode(encoded)

    def test_corrupted_magic_rejected(self):
        codec = BaseXORCodec("k")
        encoded = codec.encode(b"data")
        raw = bytearray(base64.b64decode(encoded.encode("ascii")))
        raw[0] = ord("X")  # 破坏魔数
        corrupted = base64.b64encode(bytes(raw)).decode("ascii")
        with pytest.raises(ValueError, match="魔数不匹配"):
            codec.decode(corrupted)

    def test_from_ca_matches_from_fingerprint(self, ca):
        from ai_llm_agent_crawler.security.basexor import ca_fingerprint_from_pem
        ca_cert_pem = ca.export_ca_certificate("PEM").decode("ascii")
        c1 = BaseXORCodec.from_ca(ca)
        c2 = BaseXORCodec.from_fingerprint(ca_fingerprint_from_pem(ca_cert_pem))
        assert c1.key == c2.key

    def test_empty_key_rejected(self):
        with pytest.raises(ValueError):
            BaseXORCodec("")


# ---------------------------------------------------------------------------
# 代码签名凭据
# ---------------------------------------------------------------------------


class TestCodeSigningCredential:
    def test_issue(self, credential):
        assert "BEGIN CERTIFICATE" in credential.cert_pem
        assert "BEGIN PRIVATE KEY" in credential.private_key_pem
        assert "BEGIN CERTIFICATE" in credential.ca_cert_pem

    def test_load(self, credential):
        cert = credential.load_certificate()
        key = credential.load_private_key()
        assert cert is not None
        assert key is not None

    def test_dict_round_trip(self, credential):
        restored = CodeSigningCredential.from_dict(credential.to_dict())
        assert restored.cert_pem == credential.cert_pem
        assert restored.private_key_pem == credential.private_key_pem


# ---------------------------------------------------------------------------
# 探针签名与校验
# ---------------------------------------------------------------------------


class TestBaseXORProbeSignVerify:
    def test_sign_block_produces_valid_signature(self, probe, blocks):
        manifest = probe.sign_block(blocks[0])
        assert manifest.block_id == "blk-001"
        assert manifest.checksum == hashlib.sha256(blocks[0].data).hexdigest()
        assert manifest.signature  # 非空
        assert manifest.signer_cert_pem
        assert manifest.ca_cert_pem

    def test_verify_valid_block_is_compliant(self, probe, blocks):
        manifest = probe.sign_block(blocks[0])
        items = probe.verify_manifest(manifest, block=blocks[0])
        verdicts = {i.check: i.verdict for i in items}
        assert verdicts[ComplianceCheck.MANIFEST_INTEGRITY] == ComplianceVerdict.COMPLIANT
        assert verdicts[ComplianceCheck.BLOCK_CHECKSUM] == ComplianceVerdict.COMPLIANT
        assert verdicts[ComplianceCheck.CERT_CHAIN] == ComplianceVerdict.COMPLIANT
        assert verdicts[ComplianceCheck.CERT_NOT_EXPIRED] == ComplianceVerdict.COMPLIANT
        assert verdicts[ComplianceCheck.CERT_NOT_REVOKED] == ComplianceVerdict.COMPLIANT
        assert verdicts[ComplianceCheck.CA_SIGNATURE] == ComplianceVerdict.COMPLIANT

    def test_tampered_block_data_detected(self, probe, blocks):
        manifest = probe.sign_block(blocks[0])
        tampered = DataBlock(
            block_id=blocks[0].block_id,
            data=blocks[0].data + b"TAMPER",
            sequence_number=blocks[0].sequence_number,
        )
        items = probe.verify_manifest(manifest, block=tampered)
        checksum_item = next(i for i in items if i.check == ComplianceCheck.BLOCK_CHECKSUM)
        assert checksum_item.verdict == ComplianceVerdict.NONCOMPLIANT
        # 签名仍有效（签名覆盖的是原 checksum，与篡改后的数据无关）
        sig_item = next(i for i in items if i.check == ComplianceCheck.CA_SIGNATURE)
        assert sig_item.verdict == ComplianceVerdict.COMPLIANT

    def test_tampered_signature_detected(self, probe, blocks):
        manifest = probe.sign_block(blocks[0])
        # 翻转签名首字节
        sig_bytes = bytearray(base64.b64decode(manifest.signature))
        sig_bytes[0] ^= 0xFF
        manifest.signature = base64.b64encode(bytes(sig_bytes)).decode("ascii")
        items = probe.verify_manifest(manifest, block=blocks[0])
        sig_item = next(i for i in items if i.check == ComplianceCheck.CA_SIGNATURE)
        assert sig_item.verdict == ComplianceVerdict.NONCOMPLIANT

    def test_revoked_certificate_detected(self, ca, credential, blocks):
        probe = BaseXORProbe(ca=ca, credential=credential)
        manifest = probe.sign_block(blocks[0])
        # 吊销签名证书
        signer_cert = credential.load_certificate()
        ca.revoke_certificate(str(signer_cert.serial_number), "测试吊销")
        items = probe.verify_manifest(manifest, block=blocks[0])
        revoked_item = next(i for i in items if i.check == ComplianceCheck.CERT_NOT_REVOKED)
        assert revoked_item.verdict == ComplianceVerdict.NONCOMPLIANT

    def test_verify_without_ca_reports_revocation_unknown(self, credential, blocks):
        # 仅校验模式：未提供 CA，吊销状态应为未知
        probe = BaseXORProbe(credential=credential)
        manifest = probe.sign_block(blocks[0])
        items = probe.verify_manifest(manifest, block=blocks[0])
        revoked_item = next(i for i in items if i.check == ComplianceCheck.CERT_NOT_REVOKED)
        assert revoked_item.verdict == ComplianceVerdict.UNKNOWN

    def test_manifest_envelope_round_trip(self, probe, blocks):
        manifest = probe.sign_block(blocks[0])
        envelope = encode_manifest_envelope(manifest)
        assert envelope["format"] == MANIFEST_FORMAT
        assert envelope["ca_fingerprint"]
        assert envelope["payload"]
        restored = decode_manifest_envelope(envelope)
        assert restored.block_id == manifest.block_id
        assert restored.checksum == manifest.checksum
        assert restored.signature == manifest.signature


# ---------------------------------------------------------------------------
# 合法合规矩阵
# ---------------------------------------------------------------------------


class TestComplianceMatrix:
    def test_matrix_all_compliant(self, probe, blocks):
        manifests = [probe.sign_block(b) for b in blocks]
        block_map = {b.block_id: b for b in blocks}
        matrix = probe.verify_blocks(manifests, blocks=block_map)
        assert matrix.overall_verdict() == ComplianceVerdict.COMPLIANT
        assert all(
            matrix.block_verdict(b.block_id) == ComplianceVerdict.COMPLIANT for b in blocks
        )

    def test_matrix_with_noncompliant(self, probe, blocks):
        manifests = [probe.sign_block(b) for b in blocks]
        # 篡改第一个块的签名
        sig_bytes = bytearray(base64.b64decode(manifests[0].signature))
        sig_bytes[0] ^= 0xFF
        manifests[0].signature = base64.b64encode(bytes(sig_bytes)).decode("ascii")
        block_map = {b.block_id: b for b in blocks}
        matrix = probe.verify_blocks(manifests, blocks=block_map)
        assert matrix.overall_verdict() == ComplianceVerdict.NONCOMPLIANT
        assert matrix.block_verdict(blocks[0].block_id) == ComplianceVerdict.NONCOMPLIANT
        assert matrix.block_verdict(blocks[1].block_id) == ComplianceVerdict.COMPLIANT

    def test_matrix_to_dict(self, probe, blocks):
        manifests = [probe.sign_block(b) for b in blocks]
        matrix = probe.verify_blocks(manifests, blocks={b.block_id: b for b in blocks})
        d = matrix.to_dict()
        assert d["overall_verdict"] == ComplianceVerdict.COMPLIANT.value
        assert len(d["blocks"]) == 2
        assert {b["block_id"] for b in d["blocks"]} == {"blk-001", "blk-002"}

    def test_matrix_to_table_rows(self, probe, blocks):
        manifests = [probe.sign_block(b) for b in blocks]
        matrix = probe.verify_blocks(manifests, blocks={b.block_id: b for b in blocks})
        rows = matrix.to_table_rows()
        assert len(rows) == 2
        for check in ComplianceCheck:
            assert check.value in rows[0]

    def test_empty_matrix_is_unknown(self):
        matrix = ComplianceMatrix()
        assert matrix.overall_verdict() == ComplianceVerdict.UNKNOWN


# ---------------------------------------------------------------------------
# APT 联络线
# ---------------------------------------------------------------------------


class TestAPTContactLine:
    def test_sources_entry_contains_signed_by(self):
        contact = APTContactLine()
        entry = contact.sources_entry()
        assert entry.startswith("deb [signed-by=")
        assert "kali" in entry
        assert "main" in entry

    def test_install_instructions_has_commands(self):
        contact = APTContactLine()
        instructions = contact.install_instructions()
        assert "apt update" in instructions
        assert "gpg --dearmor" in instructions
        assert "basexor-probe" in instructions

    def test_custom_config(self):
        contact = APTContactLine(
            repo_url="https://mirrors.aliyun.com/basexor",
            distribution="kali-rolling",
            component="contrib",
        )
        entry = contact.sources_entry()
        assert "mirrors.aliyun.com/basexor" in entry
        assert "kali-rolling" in entry
        assert "contrib" in entry

    def test_to_dict(self):
        contact = APTContactLine()
        d = contact.to_dict()
        assert d["distribution"] == "kali"
        assert d["sources_entry"]


class TestBuildDebPackage:
    def test_staging_only_when_no_dpkg(self, tmp_path):
        # 在任何环境下都应能暂存目录
        deb_path = build_deb_package(
            staging_dir=tmp_path / "stage",
            output_dir=tmp_path / "out",
            version="0.0.1",
            run_dpkg=False,
        )
        assert deb_path is None
        staging = tmp_path / "stage" / "basexor-probe"
        assert (staging / "DEBIAN" / "control").exists()
        assert (staging / "usr" / "bin" / "basexor").exists()
        control = (staging / "DEBIAN" / "control").read_text()
        assert "Package: basexor-probe" in control
        assert "Version: 0.0.1" in control


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestCLI:
    def test_cli_help(self):
        runner = CliRunner()
        result = runner.invoke(basexor, ["--help"])
        assert result.exit_code == 0
        assert "BaseXOR 探针" in result.output

    def test_ca_init(self, tmp_path):
        runner = CliRunner()
        ca_dir = tmp_path / "ca"
        result = runner.invoke(
            basexor,
            ["ca", "init", "--ca-dir", str(ca_dir), "--name", "CLI CA", "--key-size", "2048"],
        )
        assert result.exit_code == 0, result.output
        assert (ca_dir / "ca_cert.pem").exists()
        assert (ca_dir / "ca_key.pem").exists()
        assert (ca_dir / "credential.json").exists()
        cred = json.loads((ca_dir / "credential.json").read_text())
        assert "cert_pem" in cred
        assert "private_key_pem" in cred

    def test_block_sign_and_verify_round_trip(self, tmp_path):
        runner = CliRunner()
        ca_dir = tmp_path / "ca"
        runner.invoke(
            basexor,
            ["ca", "init", "--ca-dir", str(ca_dir), "--key-size", "2048"],
        )
        data_file = tmp_path / "block.bin"
        data_file.write_bytes(b"cli round trip data " * 4)
        manifest_file = tmp_path / "block.bx.json"
        sign_result = runner.invoke(
            basexor,
            [
                "block", "sign",
                "--ca-dir", str(ca_dir),
                "--data", str(data_file),
                "--block-id", "cli-1",
                "--seq", "1",
                "--out", str(manifest_file),
            ],
        )
        assert sign_result.exit_code == 0, sign_result.output
        envelope = json.loads(manifest_file.read_text())
        assert envelope["format"] == MANIFEST_FORMAT

        verify_result = runner.invoke(
            basexor,
            ["block", "verify", "--data", str(data_file), "--manifest", str(manifest_file)],
        )
        assert verify_result.exit_code == 0, verify_result.output
        assert "合规" in verify_result.output

    def test_block_verify_detects_tamper(self, tmp_path):
        runner = CliRunner()
        ca_dir = tmp_path / "ca"
        runner.invoke(
            basexor,
            ["ca", "init", "--ca-dir", str(ca_dir), "--key-size", "2048"],
        )
        data_file = tmp_path / "block.bin"
        data_file.write_bytes(b"original data " * 4)
        manifest_file = tmp_path / "block.bx.json"
        runner.invoke(
            basexor,
            [
                "block", "sign",
                "--ca-dir", str(ca_dir),
                "--data", str(data_file),
                "--block-id", "t-1",
                "--seq", "1",
                "--out", str(manifest_file),
            ],
        )
        # 篡改数据
        data_file.write_bytes(b"tampered data " * 4)
        result = runner.invoke(
            basexor,
            ["block", "verify", "--data", str(data_file), "--manifest", str(manifest_file)],
        )
        assert result.exit_code == 1
        assert "不合规" in result.output

    def test_matrix_json_output(self, tmp_path):
        runner = CliRunner()
        ca_dir = tmp_path / "ca"
        runner.invoke(
            basexor,
            ["ca", "init", "--ca-dir", str(ca_dir), "--key-size", "2048"],
        )
        manifests_dir = tmp_path / "manifests"
        manifests_dir.mkdir()
        for i in range(2):
            data_file = tmp_path / f"b{i}.bin"
            data_file.write_bytes(f"matrix data {i}".encode())
            runner.invoke(
                basexor,
                [
                    "block", "sign",
                    "--ca-dir", str(ca_dir),
                    "--data", str(data_file),
                    "--block-id", f"m-{i}",
                    "--seq", str(i),
                    "--out", str(manifests_dir / f"m-{i}.json"),
                ],
            )
        result = runner.invoke(
            basexor, ["matrix", "--manifests-dir", str(manifests_dir), "--json"]
        )
        assert result.exit_code == 0, result.output
        # 输出含 JSON 矩阵
        assert "overall_verdict" in result.output
        assert "compliant" in result.output

    def test_apt_line(self):
        runner = CliRunner()
        result = runner.invoke(basexor, ["apt", "line", "--install"])
        assert result.exit_code == 0
        assert "sources.list.d" in result.output or "basexor.list" in result.output
        assert "apt update" in result.output

    def test_apt_pack(self, tmp_path):
        runner = CliRunner()
        result = runner.invoke(
            basexor,
            [
                "apt", "pack",
                "--staging-dir", str(tmp_path / "stage"),
                "--output-dir", str(tmp_path / "out"),
                "--no-dpkg",
            ],
        )
        assert result.exit_code == 0, result.output
        assert (tmp_path / "stage" / "basexor-probe" / "DEBIAN" / "control").exists()

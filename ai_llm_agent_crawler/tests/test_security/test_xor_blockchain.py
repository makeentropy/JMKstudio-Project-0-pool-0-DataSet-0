"""security 扩展模块测试：噪音字典 / XOR 时钟 / 区块链编码容器。"""

from __future__ import annotations

import pytest

from ai_llm_agent_crawler.security import (
    BlockchainEncodingContainer,
    NoiseDictionary,
    XorClockCodec,
    XorClockPayload,
    build_noise_dictionary,
    merge_chains,
)


class TestNoiseDictionary:
    def test_keystream_deterministic(self) -> None:
        nd1 = NoiseDictionary(dimension="dim-1", clock_seed=42)
        nd2 = NoiseDictionary(dimension="dim-1", clock_seed=42)
        assert nd1.keystream(64) == nd2.keystream(64)

    def test_different_dimension_differs(self) -> None:
        a = NoiseDictionary(dimension="a", clock_seed=1).keystream(32)
        b = NoiseDictionary(dimension="b", clock_seed=1).keystream(32)
        assert a != b

    def test_fingerprint_stable(self) -> None:
        nd = NoiseDictionary(dimension="x", clock_seed=7)
        assert nd.fingerprint() == nd.fingerprint()
        assert len(nd.fingerprint()) == 64

    def test_invalid_dimension(self) -> None:
        with pytest.raises(ValueError):
            NoiseDictionary(dimension="", clock_seed=1)

    def test_negative_seed(self) -> None:
        with pytest.raises(ValueError):
            NoiseDictionary(dimension="x", clock_seed=-1)

    def test_zero_length(self) -> None:
        assert NoiseDictionary(dimension="x", clock_seed=1).keystream(0) == b""

    def test_build_helper(self) -> None:
        nd = build_noise_dictionary("d", 1)
        assert nd.dimension == "d"


class TestXorClockCodec:
    def test_encode_decode_roundtrip(self) -> None:
        codec = XorClockCodec()
        plain = "你好，trae！".encode("utf-8")
        payload = codec.encode(plain, "dim-1", 100)
        decoded = codec.decode(payload)
        assert decoded == plain

    def test_decode_verify_failure_on_tamper(self) -> None:
        codec = XorClockCodec()
        payload = codec.encode(b"secret", "dim", 1)
        tampered = XorClockPayload(
            dimension=payload.dimension,
            clock_seed=payload.clock_seed,
            ciphertext=b"X" + payload.ciphertext[1:],
            clock_check=payload.clock_check,
            fingerprint=payload.fingerprint,
        )
        with pytest.raises(ValueError, match="校验失败"):
            codec.decode(tampered, verify=True)

    def test_decode_without_verify(self) -> None:
        codec = XorClockCodec()
        payload = codec.encode(b"abc", "d", 1)
        # 不校验也能解码（密钥流一致）
        assert codec.decode(payload, verify=False) == b"abc"

    def test_bytes_roundtrip(self) -> None:
        codec = XorClockCodec()
        payload = codec.encode(b"data", "dim", 5)
        wire = payload.to_bytes()
        restored = XorClockPayload.from_bytes(wire)
        assert restored.ciphertext == payload.ciphertext
        assert restored.dimension == "dim"
        assert restored.clock_seed == 5

    def test_encode_requires_bytes(self) -> None:
        with pytest.raises(TypeError):
            XorClockCodec().encode("not-bytes", "d", 1)  # type: ignore[arg-type]

    def test_wrong_dimension_decode_differs(self) -> None:
        codec = XorClockCodec()
        payload = codec.encode(b"abc", "dim-a", 1)
        wrong = XorClockPayload(
            dimension="dim-b",
            clock_seed=payload.clock_seed,
            ciphertext=payload.ciphertext,
            clock_check=codec._clock_check("dim-b", payload.clock_seed, payload.ciphertext),
            fingerprint=payload.fingerprint,
        )
        assert codec.decode(wrong, verify=False) != b"abc"


class TestBlockchainEncoding:
    def test_genesis_and_append(self) -> None:
        chain = BlockchainEncodingContainer()
        assert len(chain.records) == 1  # genesis
        chain.append("CA-1", "dim", 1, b"cipher")
        assert len(chain.records) == 2
        assert chain.verify_chain() is True

    def test_mine_wallet(self) -> None:
        chain = BlockchainEncodingContainer()
        rec = chain.mine_wallet(
            dictionary_entry="entry",
            ca_serial="CA-1",
            dimension="dim",
            clock_seed=1,
            ciphertext=b"abc",
            difficulty=1,
        )
        assert rec.nonce >= 0
        assert rec.extra["mine_hash"].startswith("0")
        assert chain.verify_chain() is True

    def test_verify_detects_tamper(self) -> None:
        chain = BlockchainEncodingContainer()
        chain.append("CA-1", "dim", 1, b"abc")
        chain.records[1].ciphertext = b"tampered"
        # hash 未重算，应校验失败
        assert chain.verify_chain() is False

    def test_find_by_ca_and_dimension(self) -> None:
        chain = BlockchainEncodingContainer()
        chain.append("CA-1", "dim-a", 1, b"a")
        chain.append("CA-2", "dim-b", 2, b"b")
        assert len(chain.find_by_ca("CA-1")) == 1
        assert len(chain.find_by_dimension("dim-b")) == 1

    def test_merge_chains(self) -> None:
        c1 = BlockchainEncodingContainer()
        c2 = BlockchainEncodingContainer()
        c1.append("CA-1", "dim", 1, b"a")
        c2.append("CA-2", "dim", 2, b"b")
        merged = merge_chains(c1, c2)
        # 两条各 1 条记录 + genesis(1) = 3
        assert len(merged.records) == 3
        assert merged.verify_chain() is True

    def test_to_dict(self) -> None:
        chain = BlockchainEncodingContainer()
        chain.append("CA-1", "dim", 1, b"abc")
        d = chain.to_dict()
        assert d["length"] == 2
        assert d["records"][1]["ca_serial"] == "CA-1"

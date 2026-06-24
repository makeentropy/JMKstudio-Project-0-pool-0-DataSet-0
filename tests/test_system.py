"""
Tests for the quantum steganographic memory execution system.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest


class TestCrypto:
    def test_ca_and_certificates(self):
        from src.utils import CA
        ca = CA("TEST_CA")
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend
        pk = rsa.generate_private_key(65537, 2048, default_backend())
        cert = ca.issue_certificate("test_subject", pk.public_key())
        assert ca.verify_certificate(cert) is True

    def test_hash_data(self):
        from src.utils import hash_data
        h = hash_data(b"hello")
        assert len(h) == 64

    def test_generate_id(self):
        from src.utils import generate_id
        id1 = generate_id("test")
        id2 = generate_id("test")
        assert id1 != id2
        assert id1.startswith("test_")


class TestLogicLogger:
    def test_genesis_block(self):
        from src.utils import LogicLogger
        logger = LogicLogger("test")
        assert logger.chain_length == 1
        assert logger.verify_chain() is True

    def test_log_entry(self):
        from src.utils import LogicLogger
        logger = LogicLogger("test")
        entry = logger.log("test_mod", "test_action", key="value")
        assert logger.chain_length == 2
        assert entry.module == "test_mod"
        assert entry.action == "test_action"
        assert entry.payload["key"] == "value"
        assert logger.verify_chain() is True

    def test_chain_integrity(self):
        from src.utils import LogicLogger
        logger = LogicLogger("test")
        for i in range(10):
            logger.log("mod", f"action_{i}", n=i)
        assert logger.chain_length == 11
        assert logger.verify_chain() is True


class TestSteganography:
    def test_medium_bytes(self):
        from src.steganography import StegoMedium, MediumType
        data = bytearray(b"\x00\x01\x02\x03")
        medium = StegoMedium(data, MediumType.BYTES)
        assert len(medium) == 4
        medium.set_lsb(0, 1)
        assert medium.get_lsb(0) == 1

    def test_encode_decode(self):
        from src.steganography import StegoEncoder, StegoDecoder, StegoMedium, MediumType
        carrier = bytearray([0] * 1024)
        medium = StegoMedium(carrier, MediumType.BYTES)
        encoder = StegoEncoder(medium)
        data = b"secret message 12345"
        med, anchor = encoder.encode(data, tag="test")
        decoder = StegoDecoder(med)
        result = decoder.extract_by_anchor(anchor)
        assert result == data

    def test_ca_stego_verification(self):
        from src.utils import CA
        from src.steganography import StegoEncoder, StegoDecoder, StegoMedium, MediumType, CAStegoVerifier
        ca = CA("TEST_CA")
        from cryptography.hazmat.primitives.asymmetric import rsa
        from cryptography.hazmat.backends import default_backend
        pk = rsa.generate_private_key(65537, 2048, default_backend())
        cert = ca.issue_certificate("test_probe", pk.public_key())

        verifier = CAStegoVerifier(ca, cert, pk)
        carrier = bytearray([0] * 1024)
        medium = StegoMedium(carrier, MediumType.BYTES)
        encoder = StegoEncoder(medium)
        data = b"verified data"
        med, anchor = verifier.encode_verified(encoder, data, tag="signed")
        assert anchor.signature is not None

        decoder = StegoDecoder(med)
        result = verifier.decode_verified(decoder, anchor)
        assert result == data


class TestMemoryMatrix:
    def test_write_and_read(self):
        from src.memory_matrix import SingularityMatrix
        matrix = SingularityMatrix("test")
        cell = matrix.write("anchor1", b"hello world", source="test", tag="demo")
        assert cell.anchor == "anchor1"
        assert matrix.size == 1
        result = matrix.read("anchor1")
        assert len(result) == 1
        assert result[0].data == b"hello world"

    def test_query(self):
        from src.memory_matrix import SingularityMatrix
        matrix = SingularityMatrix("test")
        for i in range(10):
            matrix.write(f"a{i%3}", f"data_{i}".encode(),
                         source=f"s{i%2}", tag=f"t{i%4}", priority=i)
        cells = matrix.query(tag="t0")
        assert len(cells) == 3
        cells = matrix.query(source="s0")
        assert len(cells) == 5

    def test_memory_pool_and_spaces(self):
        from src.memory_matrix import MemoryPool
        pool = MemoryPool("test_pool")
        assert pool.space_count == 0
        space = pool.create_space("dim1")
        assert pool.space_count == 1
        pool.matrix.write("test", b"test_data", tag="t1")
        ds = space.create_dataset("ds1", dimension="dim", tag_filter="t1")
        assert ds.size >= 1


class TestBaseNode:
    def test_node_lifecycle(self):
        from src.utils import CA
        from src.base_node import BaseNode
        ca = CA("TEST")
        node = BaseNode("test_node", ca)
        assert node.state.value == "created"
        assert node.initialize() is True
        assert node.state.value == "running"
        node.pause()
        assert node.state.value == "paused"
        node.resume()
        assert node.state.value == "running"
        node.terminate()
        assert node.state.value == "terminated"

    def test_node_tags(self):
        from src.utils import CA
        from src.base_node import BaseNode
        ca = CA("TEST")
        node = BaseNode("test", ca)
        node.add_tag("alpha")
        node.add_tag("beta")
        assert node.has_tag("alpha")
        assert "alpha" in node.tags
        node.remove_tag("alpha")
        assert not node.has_tag("alpha")

    def test_process_manager(self):
        from src.utils import CA
        from src.base_node import ProcessManager
        ca = CA("TEST")
        pm = ProcessManager(ca)
        proc = pm.spawn("test_proc")
        assert proc is not None
        assert pm.count == 1
        assert proc.state.value == "active"
        pm.kill(proc.pid)
        assert proc.state.value == "zombie"
        pm.reap()
        assert pm.count == 0


class TestProbe:
    def test_probe_encode_decode(self):
        from src.utils import CA
        from src.probe import Probe
        ca = CA("TEST")
        probe = Probe("test_probe", ca)
        data = b"hello stego probe"
        medium, anchor = probe.encode_to_medium(data, tag="test")
        assert anchor.payload_hash is not None
        decoded = probe.decode_from_medium(medium, anchor)
        assert decoded == data

    def test_probe_with_matrix(self):
        from src.utils import CA
        from src.probe import Probe
        from src.memory_matrix import SingularityMatrix
        ca = CA("TEST")
        matrix = SingularityMatrix("test")
        probe = Probe("test_probe", ca, matrix=matrix)
        data = b"matrix test"
        medium, anchor = probe.encode_to_medium(data, tag="matrixtest")
        probe.decode_from_medium(medium, anchor)
        assert matrix.size >= 1


class TestAIAgent:
    def test_agent_creation(self):
        from src.utils import CA
        from src.ai_agent import StegoAgent
        ca = CA("TEST")
        agent = StegoAgent("test_agent", ca)
        assert agent.state.value == "dormant"
        assert agent.self_model.identity == "test_agent"

    def test_okr(self):
        from src.ai_agent import OKR
        okr = OKR("test")
        obj = okr.create_objective("Test objective")
        kr = okr.add_key_result(obj.obj_id, "Test KR", target_value=10.0)
        assert kr is not None
        okr.update_key_result(kr.kr_id, value=5.0)
        assert kr.progress == 0.5
        assert obj.progress == 0.5
        assert okr.overall_progress == 0.5


class TestDataScience:
    def test_file_manager(self):
        from src.data_science import FileManager
        fm = FileManager(os.path.join(os.path.dirname(__file__), "..", "src"))
        fm.scan_directory()
        assert fm.count > 0

    def test_data_order(self):
        from src.data_science import DataOrder
        from src.data_science.data_order import SortAlgorithm
        do = DataOrder()
        items = [{"name": "c", "val": 3}, {"name": "a", "val": 1}, {"name": "b", "val": 2}]
        do.create_rule("by_val", "val")
        result = do.apply_order(items, algorithm=SortAlgorithm.QUICK)
        assert len(result.sorted_items) == 3
        assert result.sorted_items[0]["val"] == 1
        assert result.comparisons > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

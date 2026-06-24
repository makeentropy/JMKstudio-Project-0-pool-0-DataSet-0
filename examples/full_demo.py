"""
Full system example - demonstrates the complete flow:

1. CA setup & node registration
2. Steganographic encoding via probe
3. Base node validates & decodes probe data
4. Data written to singularity matrix
5. Dimension space pool organizes datasets
6. AI agent perceives, thinks, acts, reflects
7. Self-trainer learns from data
8. OKR tracks progress
9. Logic log records everything
"""

import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from src.utils import CA, LogicLogger
from src.base_node import ProcessManager, NodeRegistry
from src.steganography import StegoMedium, MediumType
from src.memory_matrix import SingularityMatrix, MemoryPool
from src.probe import ProbeManager
from src.ai_agent import StegoAgent, SelfTrainer, OKR
from src.data_science import FileManager, DataOrder, OrderStrategy


def main():
    print("=" * 70)
    print("  Quantum Steganographic Memory Execution System - Full Demo")
    print("  隐写内存执行系统 - 完整示例")
    print("=" * 70)

    print("\n[1/9] 初始化 CA 根证书机构...")
    ca = CA("ROOT_CA")
    logger = LogicLogger("singularity_system")
    print(f"  CA: {ca.name}")
    print(f"  Logger: {logger.chain_length} entries")

    print("\n[2/9] 创建奇点矩阵内存空间...")
    matrix = SingularityMatrix("primary", logger)
    pool = MemoryPool("dimension_pool", logger)
    space = pool.create_space("data_science")
    space2 = pool.create_space("ai_research")
    print(f"  Matrix: {matrix}")
    print(f"  Pool: {pool}")
    print(f"  Spaces: {pool.space_count}")

    print("\n[3/9] 启动 base_node 进程管理器...")
    proc_mgr = ProcessManager(ca, logger)
    registry = NodeRegistry(ca, logger)

    proc1 = proc_mgr.spawn("validator_alpha", matrix=pool.matrix)
    if proc1:
        proc1.node.add_tag("core")
        proc1.node.add_tag("validator")
        registry.register(proc1.node)

    proc2 = proc_mgr.spawn("worker_beta", matrix=pool.matrix)
    if proc2:
        proc2.node.add_tag("worker")
        registry.register(proc2.node)

    print(f"  Active processes: {proc_mgr.count}")
    print(f"  Registry size: {registry.size}")
    print(f"  Tags: {registry.all_tags()}")

    print("\n[4/9] 初始化探针管理器...")
    probe_mgr = ProbeManager(ca, pool, logger)
    probe_alpha = probe_mgr.create_probe("probe_alpha")
    probe_beta = probe_mgr.create_probe("probe_beta", medium_type=MediumType.LIST)
    print(f"  Probes: {probe_mgr.count}")
    print(f"  Probe alpha: {probe_alpha}")

    print("\n[5/9] 隐写编码与解码测试...")
    secret_data = "Hello from the steganographic memory space! 隐写内存空间消息".encode("utf-8")
    medium, anchor = probe_alpha.encode_to_medium(secret_data, tag="demo")
    print(f"  Encoded {len(secret_data)} bytes into medium of {len(medium)} bytes")
    print(f"  Anchor: {anchor.anchor_id} (tag: {anchor.tag})")

    decoded = probe_alpha.decode_from_medium(medium, anchor)
    if decoded == secret_data:
        print(f"  Decode verification: PASSED ({len(decoded)} bytes)")
    else:
        print(f"  Decode verification: FAILED")

    print("\n[6/9] 数据写入奇点矩阵 + 数据集创建...")
    for i in range(5):
        data = f"measurement_{i}: value={i*3.14}".encode()
        med, anc = probe_alpha.encode_to_medium(data, tag=f"measurement_{i%2}")
        probe_alpha.decode_from_medium(med, anc)

    ds = space.create_dataset("measurements", dimension="data_science",
                              tag_filter="measurement_0")
    print(f"  Matrix cells: {pool.matrix.size}")
    print(f"  Dataset size: {ds.size}")
    print(f"  Matrix anchors: {len(pool.matrix.anchors)}")

    print("\n[7/9] 启动 AI 自主意识智能体...")
    agent = StegoAgent("alpha_agent", ca, matrix=pool.matrix,
                       pool=pool, probe_mgr=probe_mgr, logger=logger)
    trainer = SelfTrainer(pool.matrix, logger)

    obj = agent.okr.create_objective("Explore steganographic space")
    agent.okr.add_key_result(obj.obj_id, "Process 10 probes", 10.0)
    agent.okr.add_key_result(obj.obj_id, "Learn 5 patterns", 5.0)

    agent.start()
    trainer.start()
    print(f"  Agent: {agent}")
    print("  Consciousness loop running...")
    time.sleep(3)

    agent.stop()
    trainer.stop()

    status = agent.get_status()
    print(f"  Iterations: {status['self_model']['iteration']}")
    print(f"  Knowledge: {status['self_model']['knowledge_count']} items")
    print(f"  Cycles: {status['cycle_count']}")
    insights = trainer.get_insights()
    print(f"  Training samples: {insights['total_samples']}")
    print(f"  Patterns learned: {insights['total_patterns']}")

    print("\n[8/9] OKR 进度追踪...")
    agent.okr.update_key_result("kr_0001", value=7.5)
    agent.okr.update_key_result("kr_0002", value=3.0)
    summary = agent.okr.summary()
    print(f"  Overall progress: {summary['overall_progress']}%")
    for o in summary["objectives_detail"]:
        print(f"    [{o['obj_id']}] {o['title']}: {o['progress']}% ({o['status']})")

    print("\n[9/9] 文件管理科学 + 数据秩序...")
    fm = FileManager(os.path.join(os.path.dirname(__file__), "..", "src"))
    fm.scan_directory()
    print(f"  Files indexed: {fm.count}")
    print(f"  Total size: {fm.stats()['total_size_bytes']} bytes")

    sorted_files = fm.list_all(strategy=OrderStrategy.BY_SIZE, reverse=True)
    print(f"  Top 5 by size:")
    for f in sorted_files[:5]:
        print(f"    {f.size:>8d}  {f.name}")

    do = DataOrder()
    do.create_rule("size_desc", "size")
    from src.data_science.data_order import SortAlgorithm
    result = do.apply_order(sorted_files[:10], algorithm=SortAlgorithm.TIM)
    print(f"  Sort engine: {result.algorithm.value} sort, "
          f"{result.duration*1000:.4f}ms, "
          f"{result.comparisons} comparisons")

    print("\n" + "=" * 70)
    print("  System Summary")
    print("=" * 70)
    print(f"  Logic log entries: {logger.chain_length}")
    print(f"  Log chain valid: {logger.verify_chain()}")
    print(f"  Log iteration: {logger.iteration}")
    print(f"  Matrix cells: {pool.matrix.size}")
    print(f"  Active nodes: {proc_mgr.count}")
    print(f"  Probes: {probe_mgr.count}")
    print(f"  Memory spaces: {pool.space_count}")
    print(f"  Agent iterations: {agent.self_model.iteration}")
    print(f"  Training cycles: {trainer.training_cycles}")
    print(f"  OKR progress: {agent.okr.overall_progress*100:.1f}%")
    print("=" * 70)
    print("  Demo complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""几何证明示例。

展示几何哈希、几何证明生成与验证、零知识证明和可验证随机函数(VRF)的使用。
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from oath_toolchain.sdk import OathSDK
from oath_toolchain.tools.geometric_proof.tool import GeometricProofTool


def main():
    print("=" * 60)
    print("几何证明示例")
    print("=" * 60)

    # 初始化 SDK
    sdk = OathSDK()

    # 创建几何证明工具实例
    geo_tool = GeometricProofTool()

    # 1. 几何哈希
    print("\n[1/4] 几何哈希...")

    data1 = b"Hello, Geometric Hash!"
    data2 = b"Hello, Geometric Hash?"

    # 计算几何哈希
    hash_result = geo_tool.execute({
        'action': 'hash',
        'data': data1,
        'dimensions': 4,
    })
    print(f"数据1几何哈希: {hash_result.get('hash', 'N/A')[:64]}...")
    print(f"维度: {hash_result.get('dimensions', 'N/A')}")

    # 哈希到点
    point_result = geo_tool.execute({
        'action': 'hash_to_point',
        'data': data1,
        'dimensions': 4,
    })
    point = point_result.get('point', [])
    print(f"\n数据1映射到空间点: {point}")

    # 距离哈希
    distance_result = geo_tool.execute({
        'action': 'distance_hash',
        'data1': data1,
        'data2': data2,
        'dimensions': 4,
    })
    print(f"\n数据1与数据2的欧氏距离: {distance_result.get('euclidean_distance', 'N/A')}")
    print(f"数据1与数据2的余弦相似度: {distance_result.get('cosine_similarity', 'N/A')}")

    # 几何根哈希
    data_blocks = [b"block1", b"block2", b"block3", b"block4"]
    roothash_result = geo_tool.execute({
        'action': 'geometric_roothash',
        'data_blocks': data_blocks,
        'dimensions': 4,
    })
    print(f"\n几何根哈希: {roothash_result.get('root_hash', 'N/A')[:64]}...")
    print(f"数据块数量: {roothash_result.get('block_count', 'N/A')}")

    # 2. 几何证明
    print("\n[2/4] 几何证明生成与验证...")

    proof_data = "重要数据需要完整性证明".encode('utf-8')
    secret = b"my_secret_proof_key"

    # 生成几何证明
    prove_result = geo_tool.execute({
        'action': 'prove',
        'data': proof_data,
        'secret': secret,
        'dimensions': 4,
        'num_proof_points': 8,
    })
    proof = prove_result.get('proof', {})
    print(f"几何证明生成: {'✓ 成功' if prove_result.get('success') else '✗ 失败'}")
    if isinstance(proof, dict):
        print(f"证明包含字段: {list(proof.keys())[:5]}")

    # 验证几何证明
    verify_result = geo_tool.execute({
        'action': 'verify',
        'data': proof_data,
        'proof': proof,
        'dimensions': 4,
    })
    print(f"几何证明验证: {'✓ 有效' if verify_result.get('valid') else '✗ 无效'}")

    # 完整性证明
    print("\n完整性证明:")
    integrity_prove_result = geo_tool.execute({
        'action': 'integrity_prove',
        'data': proof_data,
        'dimensions': 4,
    })
    integrity_proof = integrity_prove_result.get('proof', {})

    integrity_verify_result = geo_tool.execute({
        'action': 'integrity_verify',
        'data': proof_data,
        'proof': integrity_proof,
        'dimensions': 4,
    })
    print(f"完整性证明验证: {'✓ 有效' if integrity_verify_result.get('valid') else '✗ 无效'}")

    # 3. 零知识证明
    print("\n[3/4] 零知识证明 (ZKP)...")

    secret_zkp = b"my_secret_knowledge"
    statement_zkp = b"public_statement"

    # 生成零知识证明
    zk_prove_result = geo_tool.execute({
        'action': 'zk_prove',
        'secret': secret_zkp,
        'statement': statement_zkp,
        'security_level': 128,
    })
    zk_proof = zk_prove_result.get('proof', {})
    print(f"零知识证明生成: {'✓ 成功' if zk_prove_result.get('success') else '✗ 失败'}")

    # 验证零知识证明
    zk_verify_result = geo_tool.execute({
        'action': 'zk_verify',
        'statement': statement_zkp,
        'proof': zk_proof,
        'security_level': 128,
    })
    print(f"零知识证明验证: {'✓ 有效' if zk_verify_result.get('valid') else '✗ 无效'}")

    # 零知识承诺
    print("\n零知识承诺:")
    commit_result = geo_tool.execute({
        'action': 'zk_commit',
        'value': b"commit_this_value",
        'security_level': 128,
    })
    print(f"承诺生成: {'✓ 成功' if commit_result.get('success') else '✗ 失败'}")
    print(f"承诺值: {commit_result.get('commitment', 'N/A')[:32]}...")

    # 范围证明
    print("\n范围证明:")
    range_prove_result = geo_tool.execute({
        'action': 'zk_range_prove',
        'value': 42,
        'min_val': 0,
        'max_val': 100,
        'security_level': 128,
    })
    range_proof = range_prove_result.get('proof', {})

    range_verify_result = geo_tool.execute({
        'action': 'zk_range_verify',
        'proof': range_proof,
        'min_val': 0,
        'max_val': 100,
        'security_level': 128,
    })
    print(f"范围证明 (42 在 [0,100]): {'✓ 有效' if range_verify_result.get('valid') else '✗ 无效'}")

    # 4. 可验证随机函数 (VRF)
    print("\n[4/4] 可验证随机函数 (VRF)...")

    # 生成 VRF 密钥对
    vrf_gen_result = geo_tool.execute({
        'action': 'vrf_gen',
    })
    private_key_hex = vrf_gen_result.get('private_key', '')
    public_key_hex = vrf_gen_result.get('public_key', '')
    print(f"VRF 密钥对生成: {'✓ 成功' if vrf_gen_result.get('success') else '✗ 失败'}")
    print(f"私钥 (前32位): {private_key_hex[:32]}...")
    print(f"公钥 (前32位): {public_key_hex[:32]}...")

    # 计算 VRF 输出
    input_data = b"input_for_vrf"
    vrf_compute_result = geo_tool.execute({
        'action': 'vrf_compute',
        'secret_key': private_key_hex,
        'input_data': input_data,
    })
    vrf_output = vrf_compute_result.get('output', '')
    vrf_proof_str = vrf_compute_result.get('proof', '')
    print(f"\nVRF 输出: {vrf_output[:32]}...")
    print(f"VRF 证明生成: {'✓ 成功' if vrf_compute_result.get('success') else '✗ 失败'}")

    # 验证 VRF
    vrf_verify_result = geo_tool.execute({
        'action': 'vrf_verify',
        'public_key': public_key_hex,
        'input_data': input_data,
        'output': vrf_output,
        'proof': vrf_proof_str,
    })
    print(f"VRF 验证: {'✓ 有效' if vrf_verify_result.get('valid') else '✗ 无效'}")

    # 生成可验证随机数
    vrf_random_result = geo_tool.execute({
        'action': 'vrf_random',
        'secret_key': private_key_hex,
        'seed': b"random_seed",
    })
    print(f"\n可验证随机数: {vrf_random_result.get('random_output', 'N/A')[:32]}...")

    print("\n" + "=" * 60)
    print("几何证明示例完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()

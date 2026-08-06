"""
安全加密模块

提供数据加密、解密、哈希计算、认证、压缩和访问控制功能。
"""

# 基础加密模块
from ai_llm_agent_crawler.security.encryption import AESCipher, Encryptor
from ai_llm_agent_crawler.security.hashing import HashCalculator

# GPG加密模块
from ai_llm_agent_crawler.security.gpg_encryption import (
    EncryptionMode,
    EncryptedData,
    GPGKey,
    GPGKeyManager,
    GPGDictionaryEncryptor,
    SecureDictionaryStorage,
)

# CA认证系统
from ai_llm_agent_crawler.security.ca_system import (
    CertificateStatus,
    CertificateType,
    CertificateInfo,
    CertificateRevocationList,
    CertificateAuthority,
    CertificateStore,
    CertificateVerifier,
)

# Datachain压缩算法
from ai_llm_agent_crawler.security.datachain_compression import (
    CompressionAlgorithm,
    CompressionLevel,
    CompressionMetadata,
    DataBlock,
    CompressedDataBlock,
    DataChainHeader,
    BaseCompressor,
    ZlibCompressor,
    GzipCompressor,
    LZMACompressor,
    BZ2Compressor,
    ZstdCompressor,
    DeltaCompressor,
    RLECompressor,
    DataChainCompressor,
    AdaptiveCompressor,
)

# 访问控制和权限管理
from ai_llm_agent_crawler.security.access_control import (
    Permission,
    ResourceType,
    AccessDecision,
    User,
    Role,
    Resource,
    AccessPolicy,
    Session,
    UserManager,
    RoleManager,
    ResourceManager,
    AccessController,
)

# 数据保全与安全校验链（O3：Merkle + GPG CA + baseXOR-Prober + HashChain）
from ai_llm_agent_crawler.security.integrity_chain import (
    HashAlgo,
    hash_bytes,
    hash_file,
    MerkleNode,
    MerkleProof,
    MerkleTree,
    MerkleDAGNode,
    MerkleDAGBuilder,
    SnapshotSignature,
    SnapshotSigner,
    AnchorValidationResult,
    AnchorRecord,
    ProbeReport,
    BaseXORProber,
    DistributedProber,
    ChainEntry,
    ChainConsensus,
    HashChainLedger,
)

__all__ = [
    # 基础加密
    "AESCipher",
    "Encryptor",
    "HashCalculator",
    # GPG加密
    "EncryptionMode",
    "EncryptedData",
    "GPGKey",
    "GPGKeyManager",
    "GPGDictionaryEncryptor",
    "SecureDictionaryStorage",
    # CA认证系统
    "CertificateStatus",
    "CertificateType",
    "CertificateInfo",
    "CertificateRevocationList",
    "CertificateAuthority",
    "CertificateStore",
    "CertificateVerifier",
    # Datachain压缩
    "CompressionAlgorithm",
    "CompressionLevel",
    "CompressionMetadata",
    "DataBlock",
    "CompressedDataBlock",
    "DataChainHeader",
    "BaseCompressor",
    "ZlibCompressor",
    "GzipCompressor",
    "LZMACompressor",
    "BZ2Compressor",
    "ZstdCompressor",
    "DeltaCompressor",
    "RLECompressor",
    "DataChainCompressor",
    "AdaptiveCompressor",
    # 访问控制
    "Permission",
    "ResourceType",
    "AccessDecision",
    "User",
    "Role",
    "Resource",
    "AccessPolicy",
    "Session",
    "UserManager",
    "RoleManager",
    "ResourceManager",
    "AccessController",
    # 数据保全与安全校验链（O3）
    "HashAlgo",
    "hash_bytes",
    "hash_file",
    "MerkleNode",
    "MerkleProof",
    "MerkleTree",
    "MerkleDAGNode",
    "MerkleDAGBuilder",
    "SnapshotSignature",
    "SnapshotSigner",
    "AnchorValidationResult",
    "AnchorRecord",
    "ProbeReport",
    "BaseXORProber",
    "DistributedProber",
    "ChainEntry",
    "ChainConsensus",
    "HashChainLedger",
]
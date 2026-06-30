"""神誓工具链核心模块。

包含工具基类、注册中心、配置管理、异常体系、日志工具、
数学运算、密码学原语和数据结构等核心功能。
"""

from .base import OathTool
from .registry import ToolRegistry, register_tool
from .config import ConfigManager, ConfigSchema
from .exceptions import (
    OathToolchainError,
    ToolNotFoundError,
    ConfigError,
    EncryptionError,
    ValidationError,
    AuthenticationError,
)
from .logging_util import get_logger, setup_logging, set_level
from .math import (
    Vector,
    zeros,
    ones,
    random_vector,
    SpacePoint,
    HyperPlane,
    SpaceHash,
    midpoint,
    scale_point,
    translate_point,
    point_on_side,
)
from .crypto import (
    AESCipher,
    RSACipher,
    ECCipher,
    Hash,
    KDF,
    SecureRandom,
    get_random_bytes,
    get_random_int,
    get_random_string,
    generate_salt,
)
from .data_structures import (
    MerkleTree,
    HashChain,
)

__all__ = [
    "OathTool",
    "ToolRegistry",
    "register_tool",
    "ConfigManager",
    "ConfigSchema",
    "OathToolchainError",
    "ToolNotFoundError",
    "ConfigError",
    "EncryptionError",
    "ValidationError",
    "AuthenticationError",
    "get_logger",
    "setup_logging",
    "set_level",
    "Vector",
    "zeros",
    "ones",
    "random_vector",
    "SpacePoint",
    "HyperPlane",
    "SpaceHash",
    "midpoint",
    "scale_point",
    "translate_point",
    "point_on_side",
    "AESCipher",
    "RSACipher",
    "ECCipher",
    "Hash",
    "KDF",
    "SecureRandom",
    "get_random_bytes",
    "get_random_int",
    "get_random_string",
    "generate_salt",
    "MerkleTree",
    "HashChain",
]

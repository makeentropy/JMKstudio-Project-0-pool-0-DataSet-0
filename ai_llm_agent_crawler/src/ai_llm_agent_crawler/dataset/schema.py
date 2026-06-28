"""
数据集生成流程和数据格式标准模块

定义数据集的数据模型、格式标准和转换流程。
支持JSON、Parquet、CSV等机器学习训练格式。
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, field_validator, model_validator


class DatasetFormat(str, Enum):
    """数据集格式枚举"""

    JSON = "json"
    PARQUET = "parquet"
    CSV = "csv"
    EXCEL = "excel"
    HDF5 = "hdf5"
    ARROW = "arrow"


class DatasetType(str, Enum):
    """数据集类型枚举"""

    TRAINING = "training"  # 训练集
    VALIDATION = "validation"  # 验证集
    TEST = "test"  # 测试集
    INFERENCE = "inference"  # 推理集


class DataQuality(str, Enum):
    """数据质量等级"""

    HIGH = "high"  # 高质量 - 经过多重验证
    MEDIUM = "medium"  # 中等质量 - 基本验证通过
    LOW = "low"  # 低质量 - 待清洗
    RAW = "raw"  # 原始数据 - 未处理


class AnnotationMethod(str, Enum):
    """标注方法枚举"""

    MANUAL = "manual"  # 人工标注
    RULE_BASED = "rule_based"  # 规则标注
    MODEL_BASED = "model_based"  # 模型标注
    SEMI_AUTO = "semi_auto"  # 半自动标注
    CROWD_SOURCE = "crowd_source"  # 众包标注


class DataType(str, Enum):
    """数据类型枚举"""

    TEXT = "text"  # 文本数据
    IMAGE = "image"  # 图像数据
    AUDIO = "audio"  # 音频数据
    VIDEO = "video"  # 视频数据
    TABULAR = "tabular"  # 表格数据
    MULTIMODAL = "multimodal"  # 多模态数据
    TIME_SERIES = "time_series"  # 时间序列数据


class FieldSchema(BaseModel):
    """字段模式定义"""

    name: str = Field(..., description="字段名称")
    data_type: str = Field(..., description="数据类型")
    nullable: bool = Field(default=True, description="是否允许为空")
    description: str = Field(default="", description="字段描述")
    default: Optional[Any] = Field(default=None, description="默认值")
    constraints: Dict[str, Any] = Field(default_factory=dict, description="字段约束")

    # 验证相关
    min_value: Optional[Union[int, float]] = Field(default=None, description="最小值")
    max_value: Optional[Union[int, float]] = Field(default=None, description="最大值")
    min_length: Optional[int] = Field(default=None, description="最小长度")
    max_length: Optional[int] = Field(default=None, description="最大长度")
    pattern: Optional[str] = Field(default=None, description="正则表达式模式")
    enum_values: Optional[List[Any]] = Field(default=None, description="枚举值列表")


class LabelSchema(BaseModel):
    """标签模式定义"""

    name: str = Field(..., description="标签名称")
    label_type: str = Field(..., description="标签类型: classification, regression, sequence, etc.")
    classes: Optional[List[str]] = Field(default=None, description="类别列表（分类任务）")
    description: str = Field(default="", description="标签描述")
    annotation_method: AnnotationMethod = Field(
        default=AnnotationMethod.MANUAL, description="标注方法"
    )
    confidence_threshold: float = Field(
        default=0.8, ge=0.0, le=1.0, description="置信度阈值"
    )


class DatasetSchema(BaseModel):
    """数据集模式定义"""

    name: str = Field(..., description="数据集名称")
    version: str = Field(default="1.0.0", description="数据集版本")
    description: str = Field(default="", description="数据集描述")
    dataset_type: DatasetType = Field(default=DatasetType.TRAINING, description="数据集类型")
    data_type: DataType = Field(default=DataType.TEXT, description="数据类型")
    quality: DataQuality = Field(default=DataQuality.RAW, description="数据质量等级")

    # 字段定义
    fields: List[FieldSchema] = Field(default_factory=list, description="字段模式列表")
    labels: List[LabelSchema] = Field(default_factory=list, description="标签模式列表")

    # 元数据
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    created_by: str = Field(default="system", description="创建者")
    tags: List[str] = Field(default_factory=list, description="标签")

    # 统计信息
    total_records: int = Field(default=0, description="总记录数")
    valid_records: int = Field(default=0, description="有效记录数")
    invalid_records: int = Field(default=0, description="无效记录数")

    # 格式配置
    format: DatasetFormat = Field(default=DatasetFormat.PARQUET, description="数据集格式")
    compression: str = Field(default="snappy", description="压缩算法")

    # 来源信息
    source: str = Field(default="", description="数据来源")
    source_version: str = Field(default="", description="数据源版本")

    class Config:
        use_enum_values = True

    @model_validator(mode="after")
    def update_timestamp(self) -> "DatasetSchema":
        """更新时间戳"""
        self.updated_at = datetime.now()
        return self

    def get_field_names(self) -> List[str]:
        """获取所有字段名"""
        return [field.name for field in self.fields]

    def get_label_names(self) -> List[str]:
        """获取所有标签名"""
        return [label.name for label in self.labels]

    def validate_record(self, record: Dict[str, Any]) -> tuple[bool, List[str]]:
        """
        验证单条记录

        Args:
            record: 要验证的记录

        Returns:
            (是否有效, 错误消息列表)
        """
        errors = []

        for field in self.fields:
            value = record.get(field.name)
            field_errors = self._validate_field(field, value)
            errors.extend(field_errors)

        return len(errors) == 0, errors

    def _validate_field(self, field: FieldSchema, value: Any) -> List[str]:
        """验证单个字段"""
        errors = []

        # 检查是否为空
        if value is None:
            if not field.nullable:
                errors.append(f"字段 '{field.name}' 不能为空")
            return errors

        # 检查类型
        if not self._check_type(value, field.data_type):
            errors.append(
                f"字段 '{field.name}' 类型错误，期望 {field.data_type}，实际 {type(value).__name__}"
            )
            return errors

        # 检查最小值
        if field.min_value is not None and isinstance(value, (int, float)):
            if value < field.min_value:
                errors.append(
                    f"字段 '{field.name}' 值 {value} 小于最小值 {field.min_value}"
                )

        # 检查最大值
        if field.max_value is not None and isinstance(value, (int, float)):
            if value > field.max_value:
                errors.append(
                    f"字段 '{field.name}' 值 {value} 大于最大值 {field.max_value}"
                )

        # 检查最小长度
        if field.min_length is not None and hasattr(value, "__len__"):
            if len(value) < field.min_length:
                errors.append(
                    f"字段 '{field.name}' 长度 {len(value)} 小于最小长度 {field.min_length}"
                )

        # 检查最大长度
        if field.max_length is not None and hasattr(value, "__len__"):
            if len(value) > field.max_length:
                errors.append(
                    f"字段 '{field.name}' 长度 {len(value)} 大于最大长度 {field.max_length}"
                )

        # 检查正则表达式
        if field.pattern is not None and isinstance(value, str):
            import re

            if not re.match(field.pattern, value):
                errors.append(
                    f"字段 '{field.name}' 值 '{value}' 不匹配模式 '{field.pattern}'"
                )

        # 检查枚举值
        if field.enum_values is not None:
            if value not in field.enum_values:
                errors.append(
                    f"字段 '{field.name}' 值 '{value}' 不在枚举值列表 {field.enum_values} 中"
                )

        return errors

    def _check_type(self, value: Any, expected_type: str) -> bool:
        """检查类型是否匹配"""
        type_mapping = {
            "str": str,
            "int": int,
            "float": float,
            "bool": bool,
            "list": list,
            "dict": dict,
            "datetime": datetime,
        }

        expected = type_mapping.get(expected_type)
        if expected is None:
            return True  # 未知类型，默认通过

        return isinstance(value, expected)


class DatasetRecord(BaseModel):
    """数据集记录"""

    id: str = Field(..., description="记录ID")
    data: Dict[str, Any] = Field(..., description="数据内容")
    labels: Dict[str, Any] = Field(default_factory=dict, description="标签数据")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="元数据")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")

    # 来源信息
    source: str = Field(default="", description="数据来源")
    source_id: str = Field(default="", description="来源ID")

    # 质量信息
    quality: DataQuality = Field(default=DataQuality.RAW, description="数据质量")
    is_valid: bool = Field(default=True, description="是否有效")
    validation_errors: List[str] = Field(default_factory=list, description="验证错误")


class DatasetSplit(BaseModel):
    """数据集分割配置"""

    train_ratio: float = Field(default=0.8, ge=0.0, le=1.0, description="训练集比例")
    val_ratio: float = Field(default=0.1, ge=0.0, le=1.0, description="验证集比例")
    test_ratio: float = Field(default=0.1, ge=0.0, le=1.0, description="测试集比例")
    stratify: bool = Field(default=False, description="是否分层抽样")
    random_seed: int = Field(default=42, description="随机种子")
    shuffle: bool = Field(default=True, description="是否打乱")

    @model_validator(mode="after")
    def validate_ratios(self) -> "DatasetSplit":
        """验证比例之和为1"""
        total = self.train_ratio + self.val_ratio + self.test_ratio
        if abs(total - 1.0) > 0.001:
            raise ValueError(f"比例之和必须为1.0，当前为 {total}")
        return self


class DatasetPipeline(BaseModel):
    """数据集处理管道配置"""

    name: str = Field(..., description="管道名称")
    description: str = Field(default="", description="管道描述")
    steps: List[str] = Field(default_factory=list, description="处理步骤")
    schema: Optional[DatasetSchema] = Field(default=None, description="数据集模式")
    split_config: Optional[DatasetSplit] = Field(default=None, description="分割配置")

    # 输入输出配置
    input_path: Optional[Path] = Field(default=None, description="输入路径")
    output_dir: Path = Field(default=Path("data/datasets"), description="输出目录")

    # 处理配置
    batch_size: int = Field(default=1000, description="批处理大小")
    num_workers: int = Field(default=1, description="工作进程数")
    parallel: bool = Field(default=False, description="是否并行处理")

    # 质量控制
    quality_threshold: float = Field(default=0.8, description="质量阈值")
    skip_invalid: bool = Field(default=True, description="是否跳过无效记录")
    auto_annotate: bool = Field(default=False, description="是否自动标注")

    class Config:
        arbitrary_types_allowed = True


class DatasetVersion(BaseModel):
    """数据集版本信息"""

    version: str = Field(..., description="版本号")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    created_by: str = Field(default="system", description="创建者")
    description: str = Field(default="", description="版本描述")
    changes: List[str] = Field(default_factory=list, description="变更列表")
    parent_version: Optional[str] = Field(default=None, description="父版本")
    checksum: str = Field(default="", description="校验和")
    file_path: Path = Field(default=Path(""), description="文件路径")
    size_bytes: int = Field(default=0, description="文件大小（字节）")
    record_count: int = Field(default=0, description="记录数量")
    is_active: bool = Field(default=True, description="是否激活")

    class Config:
        arbitrary_types_allowed = True


class DatasetMetadata(BaseModel):
    """数据集元数据"""

    id: str = Field(..., description="数据集ID")
    name: str = Field(..., description="数据集名称")
    description: str = Field(default="", description="数据集描述")
    version: str = Field(default="1.0.0", description="当前版本")

    # 基本属性
    dataset_type: DatasetType = Field(default=DatasetType.TRAINING, description="数据集类型")
    data_type: DataType = Field(default=DataType.TEXT, description="数据类型")
    format: DatasetFormat = Field(default=DatasetFormat.PARQUET, description="数据格式")
    quality: DataQuality = Field(default=DataQuality.RAW, description="数据质量")

    # 统计信息
    total_records: int = Field(default=0, description="总记录数")
    train_records: int = Field(default=0, description="训练集记录数")
    val_records: int = Field(default=0, description="验证集记录数")
    test_records: int = Field(default=0, description="测试集记录数")

    # 文件信息
    file_path: Path = Field(default=Path(""), description="主文件路径")
    file_size: int = Field(default=0, description="文件大小（字节）")
    checksum: str = Field(default="", description="校验和")
    compression: str = Field(default="snappy", description="压缩算法")

    # 时间信息
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(default_factory=datetime.now, description="更新时间")
    expires_at: Optional[datetime] = Field(default=None, description="过期时间")

    # 来源信息
    source: str = Field(default="", description="数据来源")
    source_url: Optional[str] = Field(default=None, description="数据源URL")
    source_version: str = Field(default="", description="数据源版本")

    # 标签和分类
    tags: List[str] = Field(default_factory=list, description="标签列表")
    categories: List[str] = Field(default_factory=list, description="分类列表")

    # 许可和使用
    license: str = Field(default="", description="许可证")
    is_public: bool = Field(default=False, description="是否公开")
    owner: str = Field(default="system", description="所有者")

    # 扩展属性
    extra: Dict[str, Any] = Field(default_factory=dict, description="扩展属性")

    class Config:
        use_enum_values = True
        arbitrary_types_allowed = True


class DataFormatConverter:
    """数据格式转换器"""

    @staticmethod
    def get_format_extension(format: DatasetFormat) -> str:
        """获取格式对应的文件扩展名"""
        extensions = {
            DatasetFormat.JSON: ".json",
            DatasetFormat.PARQUET: ".parquet",
            DatasetFormat.CSV: ".csv",
            DatasetFormat.EXCEL: ".xlsx",
            DatasetFormat.HDF5: ".h5",
            DatasetFormat.ARROW: ".arrow",
        }
        return extensions.get(format, ".dat")

    @staticmethod
    def is_binary_format(format: DatasetFormat) -> bool:
        """判断是否为二进制格式"""
        binary_formats = {
            DatasetFormat.PARQUET,
            DatasetFormat.HDF5,
            DatasetFormat.ARROW,
        }
        return format in binary_formats

    @staticmethod
    def supports_compression(format: DatasetFormat) -> bool:
        """判断是否支持压缩"""
        compression_formats = {
            DatasetFormat.PARQUET,
            DatasetFormat.CSV,  # gzip压缩
            DatasetFormat.JSON,  # gzip压缩
        }
        return format in compression_formats

    @staticmethod
    def get_supported_compressions(format: DatasetFormat) -> List[str]:
        """获取格式支持的压缩算法"""
        compressions = {
            DatasetFormat.PARQUET: ["snappy", "gzip", "brotli", "lz4", "zstd"],
            DatasetFormat.CSV: ["gzip", "bz2", "xz"],
            DatasetFormat.JSON: ["gzip", "bz2", "xz"],
            DatasetFormat.HDF5: ["gzip", "lzf", "blosc"],
            DatasetFormat.ARROW: ["lz4", "zstd", "snappy", "gzip"],
        }
        return compressions.get(format, [])
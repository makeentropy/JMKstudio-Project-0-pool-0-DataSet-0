#!/usr/bin/env python3
"""
预训练数据集生成模块使用示例
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.generator import (
    DatasetGenerationPipeline,
    DataFormatter,
    FormatType,
    DataSplitter,
    DataExporter,
    ExportFormat,
)
from config.config import settings


def example_basic_pipeline():
    """
    示例 1: 基础使用 - 完整的数据集生成流程
    """
    print("=" * 60)
    print("示例 1: 基础使用 - 完整的数据集生成流程")
    print("=" * 60)

    pipeline = DatasetGenerationPipeline(
        input_dir=settings.ANNOTATED_DATA_DIR,
        output_dir=settings.FINAL_DATA_DIR,
        train_ratio=0.7,
        val_ratio=0.2,
        test_ratio=0.1,
        enable_augmentation=False,
        export_format=ExportFormat.JSONL,
    )

    try:
        result = pipeline.run()
        print(f"\n数据集生成成功!")
        print(f"输出目录: {result['output_dir']}")
        print(f"\n数据集划分信息:")
        for k, v in result['split_info'].items():
            print(f"  {k}: {v}")
        print(f"\n导出路径:")
        for k, v in result['export_paths'].items():
            print(f"  {k}: {v}")
    except Exception as e:
        print(f"错误: {e}")


def example_different_formats():
    """
    示例 2: 导出不同格式的数据集
    """
    print("\n" + "=" * 60)
    print("示例 2: 导出不同格式的数据集")
    print("=" * 60)

    for format_type in [ExportFormat.JSONL, ExportFormat.PARQUET, ExportFormat.ALPACA, ExportFormat.LLAMA]:
        print(f"\n导出格式: {format_type.value}")
        pipeline = DatasetGenerationPipeline(
            export_format=format_type,
        )
        try:
            result = pipeline.run()
            print(f"  成功! 输出: {result['output_dir']}")
        except Exception as e:
            print(f"  错误: {e}")


def example_with_augmentation():
    """
    示例 3: 启用数据增强
    """
    print("\n" + "=" * 60)
    print("示例 3: 启用数据增强")
    print("=" * 60)

    pipeline = DatasetGenerationPipeline(
        enable_augmentation=True,
        export_format=ExportFormat.JSONL,
    )

    try:
        result = pipeline.run()
        print(f"\n数据增强的数据集生成成功!")
        print(f"输出目录: {result['output_dir']}")
    except Exception as e:
        print(f"错误: {e}")


def example_custom_split():
    """
    示例 4: 自定义数据集划分比例
    """
    print("\n" + "=" * 60)
    print("示例 4: 自定义数据集划分比例 (80/10/10)")
    print("=" * 60)

    pipeline = DatasetGenerationPipeline(
        train_ratio=0.8,
        val_ratio=0.1,
        test_ratio=0.1,
        export_format=ExportFormat.JSONL,
    )

    try:
        result = pipeline.run()
        print(f"\n自定义比例的数据集生成成功!")
        print(f"输出目录: {result['output_dir']}")
    except Exception as e:
        print(f"错误: {e}")


if __name__ == "__main__":
    print("预训练数据集生成模块示例\n")

    # 运行所有示例
    example_basic_pipeline()
    # example_different_formats()  # 取消注释以运行
    # example_with_augmentation()  # 取消注释以运行
    # example_custom_split()  # 取消注释以运行

    print("\n" + "=" * 60)
    print("所有示例运行完成!")
    print("=" * 60)

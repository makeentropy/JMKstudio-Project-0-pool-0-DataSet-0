#!/usr/bin/env python3
"""
数据标注模块使用示例

本示例展示了如何使用数据标注模块的各项功能，包括：
1. 使用半自动标注器进行标注
2. 使用人工标注器进行标注
3. 标签管理
4. 质量检查
5. 数据存储
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.annotator import (
    AnnotationLabel,
    AnnotatedData,
    LabelManager,
    ManualAnnotator,
    SemiAutoAnnotator,
    QualityChecker,
    AnnotationStorage
)
from src.collector.models import AgentInteraction


def create_sample_interactions() -> list[AgentInteraction]:
    """创建示例交互数据"""
    interactions = [
        AgentInteraction(
            user_input="你好，请问如何学习Python？",
            agent_response="你好！学习Python可以从基础开始，推荐先看官方教程，然后多做练习。"
        ),
        AgentInteraction(
            user_input="谢谢，你的回答很有帮助！",
            agent_response="不客气，很高兴能帮到你。"
        ),
        AgentInteraction(
            user_input="这个答案不对，你能重新回答吗？",
            agent_response="抱歉，让我重新解释一下。"
        ),
        AgentInteraction(
            user_input="太短了",
            agent_response="好"
        ),
        AgentInteraction(
            user_input="这个回答太棒了，完美解决了我的问题！",
            agent_response="非常感谢您的反馈，这对我们很重要。"
        )
    ]
    return interactions


def example_semi_auto_annotation():
    """示例1：使用半自动标注器"""
    print("=" * 60)
    print("示例1：半自动标注")
    print("=" * 60)

    interactions = create_sample_interactions()
    annotator = SemiAutoAnnotator()

    annotated_data_list = annotator.annotate_batch(interactions)

    for i, data in enumerate(annotated_data_list):
        print(f"\n交互 {i + 1}:")
        print(f"  用户输入: {data.original_interaction.user_input}")
        print(f"  助手回复: {data.original_interaction.agent_response}")
        print(f"  标注结果:")
        for ann in data.annotations:
            print(f"    - 标签: {ann.label.value}, 置信度: {ann.confidence:.2f}")
            if ann.metadata:
                print(f"      元数据: {ann.metadata}")

    print("\n" + "=" * 60)
    print("标签建议:")
    print("=" * 60)
    for i, interaction in enumerate(interactions):
        suggestions = annotator.suggest_labels(interaction)
        print(f"\n交互 {i + 1} 的建议:")
        for sugg in suggestions:
            print(f"  - {sugg['label'].value}: {sugg['confidence']:.2f}")

    return annotated_data_list


def example_manual_annotation():
    """示例2：使用人工标注器"""
    print("\n" + "=" * 60)
    print("示例2：人工标注")
    print("=" * 60)

    interactions = create_sample_interactions()
    annotator = ManualAnnotator(annotator_id="human_001")

    annotation1 = annotator.create_annotation(
        label=AnnotationLabel.HELPFUL,
        confidence=1.0,
        notes="用户明确表示有帮助"
    )

    annotation2 = annotator.create_annotation(
        label=AnnotationLabel.POSITIVE,
        confidence=0.9
    )

    annotated_data = annotator.annotate(
        interactions[1],
        annotations=[annotation1, annotation2]
    )

    print(f"\n用户输入: {annotated_data.original_interaction.user_input}")
    print(f"助手回复: {annotated_data.original_interaction.agent_response}")
    print(f"人工标注:")
    for ann in annotated_data.annotations:
        print(f"  - {ann.label.value}, 置信度: {ann.confidence}")
        if ann.notes:
            print(f"    备注: {ann.notes}")

    return annotated_data


def example_label_management():
    """示例3：标签管理"""
    print("\n" + "=" * 60)
    print("示例3：标签管理")
    print("=" * 60)

    label_manager = LabelManager()

    print("\n所有可用标签:")
    for label in label_manager.get_all_labels():
        print(f"  - {label.value}")

    print("\n按类别查看标签:")
    for category in label_manager.get_all_categories():
        print(f"\n  {category.name} ({category.description}):")
        labels = label_manager.get_labels_by_category(category.name)
        for label in labels:
            print(f"    - {label.value}")

    label_manager.add_custom_label("urgent")
    print(f"\n添加自定义标签后: {label_manager.get_all_custom_labels()}")


def example_quality_check(annotated_data_list: list[AnnotatedData]):
    """示例4：质量检查"""
    print("\n" + "=" * 60)
    print("示例4：质量检查")
    print("=" * 60)

    checker = QualityChecker(low_confidence_threshold=0.5)

    metrics = checker.assess_batch(annotated_data_list)

    print("\n质量统计:")
    print(f"  总标注数: {metrics.total_annotations}")
    print(f"  已验证数: {metrics.verified_count}")
    print(f"  平均置信度: {metrics.average_confidence:.2f}")
    print(f"  冲突数: {metrics.conflict_count}")
    print(f"  低置信度数: {metrics.low_confidence_count}")

    print("\n单条数据检查:")
    for i, data in enumerate(annotated_data_list):
        score, issues = checker.assess_single(data)
        print(f"\n  数据 {i + 1}:")
        print(f"    质量分数: {score:.2f}")
        if issues:
            print(f"    问题: {issues}")

    filtered = checker.filter_low_quality(annotated_data_list, min_score=0.6)
    print(f"\n筛选后高质量数据: {len(filtered)}/{len(annotated_data_list)}")


def example_storage(annotated_data_list: list[AnnotatedData]):
    """示例5：数据存储"""
    print("\n" + "=" * 60)
    print("示例5：数据存储")
    print("=" * 60)

    storage = AnnotationStorage()

    saved_path = storage.save_batch(annotated_data_list)
    print(f"\n已保存到: {saved_path}")

    loaded_data = storage.load_batch(saved_path)
    print(f"已加载: {len(loaded_data)} 条数据")

    stats = storage.get_statistics()
    print("\n存储统计:")
    for key, value in stats.items():
        print(f"  {key}: {value}")


def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("数据标注模块使用示例")
    print("=" * 60)

    annotated_data_list = example_semi_auto_annotation()
    example_manual_annotation()
    example_label_management()
    example_quality_check(annotated_data_list)
    example_storage(annotated_data_list)

    print("\n" + "=" * 60)
    print("所有示例运行完成！")
    print("=" * 60)


if __name__ == "__main__":
    main()

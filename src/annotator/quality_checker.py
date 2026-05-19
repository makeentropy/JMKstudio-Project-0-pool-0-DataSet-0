from typing import Dict, List, Optional, Tuple
from collections import Counter
from datetime import datetime

from .models import Annotation, AnnotationLabel, AnnotatedData
from .label_manager import LabelManager


class QualityMetrics:
    def __init__(self):
        self.total_annotations: int = 0
        self.verified_count: int = 0
        self.average_confidence: float = 0.0
        self.label_distribution: Dict[AnnotationLabel, int] = {}
        self.annotator_distribution: Dict[str, int] = {}
        self.conflict_count: int = 0
        self.low_confidence_count: int = 0
        self.low_confidence_threshold: float = 0.5

    def to_dict(self) -> Dict:
        return {
            "total_annotations": self.total_annotations,
            "verified_count": self.verified_count,
            "average_confidence": self.average_confidence,
            "label_distribution": {k.value: v for k, v in self.label_distribution.items()},
            "annotator_distribution": self.annotator_distribution,
            "conflict_count": self.conflict_count,
            "low_confidence_count": self.low_confidence_count,
            "verification_rate": self.verified_count / max(1, self.total_annotations)
        }


class QualityChecker:
    def __init__(
        self,
        low_confidence_threshold: float = 0.5,
        min_annotations_per_item: int = 1
    ):
        self.low_confidence_threshold = low_confidence_threshold
        self.min_annotations_per_item = min_annotations_per_item
        self.label_manager = LabelManager()

    def check_annotation_confidence(
        self,
        annotation: Annotation
    ) -> Tuple[bool, Optional[str]]:
        if annotation.confidence < self.low_confidence_threshold:
            return False, f"置信度 {annotation.confidence:.2f} 低于阈值 {self.low_confidence_threshold}"
        return True, None

    def check_label_validity(
        self,
        annotation: Annotation
    ) -> Tuple[bool, Optional[str]]:
        is_valid = self.label_manager.validate_label(
            annotation.label,
            annotation.custom_label
        )
        if not is_valid:
            return False, f"标签 {annotation.label} 无效"
        return True, None

    def check_conflicts(
        self,
        annotations: List[Annotation]
    ) -> List[Tuple[Annotation, Annotation, str]]:
        conflicts = []
        label_manager = self.label_manager

        category_annotations: Dict[str, List[Annotation]] = {}
        for ann in annotations:
            category = label_manager.get_label_category(ann.label)
            if category:
                if category not in category_annotations:
                    category_annotations[category] = []
                category_annotations[category].append(ann)

        conflicting_pairs = {
            "sentiment": [
                (AnnotationLabel.POSITIVE, AnnotationLabel.NEGATIVE),
            ],
            "quality": [
                (AnnotationLabel.HELPFUL, AnnotationLabel.UNHELPFUL),
                (AnnotationLabel.CORRECT, AnnotationLabel.INCORRECT),
                (AnnotationLabel.COMPLETE, AnnotationLabel.INCOMPLETE),
            ],
            "relevance": [
                (AnnotationLabel.RELEVANT, AnnotationLabel.IRRELEVANT),
            ],
            "safety": [
                (AnnotationLabel.SAFE, AnnotationLabel.UNSAFE),
            ]
        }

        for category, anns in category_annotations.items():
            if category in conflicting_pairs:
                pairs = conflicting_pairs[category]
                for i, ann1 in enumerate(anns):
                    for ann2 in anns[i+1:]:
                        for label1, label2 in pairs:
                            if (ann1.label == label1 and ann2.label == label2) or \
                               (ann1.label == label2 and ann2.label == label1):
                                conflicts.append((
                                    ann1,
                                    ann2,
                                    f"类别 {category} 中存在冲突标签: {label1.value} vs {label2.value}"
                                ))

        return conflicts

    def assess_single(
        self,
        annotated_data: AnnotatedData
    ) -> Tuple[float, List[str]]:
        issues = []
        score = 1.0

        if not annotated_data.annotations:
            issues.append("没有标注信息")
            score = 0.0
            return score, issues

        if len(annotated_data.annotations) < self.min_annotations_per_item:
            issues.append(f"标注数量不足，需要至少 {self.min_annotations_per_item} 个")
            score *= 0.7

        total_confidence = 0.0
        for annotation in annotated_data.annotations:
            valid, msg = self.check_label_validity(annotation)
            if not valid and msg:
                issues.append(msg)
                score *= 0.8

            confident, msg = self.check_annotation_confidence(annotation)
            if not confident and msg:
                issues.append(msg)
                score *= 0.9

            total_confidence += annotation.confidence

        conflicts = self.check_conflicts(annotated_data.annotations)
        if conflicts:
            for _, _, msg in conflicts:
                issues.append(msg)
            score *= max(0.5, 1.0 - len(conflicts) * 0.2)

        avg_confidence = total_confidence / len(annotated_data.annotations)
        score = score * (0.7 + 0.3 * avg_confidence)

        if annotated_data.is_verified:
            score = min(1.0, score + 0.1)

        return min(1.0, max(0.0, score)), issues

    def assess_batch(
        self,
        annotated_data_list: List[AnnotatedData]
    ) -> QualityMetrics:
        metrics = QualityMetrics()
        metrics.low_confidence_threshold = self.low_confidence_threshold

        if not annotated_data_list:
            return metrics

        total_confidence = 0.0
        total_annotations_count = 0
        label_counter = Counter()
        annotator_counter = Counter()

        for annotated_data in annotated_data_list:
            metrics.total_annotations += 1
            if annotated_data.is_verified:
                metrics.verified_count += 1

            score, _ = self.assess_single(annotated_data)
            annotated_data.quality_score = score

            for annotation in annotated_data.annotations:
                total_confidence += annotation.confidence
                total_annotations_count += 1
                label_counter[annotation.label] += 1
                if annotation.annotator_id:
                    annotator_counter[annotation.annotator_id] += 1
                if annotation.confidence < self.low_confidence_threshold:
                    metrics.low_confidence_count += 1

            conflicts = self.check_conflicts(annotated_data.annotations)
            if conflicts:
                metrics.conflict_count += 1

        if total_annotations_count > 0:
            metrics.average_confidence = total_confidence / total_annotations_count

        metrics.label_distribution = dict(label_counter)
        metrics.annotator_distribution = dict(annotator_counter)

        return metrics

    def filter_low_quality(
        self,
        annotated_data_list: List[AnnotatedData],
        min_score: float = 0.6
    ) -> List[AnnotatedData]:
        filtered = []
        for annotated_data in annotated_data_list:
            score, _ = self.assess_single(annotated_data)
            if score >= min_score:
                filtered.append(annotated_data)
        return filtered

    def get_needs_review(
        self,
        annotated_data_list: List[AnnotatedData]
    ) -> List[AnnotatedData]:
        needs_review = []
        for annotated_data in annotated_data_list:
            score, issues = self.assess_single(annotated_data)
            if issues or score < 0.8 or not annotated_data.is_verified:
                needs_review.append(annotated_data)
        return needs_review

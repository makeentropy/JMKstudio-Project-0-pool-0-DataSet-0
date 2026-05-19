from typing import Dict, List, Optional, Set
from .models import AnnotationLabel


class LabelCategory:
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.labels: Set[AnnotationLabel] = set()


class LabelManager:
    def __init__(self):
        self.categories: Dict[str, LabelCategory] = {}
        self.custom_labels: Set[str] = set()
        self._init_default_categories()

    def _init_default_categories(self) -> None:
        sentiment = LabelCategory(
            name="sentiment",
            description="情感倾向标签"
        )
        sentiment.labels.update([
            AnnotationLabel.POSITIVE,
            AnnotationLabel.NEGATIVE,
            AnnotationLabel.NEUTRAL
        ])
        self.categories["sentiment"] = sentiment

        quality = LabelCategory(
            name="quality",
            description="质量评价标签"
        )
        quality.labels.update([
            AnnotationLabel.INFORMATIVE,
            AnnotationLabel.HELPFUL,
            AnnotationLabel.UNHELPFUL,
            AnnotationLabel.CORRECT,
            AnnotationLabel.INCORRECT,
            AnnotationLabel.COMPLETE,
            AnnotationLabel.INCOMPLETE
        ])
        self.categories["quality"] = quality

        relevance = LabelCategory(
            name="relevance",
            description="相关性标签"
        )
        relevance.labels.update([
            AnnotationLabel.RELEVANT,
            AnnotationLabel.IRRELEVANT
        ])
        self.categories["relevance"] = relevance

        safety = LabelCategory(
            name="safety",
            description="安全性标签"
        )
        safety.labels.update([
            AnnotationLabel.SAFE,
            AnnotationLabel.UNSAFE
        ])
        self.categories["safety"] = safety

    def add_category(self, name: str, description: str = "") -> LabelCategory:
        if name in self.categories:
            return self.categories[name]
        category = LabelCategory(name, description)
        self.categories[name] = category
        return category

    def add_label_to_category(self, label: AnnotationLabel, category_name: str) -> None:
        if category_name not in self.categories:
            self.add_category(category_name)
        self.categories[category_name].labels.add(label)

    def remove_label_from_category(self, label: AnnotationLabel, category_name: str) -> None:
        if category_name in self.categories:
            self.categories[category_name].labels.discard(label)

    def get_labels_by_category(self, category_name: str) -> List[AnnotationLabel]:
        if category_name not in self.categories:
            return []
        return list(self.categories[category_name].labels)

    def get_all_categories(self) -> List[LabelCategory]:
        return list(self.categories.values())

    def add_custom_label(self, label: str) -> None:
        self.custom_labels.add(label)

    def remove_custom_label(self, label: str) -> None:
        self.custom_labels.discard(label)

    def get_all_custom_labels(self) -> List[str]:
        return list(self.custom_labels)

    def get_all_labels(self) -> List[AnnotationLabel]:
        all_labels = set()
        for category in self.categories.values():
            all_labels.update(category.labels)
        return list(all_labels)

    def get_label_category(self, label: AnnotationLabel) -> Optional[str]:
        for category_name, category in self.categories.items():
            if label in category.labels:
                return category_name
        return None

    def validate_label(self, label: AnnotationLabel, custom_label: Optional[str] = None) -> bool:
        if label != AnnotationLabel.CUSTOM:
            return label in self.get_all_labels()
        return custom_label is not None and custom_label in self.custom_labels

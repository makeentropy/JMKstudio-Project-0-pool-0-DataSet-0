from typing import List, Tuple, Dict, Any
import random
from dataclasses import dataclass

from ..annotator.models import AnnotatedData


@dataclass
class DatasetSplit:
    train: List[AnnotatedData]
    val: List[AnnotatedData]
    test: List[AnnotatedData]


class DataSplitter:
    def __init__(
        self,
        train_ratio: float = 0.7,
        val_ratio: float = 0.2,
        test_ratio: float = 0.1,
        random_seed: int = 42,
        stratify: bool = False,
    ):
        total = train_ratio + val_ratio + test_ratio
        if not abs(total - 1.0) < 1e-6:
            raise ValueError("Sum of ratios must be 1.0")

        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.test_ratio = test_ratio
        self.random_seed = random_seed
        self.stratify = stratify
        random.seed(random_seed)

    def split(self, data_list: List[AnnotatedData]) -> DatasetSplit:
        if not data_list:
            return DatasetSplit(train=[], val=[], test=[])

        shuffled = data_list.copy()
        random.shuffle(shuffled)

        n = len(shuffled)
        train_end = int(n * self.train_ratio)
        val_end = train_end + int(n * self.val_ratio)

        train = shuffled[:train_end]
        val = shuffled[train_end:val_end]
        test = shuffled[val_end:]

        return DatasetSplit(train=train, val=val, test=test)

    def split_with_stratification(
        self,
        data_list: List[AnnotatedData],
        stratify_key: str = "quality_score",
    ) -> DatasetSplit:
        if not self.stratify:
            return self.split(data_list)

        stratified: Dict[Any, List[AnnotatedData]] = {}

        for data in data_list:
            key = self._get_stratify_key(data, stratify_key)
            if key not in stratified:
                stratified[key] = []
            stratified[key].append(data)

        train, val, test = [], [], []

        for group in stratified.values():
            split = self.split(group)
            train.extend(split.train)
            val.extend(split.val)
            test.extend(split.test)

        random.shuffle(train)
        random.shuffle(val)
        random.shuffle(test)

        return DatasetSplit(train=train, val=val, test=test)

    def _get_stratify_key(self, data: AnnotatedData, key: str) -> Any:
        if key == "quality_score":
            if data.quality_score is None:
                return "unknown"
            elif data.quality_score >= 0.8:
                return "high"
            elif data.quality_score >= 0.5:
                return "medium"
            else:
                return "low"
        elif key == "is_verified":
            return data.is_verified
        elif key == "has_annotations":
            return len(data.annotations) > 0
        else:
            return "default"

    def get_split_info(self, split: DatasetSplit) -> Dict[str, Any]:
        return {
            "train_count": len(split.train),
            "val_count": len(split.val),
            "test_count": len(split.test),
            "total_count": len(split.train) + len(split.val) + len(split.test),
            "train_ratio": len(split.train) / max(len(split.train) + len(split.val) + len(split.test), 1),
            "val_ratio": len(split.val) / max(len(split.train) + len(split.val) + len(split.test), 1),
            "test_ratio": len(split.test) / max(len(split.train) + len(split.val) + len(split.test), 1),
        }

from typing import List, Optional
import random
import re

from ..annotator.models import AnnotatedData


class TextAugmenter:
    def __init__(
        self,
        enable_synonym_replacement: bool = True,
        enable_random_deletion: bool = False,
        enable_random_swap: bool = False,
        augmentation_probability: float = 0.1,
        random_seed: int = 42,
    ):
        self.enable_synonym_replacement = enable_synonym_replacement
        self.enable_random_deletion = enable_random_deletion
        self.enable_random_swap = enable_random_swap
        self.augmentation_probability = augmentation_probability
        self.random_seed = random_seed
        random.seed(random_seed)

    def augment(self, data_list: List[AnnotatedData]) -> List[AnnotatedData]:
        augmented = []
        for data in data_list:
            augmented.append(data)
            new_data = self._augment_single(data)
            if new_data:
                augmented.append(new_data)
        return augmented

    def _augment_single(self, data: AnnotatedData) -> Optional[AnnotatedData]:
        if random.random() > self.augmentation_probability:
            return None

        import copy

        new_data = copy.deepcopy(data)

        if self.enable_synonym_replacement:
            new_data = self._synonym_replacement(new_data)

        if self.enable_random_deletion:
            new_data = self._random_deletion(new_data)

        if self.enable_random_swap:
            new_data = self._random_swap(new_data)

        new_data.id = f"{data.id}_aug"
        new_data.metadata["augmented"] = True
        new_data.metadata["original_id"] = data.id

        return new_data

    def _synonym_replacement(self, data: AnnotatedData) -> AnnotatedData:
        words = self._tokenize(data.original_interaction.user_input)
        if len(words) < 2:
            return data

        replacements = self._get_synonym_map()
        new_words = []
        for word in words:
            if word in replacements and random.random() < 0.5:
                new_words.append(random.choice(replacements[word]))
            else:
                new_words.append(word)

        data.original_interaction.user_input = self._detokenize(new_words)
        return data

    def _random_deletion(self, data: AnnotatedData) -> AnnotatedData:
        words = self._tokenize(data.original_interaction.user_input)
        if len(words) < 3:
            return data

        delete_idx = random.randint(0, len(words) - 1)
        words.pop(delete_idx)
        data.original_interaction.user_input = self._detokenize(words)
        return data

    def _random_swap(self, data: AnnotatedData) -> AnnotatedData:
        words = self._tokenize(data.original_interaction.user_input)
        if len(words) < 2:
            return data

        idx1 = random.randint(0, len(words) - 1)
        idx2 = random.randint(0, len(words) - 1)
        while idx2 == idx1:
            idx2 = random.randint(0, len(words) - 1)

        words[idx1], words[idx2] = words[idx2], words[idx1]
        data.original_interaction.user_input = self._detokenize(words)
        return data

    def _tokenize(self, text: str) -> List[str]:
        return re.findall(r"\w+|\S", text)

    def _detokenize(self, tokens: List[str]) -> str:
        return "".join(tokens)

    def _get_synonym_map(self) -> dict:
        return {
            "你好": ["您好", "嗨", "哈喽"],
            "谢谢": ["感谢", "多谢", "谢谢你"],
            "好的": ["好", "行", "可以"],
            "请问": ["想问一下", "我想问问", "咨询一下"],
            "如何": ["怎么", "怎样", "如何"],
            "学习": ["学习一下", "学", "研究"],
        }

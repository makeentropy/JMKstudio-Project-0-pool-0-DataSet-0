from typing import Any, Dict, List, Optional, Callable
from uuid import uuid4
import re

from .models import Annotation, AnnotationLabel, AnnotatedData
from .label_manager import LabelManager
from ..collector.models import AgentInteraction


class BaseAnnotator:
    def __init__(self, annotator_id: Optional[str] = None):
        self.annotator_id = annotator_id or str(uuid4())
        self.label_manager = LabelManager()

    def annotate(self, interaction: AgentInteraction) -> AnnotatedData:
        raise NotImplementedError

    def annotate_batch(self, interactions: List[AgentInteraction]) -> List[AnnotatedData]:
        return [self.annotate(interaction) for interaction in interactions]


class ManualAnnotator(BaseAnnotator):
    def __init__(self, annotator_id: Optional[str] = None):
        super().__init__(annotator_id)
        self.annotator_type = "manual"

    def create_annotation(
        self,
        label: AnnotationLabel,
        custom_label: Optional[str] = None,
        confidence: float = 1.0,
        notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Annotation:
        return Annotation(
            label=label,
            custom_label=custom_label,
            confidence=confidence,
            annotator_type=self.annotator_type,
            annotator_id=self.annotator_id,
            notes=notes,
            metadata=metadata or {}
        )

    def annotate(
        self,
        interaction: AgentInteraction,
        annotations: Optional[List[Annotation]] = None
    ) -> AnnotatedData:
        annotated_data = AnnotatedData(original_interaction=interaction)
        if annotations:
            for annotation in annotations:
                annotated_data.add_annotation(annotation)
        return annotated_data

    def get_interaction_for_annotation(self, interaction: AgentInteraction) -> Dict[str, Any]:
        return {
            "id": interaction.id,
            "user_input": interaction.user_input,
            "agent_response": interaction.agent_response,
            "tool_calls": interaction.tool_calls,
            "timestamp": interaction.timestamp,
            "available_labels": self.label_manager.get_all_labels(),
            "available_categories": [
                (cat.name, cat.description) 
                for cat in self.label_manager.get_all_categories()
            ]
        }


class SemiAutoAnnotator(BaseAnnotator):
    def __init__(
        self,
        annotator_id: Optional[str] = None,
        keyword_rules: Optional[Dict[str, List[str]]] = None
    ):
        super().__init__(annotator_id)
        self.annotator_type = "semi_auto"
        self.keyword_rules = keyword_rules or self._default_keyword_rules()
        self.custom_heuristics: List[Callable[[AgentInteraction], Optional[Annotation]]] = []

    def _default_keyword_rules(self) -> Dict[str, List[str]]:
        return {
            AnnotationLabel.POSITIVE: [
                "谢谢", "感谢", "很好", "太棒了", "完美", "满意", "优秀",
                "great", "excellent", "perfect", "thank you", "thanks", "good"
            ],
            AnnotationLabel.NEGATIVE: [
                "不好", "糟糕", "错误", "不对", "不满意", "差", "失望",
                "bad", "terrible", "wrong", "worst", "awful", "disappointed"
            ],
            AnnotationLabel.HELPFUL: [
                "帮助", "有用", "解决", "解答", "helpful", "useful", "solve"
            ],
            AnnotationLabel.CORRECT: [
                "正确", "对的", "没错", "correct", "right", "accurate"
            ],
            AnnotationLabel.SAFE: [
                "安全", "合法", "规范", "safe", "legal", "appropriate"
            ]
        }

    def add_heuristic(
        self,
        heuristic: Callable[[AgentInteraction], Optional[Annotation]]
    ) -> None:
        self.custom_heuristics.append(heuristic)

    def _keyword_based_annotation(
        self,
        interaction: AgentInteraction
    ) -> List[Annotation]:
        annotations = []
        text = f"{interaction.user_input} {interaction.agent_response}".lower()

        for label, keywords in self.keyword_rules.items():
            matched_keywords = []
            for keyword in keywords:
                if keyword.lower() in text:
                    matched_keywords.append(keyword)
            
            if matched_keywords:
                confidence = min(0.5 + (len(matched_keywords) * 0.1), 0.9)
                annotation = Annotation(
                    label=label,
                    confidence=confidence,
                    annotator_type=self.annotator_type,
                    annotator_id=self.annotator_id,
                    metadata={
                        "matched_keywords": matched_keywords,
                        "method": "keyword"
                    }
                )
                annotations.append(annotation)
        
        return annotations

    def _length_based_annotation(
        self,
        interaction: AgentInteraction
    ) -> Optional[Annotation]:
        response_length = len(interaction.agent_response)
        
        if response_length < 20:
            return Annotation(
                label=AnnotationLabel.INCOMPLETE,
                confidence=0.6,
                annotator_type=self.annotator_type,
                annotator_id=self.annotator_id,
                metadata={
                    "response_length": response_length,
                    "method": "length"
                }
            )
        elif response_length > 500:
            return Annotation(
                label=AnnotationLabel.COMPLETE,
                confidence=0.5,
                annotator_type=self.annotator_type,
                annotator_id=self.annotator_id,
                metadata={
                    "response_length": response_length,
                    "method": "length"
                }
            )
        return None

    def annotate(self, interaction: AgentInteraction) -> AnnotatedData:
        annotated_data = AnnotatedData(original_interaction=interaction)

        keyword_annotations = self._keyword_based_annotation(interaction)
        for annotation in keyword_annotations:
            annotated_data.add_annotation(annotation)

        length_annotation = self._length_based_annotation(interaction)
        if length_annotation:
            annotated_data.add_annotation(length_annotation)

        for heuristic in self.custom_heuristics:
            custom_annotation = heuristic(interaction)
            if custom_annotation:
                annotated_data.add_annotation(custom_annotation)

        return annotated_data

    def suggest_labels(
        self,
        interaction: AgentInteraction,
        min_confidence: float = 0.3
    ) -> List[Dict[str, Any]]:
        annotated_data = self.annotate(interaction)
        suggestions = []
        for annotation in annotated_data.annotations:
            if annotation.confidence >= min_confidence:
                suggestions.append({
                    "label": annotation.label,
                    "custom_label": annotation.custom_label,
                    "confidence": annotation.confidence,
                    "metadata": annotation.metadata
                })
        return suggestions

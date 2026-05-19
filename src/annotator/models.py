from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from uuid import uuid4

from ..collector.models import AgentInteraction


class AnnotationLabel(str, Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    INFORMATIVE = "informative"
    HELPFUL = "helpful"
    UNHELPFUL = "unhelpful"
    CORRECT = "correct"
    INCORRECT = "incorrect"
    COMPLETE = "complete"
    INCOMPLETE = "incomplete"
    RELEVANT = "relevant"
    IRRELEVANT = "irrelevant"
    SAFE = "safe"
    UNSAFE = "unsafe"
    CUSTOM = "custom"


class Annotation(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    label: AnnotationLabel
    custom_label: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    annotator_type: str
    annotator_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)
    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class AnnotatedData(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    original_interaction: AgentInteraction
    annotations: List[Annotation] = Field(default_factory=list)
    is_verified: bool = False
    verified_by: Optional[str] = None
    verified_at: Optional[datetime] = None
    quality_score: Optional[float] = Field(ge=0.0, le=1.0, default=None)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def add_annotation(self, annotation: Annotation) -> None:
        self.annotations.append(annotation)
        self.updated_at = datetime.now()

    def verify(self, verifier_id: str) -> None:
        self.is_verified = True
        self.verified_by = verifier_id
        self.verified_at = datetime.now()
        self.updated_at = datetime.now()

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from uuid import uuid4


class ToolCall(BaseModel):
    name: str
    arguments: Dict[str, Any]
    result: Optional[Any] = None


class AgentInteraction(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)
    user_input: str
    agent_response: str
    tool_calls: List[ToolCall] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class DataCollectionRequest(BaseModel):
    interactions: List[AgentInteraction]
    source: Optional[str] = None
    tags: Optional[List[str]] = None

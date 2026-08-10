"""API request/response models."""
from __future__ import annotations

from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., description="The user's question.")
    history: list[Message] = Field(default_factory=list)


class TraceStep(BaseModel):
    kind: str
    name: str | None = None
    provider: str | None = None
    decided: str | None = None
    tools: list[str] | None = None
    action: str | None = None


class ChatResponse(BaseModel):
    answer: str
    trace: list[dict] = Field(default_factory=list)
    demo_mode: bool = False

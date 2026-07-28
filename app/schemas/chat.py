"""Chat API contracts."""

from pydantic import Field

from app.domain.common import DomainModel, MachineId
from app.schemas.recommendations import AgentRecommendation


class ChatRequest(DomainModel):
    message: str = Field(min_length=1, max_length=10_000)
    session_id: str | None = Field(default=None, min_length=1)
    machine_id: MachineId | None = None


class ChatResponse(DomainModel):
    request_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    result: AgentRecommendation

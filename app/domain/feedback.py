"""Agent feedback domain contract."""

from datetime import datetime

from pydantic import Field, field_validator

from app.domain.common import DomainModel, FeedbackRating, require_utc


class AgentFeedback(DomainModel):
    feedback_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    rating: FeedbackRating
    created_at: datetime
    comment: str | None = Field(default=None, max_length=2000)
    agent_version: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    model_version: str = Field(min_length=1)

    @field_validator("created_at")
    @classmethod
    def timestamp_is_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

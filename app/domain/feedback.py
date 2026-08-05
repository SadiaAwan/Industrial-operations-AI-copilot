"""Agent feedback domain contract."""

from datetime import datetime

from pydantic import Field, field_validator

from app.domain.common import DomainModel, FeedbackRating, require_utc
from app.domain.privacy import MAX_FEEDBACK_COMMENT_LENGTH, sanitize_feedback_comment


class AgentFeedback(DomainModel):
    feedback_id: str = Field(min_length=1)
    session_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    trace_id: str = Field(min_length=1, max_length=128)
    rating: FeedbackRating
    created_at: datetime
    comment: str | None = Field(default=None, max_length=MAX_FEEDBACK_COMMENT_LENGTH)
    agent_version: str = Field(min_length=1)
    prompt_version: str = Field(min_length=1)
    prompt_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    model_version: str = Field(min_length=1)

    @field_validator("comment", mode="before")
    @classmethod
    def comment_is_sanitized(cls, value: object) -> object:
        return sanitize_feedback_comment(value) if isinstance(value, str) else value

    @field_validator("created_at")
    @classmethod
    def timestamp_is_utc(cls, value: datetime) -> datetime:
        return require_utc(value)

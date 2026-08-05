"""Feedback API contracts."""

from pydantic import Field, field_validator

from app.domain.common import DomainModel, FeedbackRating
from app.domain.feedback import AgentFeedback
from app.domain.privacy import MAX_FEEDBACK_COMMENT_LENGTH, sanitize_feedback_comment


class FeedbackCreate(DomainModel):
    session_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    rating: FeedbackRating
    comment: str | None = Field(default=None, max_length=MAX_FEEDBACK_COMMENT_LENGTH)

    @field_validator("comment", mode="before")
    @classmethod
    def sanitize_comment(cls, value: object) -> object:
        return sanitize_feedback_comment(value) if isinstance(value, str) else value


class FeedbackResponse(DomainModel):
    feedback: AgentFeedback

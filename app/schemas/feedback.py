"""Feedback API contracts."""

from pydantic import Field

from app.domain.common import DomainModel, FeedbackRating


class FeedbackCreate(DomainModel):
    session_id: str = Field(min_length=1)
    request_id: str = Field(min_length=1)
    rating: FeedbackRating
    comment: str | None = Field(default=None, max_length=2000)

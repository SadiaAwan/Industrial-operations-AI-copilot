"""Serializable UI state and bounded chat history helpers."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.schemas.chat import ChatResponse

MAX_CHAT_MESSAGES = 40


@dataclass(frozen=True, slots=True)
class ChatTurn:
    user_message: str
    response: ChatResponse


@dataclass(slots=True)
class CopilotUIState:
    selected_machine_id: str = "P-104"
    session_id: str | None = None
    turns: list[ChatTurn] = field(default_factory=list)
    submitted_feedback_request_ids: set[str] = field(default_factory=set)

    def select_machine(self, machine_id: str) -> None:
        if machine_id != self.selected_machine_id:
            self.selected_machine_id = machine_id
            self.session_id = None
            self.turns.clear()
            self.submitted_feedback_request_ids.clear()

    def record_turn(self, user_message: str, response: ChatResponse) -> None:
        self.session_id = response.session_id
        self.turns.append(ChatTurn(user_message=user_message, response=response))
        if len(self.turns) > MAX_CHAT_MESSAGES:
            del self.turns[: len(self.turns) - MAX_CHAT_MESSAGES]

    def mark_feedback_submitted(self, request_id: str) -> None:
        self.submitted_feedback_request_ids.add(request_id)

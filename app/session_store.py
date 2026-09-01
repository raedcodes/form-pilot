from dataclasses import dataclass, field

from app.models import FormPlan


@dataclass
class ConversationState:
    conversation: list[dict[str, str]] = field(default_factory=list)
    clarification_rounds: int = 0
    assumptions: list[str] = field(default_factory=list)
    plan: FormPlan | None = None
    awaiting_confirmation: bool = False


_SESSIONS: dict[str, ConversationState] = {}


def get_or_create_session(session_id: str) -> ConversationState:
    if session_id not in _SESSIONS:
        _SESSIONS[session_id] = ConversationState()
    return _SESSIONS[session_id]


def reset_session(session_id: str) -> None:
    _SESSIONS.pop(session_id, None)

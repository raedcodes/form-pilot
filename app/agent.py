from app.llm import (
    run_clarification_step,
    run_design_step,
    run_edit_step,
    run_quality_check_step,
)
from app.models import FormPlan, QualityReport
from app.session_store import get_or_create_session

MAX_CLARIFICATION_ROUNDS = 2
MAX_UNDO_HISTORY = 20
SECONDS_PER_QUESTION = 15


class AgentError(Exception):
    pass


def _push_undo(state) -> None:
    if state.plan is not None:
        state.undo_stack.append(state.plan)
        if len(state.undo_stack) > MAX_UNDO_HISTORY:
            state.undo_stack.pop(0)
    state.redo_stack.clear()


def _status_fields(state) -> dict:
    return {"can_undo": bool(state.undo_stack), "can_redo": bool(state.redo_stack)}


def handle_user_message(
    session_id: str,
    message: str,
    language: str = "English",
    tone: str = "neutral and professional",
) -> dict:
    state = get_or_create_session(session_id)

    if state.awaiting_confirmation and state.plan is not None:
        _push_undo(state)
        updated_plan = run_edit_step(state.plan, message, language, tone)
        state.plan = updated_plan
        return {
            "type": "preview",
            "plan": updated_plan,
            "assumptions": state.assumptions,
            "edited": True,
            **_status_fields(state),
        }

    state.conversation.append({"role": "user", "content": message})

    round_number = state.clarification_rounds + 1
    decision = run_clarification_step(
        state.conversation, round_number, MAX_CLARIFICATION_ROUNDS
    )

    if decision.status == "need_clarification" and round_number <= MAX_CLARIFICATION_ROUNDS:
        state.clarification_rounds += 1
        state.conversation.append({"role": "model", "content": decision.question})
        return {"type": "clarification", "question": decision.question}

    # Either the model decided it has enough, or the round cap forced it to stop
    # asking. If it ignored the cap and asked anyway, we override it here rather
    # than looping — the hard cap is enforced in code, not just by the prompt.
    assumptions = decision.assumptions if decision.status == "ready" else []
    state.assumptions = assumptions
    _push_undo(state)
    plan = run_design_step(state.conversation, assumptions, language, tone)
    state.plan = plan
    state.awaiting_confirmation = True
    return {
        "type": "preview",
        "plan": plan,
        "assumptions": assumptions,
        "edited": False,
        **_status_fields(state),
    }


def confirm_plan(session_id: str) -> FormPlan:
    state = get_or_create_session(session_id)
    if not state.awaiting_confirmation or state.plan is None:
        raise AgentError("No form plan is awaiting confirmation for this session")
    return state.plan


def cancel_preview(session_id: str) -> None:
    state = get_or_create_session(session_id)
    state.awaiting_confirmation = False
    state.plan = None
    state.undo_stack.clear()
    state.redo_stack.clear()


def apply_manual_edit(session_id: str, plan: FormPlan) -> dict:
    state = get_or_create_session(session_id)
    _push_undo(state)
    state.plan = plan
    state.awaiting_confirmation = True
    return {"plan": state.plan, **_status_fields(state)}


def undo_plan(session_id: str) -> dict:
    state = get_or_create_session(session_id)
    if not state.undo_stack:
        raise AgentError("Nothing to undo")
    if state.plan is not None:
        state.redo_stack.append(state.plan)
    state.plan = state.undo_stack.pop()
    return {"plan": state.plan, **_status_fields(state)}


def redo_plan(session_id: str) -> dict:
    state = get_or_create_session(session_id)
    if not state.redo_stack:
        raise AgentError("Nothing to redo")
    if state.plan is not None:
        state.undo_stack.append(state.plan)
    state.plan = state.redo_stack.pop()
    return {"plan": state.plan, **_status_fields(state)}


def run_quality_check(session_id: str) -> QualityReport:
    state = get_or_create_session(session_id)
    if state.plan is None:
        raise AgentError("No form plan to check")

    assessment = run_quality_check_step(state.plan)
    question_count = len(state.plan.questions)
    return QualityReport(
        clarity_score=assessment.clarity_score,
        estimated_minutes=round(question_count * SECONDS_PER_QUESTION / 60, 1),
        question_count=question_count,
        issues=assessment.issues,
        suggestions=assessment.suggestions,
    )

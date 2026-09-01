from app.llm import run_clarification_step, run_design_step, run_edit_step
from app.models import FormPlan
from app.session_store import get_or_create_session

MAX_CLARIFICATION_ROUNDS = 2


class AgentError(Exception):
    pass


def handle_user_message(session_id: str, message: str) -> dict:
    state = get_or_create_session(session_id)

    if state.awaiting_confirmation and state.plan is not None:
        updated_plan = run_edit_step(state.plan, message)
        state.plan = updated_plan
        return {
            "type": "preview",
            "plan": updated_plan,
            "assumptions": state.assumptions,
            "edited": True,
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
    plan = run_design_step(state.conversation, assumptions)
    state.plan = plan
    state.awaiting_confirmation = True
    return {"type": "preview", "plan": plan, "assumptions": assumptions, "edited": False}


def confirm_plan(session_id: str) -> FormPlan:
    state = get_or_create_session(session_id)
    if not state.awaiting_confirmation or state.plan is None:
        raise AgentError("No form plan is awaiting confirmation for this session")
    return state.plan


def cancel_preview(session_id: str) -> None:
    state = get_or_create_session(session_id)
    state.awaiting_confirmation = False
    state.plan = None

from app.llm import get_agent_response
from app.models import FormPlan
from app.session_store import ConversationState, get_or_create_session

MAX_CLARIFICATION_ROUNDS = 2

FORCE_READY_NOTICE = (
    "You have already used your 2 clarification rounds. You must respond with "
    'status "ready" now, making reasonable assumptions for anything still unclear.'
)


class AgentError(Exception):
    pass


def handle_user_message(session_id: str, message: str) -> dict:
    state = get_or_create_session(session_id)
    state.conversation.append({"role": "user", "content": message})

    rounds_exhausted = state.clarification_rounds >= MAX_CLARIFICATION_ROUNDS
    if rounds_exhausted:
        state.conversation.append({"role": "user", "content": FORCE_READY_NOTICE})

    response = get_agent_response(state.conversation)

    if response.status == "need_clarification":
        if rounds_exhausted:
            # The model ignored the hard cap; force it once more instead of
            # looping forever or silently dropping the question on the floor.
            state.conversation.append(
                {"role": "model", "content": response.model_dump_json()}
            )
            state.conversation.append({"role": "user", "content": FORCE_READY_NOTICE})
            response = get_agent_response(state.conversation)
            if response.status == "need_clarification":
                raise AgentError(
                    "LLM would not produce a plan after clarification rounds "
                    "were exhausted"
                )
        else:
            state.clarification_rounds += 1
            state.conversation.append(
                {"role": "model", "content": response.model_dump_json()}
            )
            return {"type": "clarification", "question": response.question}

    state.plan = response.plan
    state.awaiting_confirmation = True
    state.conversation.append({"role": "model", "content": response.model_dump_json()})
    return {"type": "preview", "plan": response.plan}


def confirm_plan(session_id: str) -> FormPlan:
    state = get_or_create_session(session_id)
    if not state.awaiting_confirmation or state.plan is None:
        raise AgentError("No form plan is awaiting confirmation for this session")
    return state.plan

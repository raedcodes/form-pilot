import os

from dotenv import load_dotenv
from google import genai
from pydantic import TypeAdapter, ValidationError

from app.models import ClarificationDecision, FormPlan

load_dotenv()

_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
_model = "gemini-flash-lite-latest"

_clarification_adapter = TypeAdapter(ClarificationDecision)
_plan_adapter = TypeAdapter(FormPlan)


class LLMOutputError(Exception):
    pass


CLARIFICATION_SYSTEM_PROMPT_TEMPLATE = """You are the clarification stage of a \
form-building agent. Your only job is to decide whether you have enough information \
to design a good form for the user's request, and if not, ask exactly one question.

Rules:
- Never ask about anything already stated or reasonably implied by the conversation.
- Never ask about cosmetic details (colors, title wording, branding, form theme) \
— those are not your concern.
- This is clarification round {round_number} of at most {max_rounds}.
- If this is the final allowed round, OR you already have enough information, you \
MUST respond with status "ready" and list any assumptions you are making for \
anything still unclear (an empty list if there is nothing to assume).
- Otherwise, if genuinely important information is missing, respond with status \
"need_clarification" and ask exactly ONE question.

Respond with a single JSON object matching one of these two shapes, nothing else:
{{"status": "need_clarification", "question": "<your question>"}}
{{"status": "ready", "assumptions": ["<assumption 1>", "<assumption 2>", ...]}}"""


DESIGN_SYSTEM_PROMPT = """You are the design stage of a form-building agent. You are \
given the user's request, any clarifying question/answer exchanges, and a list of \
assumptions already agreed on. Produce a structured Google Form plan.

Rules:
- Never invent a question the user didn't ask for or imply.
- Question count should roughly match any stated time constraint: assume about 15 \
seconds per question (e.g. "under 2 minutes" ≈ 5-8 questions). If no time \
constraint is stated, default to a concise 5-8 questions covering the request.
- Pick the most appropriate type per question: LINEAR_SCALE for ratings, \
MULTIPLE_CHOICE for a single choice among a few options, DROPDOWN for a single \
choice among many options, CHECKBOXES for multi-select, SHORT_ANSWER for brief free \
text, PARAGRAPH for longer free text.
- Mark a question required only if the form's purpose would be undermined by it \
being skipped.

Respond with a single JSON object matching this shape, nothing else:
{"title": "<form title>", "description": "<short description, can be empty string>",
 "questions": [
     {"title": "<question text>", "type": "<QUESTION_TYPE>", "required": <bool>,
      "options": ["<opt1>", "<opt2>", ...],  // only for MULTIPLE_CHOICE/CHECKBOXES/DROPDOWN
      "scale_min": <int>, "scale_max": <int>}  // only for LINEAR_SCALE
 ]}

Valid question types: SHORT_ANSWER, PARAGRAPH, MULTIPLE_CHOICE, CHECKBOXES, DROPDOWN, \
LINEAR_SCALE. Only include "options" for choice-type questions, and only include \
"scale_min"/"scale_max" for LINEAR_SCALE questions."""


EDIT_SYSTEM_PROMPT = """You are the edit stage of a form-building agent. You are \
given the current form plan as JSON and an instruction describing a change the user \
wants. Apply ONLY the requested change and return the complete updated plan (every \
question, not just the changed one), leaving everything else exactly as it was.

Respond with a single JSON object matching this shape, nothing else:
{"title": "<form title>", "description": "<description>",
 "questions": [
     {"title": "<question text>", "type": "<QUESTION_TYPE>", "required": <bool>,
      "options": ["<opt1>", "<opt2>", ...],  // only for MULTIPLE_CHOICE/CHECKBOXES/DROPDOWN
      "scale_min": <int>, "scale_max": <int>}  // only for LINEAR_SCALE
 ]}

Valid question types: SHORT_ANSWER, PARAGRAPH, MULTIPLE_CHOICE, CHECKBOXES, DROPDOWN, \
LINEAR_SCALE."""


def _to_contents(conversation: list[dict[str, str]]) -> list[dict]:
    return [
        {"role": turn["role"], "parts": [{"text": turn["content"]}]}
        for turn in conversation
    ]


def _generate_validated(
    contents: list[dict], system_prompt: str, adapter: TypeAdapter, max_retries: int
):
    working = list(contents)
    last_error: str | None = None

    for attempt in range(max_retries + 1):
        if last_error:
            working.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                "Your last response did not match the required "
                                f"schema: {last_error}\n"
                                "Reply again with ONLY a JSON object matching the "
                                "required shape."
                            )
                        }
                    ],
                }
            )

        response = _client.models.generate_content(
            model=_model,
            contents=working,
            config={
                "system_instruction": system_prompt,
                "response_mime_type": "application/json",
            },
        )

        try:
            return adapter.validate_json(response.text)
        except ValidationError as e:
            last_error = str(e)
            working.append({"role": "model", "parts": [{"text": response.text}]})

    raise LLMOutputError(
        f"LLM failed to produce a valid response after {max_retries} retries: {last_error}"
    )


def run_clarification_step(
    conversation: list[dict[str, str]],
    round_number: int,
    max_rounds: int,
    max_retries: int = 2,
) -> ClarificationDecision:
    system_prompt = CLARIFICATION_SYSTEM_PROMPT_TEMPLATE.format(
        round_number=round_number, max_rounds=max_rounds
    )
    return _generate_validated(
        _to_contents(conversation), system_prompt, _clarification_adapter, max_retries
    )


def run_design_step(
    conversation: list[dict[str, str]],
    assumptions: list[str],
    max_retries: int = 2,
) -> FormPlan:
    contents = _to_contents(conversation)
    if assumptions:
        assumptions_text = "\n".join(f"- {a}" for a in assumptions)
        contents.append(
            {
                "role": "user",
                "parts": [{"text": f"Assumptions to use:\n{assumptions_text}"}],
            }
        )
    return _generate_validated(contents, DESIGN_SYSTEM_PROMPT, _plan_adapter, max_retries)


def run_edit_step(
    plan: FormPlan, instruction: str, max_retries: int = 2
) -> FormPlan:
    contents = [
        {
            "role": "user",
            "parts": [
                {
                    "text": (
                        f"Current plan:\n{plan.model_dump_json()}\n\n"
                        f"Requested change: {instruction}"
                    )
                }
            ],
        }
    ]
    return _generate_validated(contents, EDIT_SYSTEM_PROMPT, _plan_adapter, max_retries)

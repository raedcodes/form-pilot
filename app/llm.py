import os

from dotenv import load_dotenv
from google import genai
from pydantic import TypeAdapter, ValidationError

from app.models import AgentResponse

load_dotenv()

_client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
_model = "gemini-3.6-flash"
_agent_response_adapter = TypeAdapter(AgentResponse)

SYSTEM_PROMPT = """You are a form-building assistant. The user describes a form/survey \
they want. Your job is to gather just enough information to design it well, then hand \
back a structured plan.

Always respond with a single JSON object matching one of these two shapes, nothing else:

1. If important information is missing, ask ONE clarifying question:
   {"status": "need_clarification", "question": "<your question>"}

2. Once you have enough information, produce the form plan:
   {"status": "ready", "plan": {
       "title": "<form title>",
       "description": "<short description, can be empty string>",
       "questions": [
           {"title": "<question text>", "type": "<QUESTION_TYPE>", "required": <bool>,
            "options": ["<opt1>", "<opt2>", ...],  // only for MULTIPLE_CHOICE/CHECKBOXES/DROPDOWN
            "scale_min": <int>, "scale_max": <int>}  // only for LINEAR_SCALE
       ]
   }}

Valid question types: SHORT_ANSWER, PARAGRAPH, MULTIPLE_CHOICE, CHECKBOXES, DROPDOWN, \
LINEAR_SCALE. Only include "options" for choice-type questions, and only include \
"scale_min"/"scale_max" for LINEAR_SCALE questions.

You get AT MOST 2 rounds of clarifying questions. If you have already asked 2 \
clarifying questions in this conversation, you MUST respond with status "ready" this \
time, making reasonable assumptions for anything still unclear."""


class LLMOutputError(Exception):
    pass


def get_agent_response(
    conversation: list[dict[str, str]], max_retries: int = 2
) -> AgentResponse:
    contents = [
        {"role": turn["role"], "parts": [{"text": turn["content"]}]}
        for turn in conversation
    ]

    last_error: str | None = None
    for attempt in range(max_retries + 1):
        if last_error:
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                "Your last response did not match the required "
                                f"schema: {last_error}\n"
                                "Reply again with ONLY a JSON object matching one of "
                                "the two shapes described in the system prompt."
                            )
                        }
                    ],
                }
            )

        response = _client.models.generate_content(
            model=_model,
            contents=contents,
            config={
                "system_instruction": SYSTEM_PROMPT,
                "response_mime_type": "application/json",
            },
        )

        try:
            return _agent_response_adapter.validate_json(response.text)
        except ValidationError as e:
            last_error = str(e)
            contents.append({"role": "model", "parts": [{"text": response.text}]})

    raise LLMOutputError(
        f"LLM failed to produce a valid response after {max_retries} retries: {last_error}"
    )

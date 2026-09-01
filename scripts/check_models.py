import json

from pydantic import TypeAdapter, ValidationError

from app.models import AgentResponse

agent_response_adapter = TypeAdapter(AgentResponse)

CASES = [
    (
        "valid clarifying question",
        {"status": "need_clarification", "question": "Should responses be anonymous?"},
        True,
    ),
    (
        "valid ready plan",
        {
            "status": "ready",
            "plan": {
                "title": "Restaurant Satisfaction Survey",
                "description": "Quick feedback, takes under 2 minutes.",
                "questions": [
                    {
                        "title": "How would you rate the food quality?",
                        "type": "LINEAR_SCALE",
                        "required": True,
                        "scale_min": 1,
                        "scale_max": 5,
                    },
                    {
                        "title": "What did you order?",
                        "type": "SHORT_ANSWER",
                        "required": False,
                    },
                    {
                        "title": "Which areas could we improve?",
                        "type": "CHECKBOXES",
                        "required": False,
                        "options": ["Food", "Service", "Price", "Ambiance"],
                    },
                ],
            },
        },
        True,
    ),
    (
        "invalid: choice question missing options",
        {
            "status": "ready",
            "plan": {
                "title": "Survey",
                "questions": [
                    {"title": "Pick one", "type": "MULTIPLE_CHOICE", "required": True}
                ],
            },
        },
        False,
    ),
    (
        "invalid: unknown status",
        {"status": "done", "plan": {}},
        False,
    ),
    (
        "invalid: empty questions list",
        {
            "status": "ready",
            "plan": {"title": "Survey", "questions": []},
        },
        False,
    ),
]

if __name__ == "__main__":
    failures = 0
    for name, payload, should_pass in CASES:
        try:
            agent_response_adapter.validate_python(payload)
            passed = True
            detail = ""
        except ValidationError as e:
            passed = False
            detail = str(e).splitlines()[0]

        ok = passed == should_pass
        status = "OK" if ok else "MISMATCH"
        print(f"[{status}] {name}: validated={passed} expected={should_pass} {detail}")
        if not ok:
            failures += 1

    print()
    if failures:
        print(f"{failures} case(s) did not behave as expected")
    else:
        print("All cases behaved as expected")

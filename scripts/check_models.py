from pydantic import TypeAdapter, ValidationError

from app.models import ClarificationDecision, FormPlan

clarification_adapter = TypeAdapter(ClarificationDecision)
plan_adapter = TypeAdapter(FormPlan)

CLARIFICATION_CASES = [
    (
        "valid need_clarification",
        {"status": "need_clarification", "question": "Should responses be anonymous?"},
        True,
    ),
    (
        "valid ready with assumptions",
        {
            "status": "ready",
            "assumptions": ["Responses are anonymous", "Audience is adult customers"],
        },
        True,
    ),
    (
        "valid ready with no assumptions",
        {"status": "ready", "assumptions": []},
        True,
    ),
    (
        "invalid: unknown status",
        {"status": "done"},
        False,
    ),
    (
        "invalid: need_clarification missing question",
        {"status": "need_clarification"},
        False,
    ),
]

PLAN_CASES = [
    (
        "valid plan",
        {
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
            ],
        },
        True,
    ),
    (
        "invalid: choice question missing options",
        {
            "title": "Survey",
            "questions": [
                {"title": "Pick one", "type": "MULTIPLE_CHOICE", "required": True}
            ],
        },
        False,
    ),
    (
        "invalid: empty questions list",
        {"title": "Survey", "questions": []},
        False,
    ),
]


def run(name, payload, should_pass, adapter):
    try:
        adapter.validate_python(payload)
        passed = True
        detail = ""
    except ValidationError as e:
        passed = False
        detail = str(e).splitlines()[0]

    ok = passed == should_pass
    status = "OK" if ok else "MISMATCH"
    print(f"[{status}] {name}: validated={passed} expected={should_pass} {detail}")
    return ok


if __name__ == "__main__":
    results = [run(n, p, s, clarification_adapter) for n, p, s in CLARIFICATION_CASES]
    results += [run(n, p, s, plan_adapter) for n, p, s in PLAN_CASES]

    print()
    failures = results.count(False)
    if failures:
        print(f"{failures} case(s) did not behave as expected")
    else:
        print("All cases behaved as expected")

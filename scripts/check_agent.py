import json

from app.agent import confirm_plan, handle_user_message

session_id = "check-agent-session"

turns = [
    "I need a form.",
    "Something for feedback I guess.",
    "Sure, keep it short and anonymous.",
]

result = None
for i, message in enumerate(turns, start=1):
    print(f"--- turn {i}: user says: {message!r} ---")
    result = handle_user_message(session_id, message)
    if result["type"] == "clarification":
        print(f"agent asks: {result['question']}")
    else:
        print(f"agent produced a plan. assumptions: {result['assumptions']}")
        print(json.dumps(result["plan"].model_dump(), indent=2))
        break
    print()

if result and result["type"] == "preview":
    print()
    print("--- confirming plan ---")
    plan = confirm_plan(session_id)
    print(f"confirmed plan title: {plan.title!r}, {len(plan.questions)} question(s)")

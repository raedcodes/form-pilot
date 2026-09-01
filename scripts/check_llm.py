import json

from app.llm import run_clarification_step, run_design_step

print("--- Case 1: vague request, expect need_clarification ---")
conversation = [
    {
        "role": "user",
        "content": "I need a customer satisfaction survey for a restaurant. It should "
        "take less than 2 minutes to complete.",
    }
]
decision = run_clarification_step(conversation, round_number=1, max_rounds=2)
print(decision)

print()
print("--- Case 2: fully detailed request, expect ready with assumptions ---")
conversation = [
    {
        "role": "user",
        "content": (
            "I need a customer satisfaction survey for a restaurant. It should take "
            "less than 2 minutes. Measure food quality, service, price, and overall "
            "experience, each on a rating scale. Responses should be anonymous. Add "
            "one optional open-ended comment field at the end."
        ),
    }
]
decision = run_clarification_step(conversation, round_number=1, max_rounds=2)
print(decision)

print()
print("--- Case 3: design step from case 2's conversation + assumptions ---")
assumptions = decision.assumptions if decision.status == "ready" else []
plan = run_design_step(conversation, assumptions)
print(json.dumps(plan.model_dump(), indent=2))

print()
print("--- Case 4: forced final round (round_number > max_rounds) ---")
vague_conversation = [{"role": "user", "content": "I need a form."}]
decision = run_clarification_step(vague_conversation, round_number=3, max_rounds=2)
print(decision)

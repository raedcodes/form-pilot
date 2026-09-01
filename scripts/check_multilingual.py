import json

from app.llm import run_design_step

print("--- Arabic, friendly tone ---")
conversation = [
    {
        "role": "user",
        "content": "I need a short customer feedback form for a coffee shop. Ratings "
        "for coffee quality and staff friendliness. Keep it under 1 minute.",
    }
]
plan = run_design_step(conversation, assumptions=[], language="Arabic", tone="friendly")
print(json.dumps(plan.model_dump(), indent=2, ensure_ascii=False))

print()
print("--- French, formal tone ---")
plan = run_design_step(conversation, assumptions=[], language="French", tone="formal")
print(json.dumps(plan.model_dump(), indent=2, ensure_ascii=False))

import json

from app.llm import get_agent_response

print("--- Case 1: vague request, expect a clarifying question ---")
conversation = [
    {
        "role": "user",
        "content": "I need a customer satisfaction survey for a restaurant. It should "
        "take less than 2 minutes to complete.",
    }
]
result = get_agent_response(conversation)
print(result)

print()
print("--- Case 2: detailed request, expect a ready plan ---")
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
result = get_agent_response(conversation)
if result.status == "ready":
    print(json.dumps(result.plan.model_dump(), indent=2))
else:
    print(result)

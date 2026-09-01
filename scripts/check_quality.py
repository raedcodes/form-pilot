import json

from app.llm import run_quality_check_step
from app.models import FormPlan

plan = FormPlan(
    title="Customer Feedback",
    description="",
    questions=[
        {
            "title": "How satisfied are you with our service?",
            "type": "LINEAR_SCALE",
            "required": True,
            "scale_min": 1,
            "scale_max": 5,
        },
        {
            "title": "Rate your satisfaction with the service you received",
            "type": "LINEAR_SCALE",
            "required": True,
            "scale_min": 1,
            "scale_max": 5,
        },
        {
            "title": "Tell us your age",
            "type": "PARAGRAPH",
            "required": True,
        },
        {
            "title": "What is your name",
            "type": "SHORT_ANSWER",
            "required": True,
        },
        {
            "title": "Any other comments?",
            "type": "PARAGRAPH",
            "required": True,
        },
    ],
)

assessment = run_quality_check_step(plan)
print(json.dumps(assessment.model_dump(), indent=2))

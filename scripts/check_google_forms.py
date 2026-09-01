from app.google_forms import create_google_form
from app.models import FormPlan, Question

plan = FormPlan(
    title="form-pilot test form",
    description="Created by the form-pilot verification script.",
    questions=[
        Question(title="Your name", type="SHORT_ANSWER", required=True),
        Question(
            title="How satisfied are you?",
            type="LINEAR_SCALE",
            required=True,
            scale_min=1,
            scale_max=5,
        ),
        Question(
            title="Which features do you use?",
            type="CHECKBOXES",
            required=False,
            options=["Search", "Export", "Sharing"],
        ),
    ],
)

url = create_google_form(plan)
print(f"Form created: {url}")

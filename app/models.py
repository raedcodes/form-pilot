from enum import Enum
from typing import Annotated, Literal, Union

from pydantic import BaseModel, Field, model_validator

CHOICE_TYPES = {"MULTIPLE_CHOICE", "CHECKBOXES", "DROPDOWN"}


class QuestionType(str, Enum):
    SHORT_ANSWER = "SHORT_ANSWER"
    PARAGRAPH = "PARAGRAPH"
    MULTIPLE_CHOICE = "MULTIPLE_CHOICE"
    CHECKBOXES = "CHECKBOXES"
    DROPDOWN = "DROPDOWN"
    LINEAR_SCALE = "LINEAR_SCALE"


class Question(BaseModel):
    title: str
    type: QuestionType
    required: bool
    options: list[str] | None = None
    scale_min: int | None = None
    scale_max: int | None = None

    @model_validator(mode="after")
    def check_type_specific_fields(self) -> "Question":
        if self.type.value in CHOICE_TYPES:
            if not self.options or len(self.options) < 2:
                raise ValueError(
                    f"{self.type.value} questions need at least 2 options"
                )
        elif self.options:
            raise ValueError(f"{self.type.value} questions must not have options")

        if self.type == QuestionType.LINEAR_SCALE:
            if self.scale_min is None or self.scale_max is None:
                raise ValueError("LINEAR_SCALE questions need scale_min and scale_max")
            if self.scale_min >= self.scale_max:
                raise ValueError("scale_min must be less than scale_max")
        elif self.scale_min is not None or self.scale_max is not None:
            raise ValueError("scale_min/scale_max only apply to LINEAR_SCALE questions")

        return self


class FormPlan(BaseModel):
    title: str
    description: str = ""
    questions: list[Question] = Field(min_length=1)


class NeedClarification(BaseModel):
    status: Literal["need_clarification"]
    question: str


class ClarificationReady(BaseModel):
    status: Literal["ready"]
    assumptions: list[str] = Field(default_factory=list)


ClarificationDecision = Annotated[
    Union[NeedClarification, ClarificationReady], Field(discriminator="status")
]

from pathlib import Path

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from app.models import FormPlan, Question

SCOPES = ["https://www.googleapis.com/auth/forms.body"]
CREDENTIALS_DIR = Path(__file__).resolve().parent.parent / "credentials"
CLIENT_SECRET_FILE = CREDENTIALS_DIR / "client_secret.json"
TOKEN_FILE = CREDENTIALS_DIR / "token.json"


class GoogleFormsError(Exception):
    pass


def get_credentials() -> Credentials:
    creds: Credentials | None = None
    if TOKEN_FILE.exists():
        creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                str(CLIENT_SECRET_FILE), SCOPES
            )
            creds = flow.run_local_server(port=0)
        TOKEN_FILE.write_text(creds.to_json())

    return creds


def _question_to_item(question: Question, index: int) -> dict:
    item: dict = {
        "title": question.title,
        "questionItem": {
            "question": {
                "required": question.required,
            }
        },
    }
    q = item["questionItem"]["question"]

    if question.type == "SHORT_ANSWER":
        q["textQuestion"] = {"paragraph": False}
    elif question.type == "PARAGRAPH":
        q["textQuestion"] = {"paragraph": True}
    elif question.type == "MULTIPLE_CHOICE":
        q["choiceQuestion"] = {
            "type": "RADIO",
            "options": [{"value": o} for o in question.options],
        }
    elif question.type == "CHECKBOXES":
        q["choiceQuestion"] = {
            "type": "CHECKBOX",
            "options": [{"value": o} for o in question.options],
        }
    elif question.type == "DROPDOWN":
        q["choiceQuestion"] = {
            "type": "DROP_DOWN",
            "options": [{"value": o} for o in question.options],
        }
    elif question.type == "LINEAR_SCALE":
        q["scaleQuestion"] = {
            "low": question.scale_min,
            "high": question.scale_max,
        }
    else:
        raise GoogleFormsError(f"Unsupported question type: {question.type}")

    return {
        "createItem": {
            "item": item,
            "location": {"index": index},
        }
    }


def create_google_form(plan: FormPlan) -> str:
    try:
        creds = get_credentials()
        service = build("forms", "v1", credentials=creds)

        form = (
            service.forms()
            .create(body={"info": {"title": plan.title}})
            .execute()
        )
        form_id = form["formId"]

        requests = [
            {
                "updateFormInfo": {
                    "info": {"description": plan.description},
                    "updateMask": "description",
                }
            }
        ]
        requests += [
            _question_to_item(question, index)
            for index, question in enumerate(plan.questions)
        ]

        service.forms().batchUpdate(
            formId=form_id, body={"requests": requests}
        ).execute()

        updated_form = service.forms().get(formId=form_id).execute()
        return updated_form["responderUri"]

    except RefreshError as e:
        raise GoogleFormsError(
            "Google authorization expired or was revoked. Delete "
            "credentials/token.json and re-run the OAuth flow."
        ) from e
    except HttpError as e:
        raise GoogleFormsError(f"Google Forms API request failed: {e}") from e

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.agent import AgentError, cancel_preview, confirm_plan, handle_user_message
from app.google_forms import GoogleFormsError, create_google_form
from app.llm import LLMOutputError
from app.session_store import reset_session

app = FastAPI(title="form-pilot")


class ChatRequest(BaseModel):
    session_id: str
    message: str


class ConfirmRequest(BaseModel):
    session_id: str


class CancelRequest(BaseModel):
    session_id: str


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/chat")
def chat(req: ChatRequest):
    try:
        return handle_user_message(req.session_id, req.message)
    except LLMOutputError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except AgentError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.post("/confirm")
def confirm(req: ConfirmRequest):
    try:
        plan = confirm_plan(req.session_id)
    except AgentError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        url = create_google_form(plan)
    except GoogleFormsError as e:
        raise HTTPException(status_code=502, detail=str(e))

    reset_session(req.session_id)
    return {"url": url}


@app.post("/cancel")
def cancel(req: CancelRequest):
    cancel_preview(req.session_id)
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="frontend", html=True), name="frontend")

import os
from fastapi import APIRouter,FastAPI, HTTPException, Request
from app.auth import router as auth_router
from app.user import router as user_router
from app.gmail import fetch_unread_emails, fetch_and_classify_emails, send_reply_email
from app.agents.gmail_graph import run_gmail_assistant, email_graph_executor, EmailState
from pydantic import BaseModel
from typing import Dict

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

app = FastAPI()
app.include_router(auth_router)
app.include_router(user_router)
router = APIRouter()

class SendReplyRequest(BaseModel):
    recipient: str
    subject: str
    reply_body: str
    thread_id: str

@app.get("/emails/unread/{user_id}")
async def get_emails(user_id: str):
    try:
        emails = fetch_unread_emails(user_id)
        return {"emails": emails}
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/emails/classify/{user_id}")
async def classify_emails(user_id: str):
    try:
        classified = fetch_and_classify_emails(user_id)
        print(user_id)
        return {"classified_emails": classified}
    except Exception as e:
        return {"error": str(e)}
    
@app.post("/emails/send/{user_id}")
async def send_email(user_id: str, payload: SendReplyRequest):
    try:
        result = send_reply_email(
            user_id=user_id,
            to_email=payload.recipient,
            subject=payload.subject,
            reply_body=payload.reply_body,
            thread_id=payload.thread_id
        )
        return {"message": "Reply sent", "message_id": result.get("id")}
    except Exception as e:
        return {"error": str(e)}
    
@app.get("/agent/run/{user_id}")
async def run_agent(user_id: str):
    print("user_id received:", user_id)
    result = run_gmail_assistant(user_id)
    return {"message": "Agent run complete", "result": result}

@router.post("/agent/resume")
def resume_agent(state: Dict):
    try:
        result = email_graph_executor.resume(state)
        return {"message": "Agent resumed and completed", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


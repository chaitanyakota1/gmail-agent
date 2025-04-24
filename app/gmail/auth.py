import os
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse,JSONResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from app.gmail.secret_manager import get_user_tokens,save_user_tokens
from app.session_store import get_user_session,set_user_session
from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, GOOGLE_SCOPES
from uuid import uuid4
from pydantic import BaseModel
import logging
from datetime import datetime
from dateutil.parser import isoparse

logger = logging.getLogger(__name__)
router = APIRouter()

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'  # Needed for local http

class SignatureUpdateRequest(BaseModel):
    signature: str

def create_flow():
    return Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=GOOGLE_SCOPES,
        redirect_uri=GOOGLE_REDIRECT_URI,
    )

@router.get("/auth/login")
async def login(user_id:str = ""):
    flow = create_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    # manually store state as query param so callback can reuse it
    return RedirectResponse(auth_url)

@router.get("/auth/callback")
async def callback(request: Request):
    flow = create_flow()
    try:
        flow.fetch_token(authorization_response=str(request.url))
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Token fetch failed: {str(e)}"})

    creds = flow.credentials
    signature = get_gmail_signature(creds) or "Best regards,\n"
    user_info_service = build("oauth2", "v2", credentials=creds)
    user_info = user_info_service.userinfo().get().execute()
    user_email = user_info["email"]

    # Token save block
    try:
        save_user_tokens(user_email, {
            "access_token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_expiry": creds.expiry.isoformat(),
        }, signature=signature)
        logger.info(f"✅ Tokens saved for {user_email}")
    except Exception as e:
        logger.error(f" Failed to save tokens for {user_email}: {e}")
        return JSONResponse(status_code=500, content={"error": "Token storage failed."})
    return RedirectResponse(f"http://localhost:8501?user_id={user_email}&login=success")

@router.get("/auth/check/{user_id}")
def check_auth(user_id: str):
    tokens = get_user_tokens(user_id)
    if tokens and "access_token" in tokens:
        expiry = isoparse(tokens.get("token_expiry", ""))
        if expiry > datetime.utcnow():
            return {"valid": True}
    return {"valid": False}

def get_gmail_signature(creds):
    service = build("gmail", "v1", credentials=creds)
    results = service.users().settings().sendAs().list(userId="me").execute()
    send_as_list = results.get("sendAs", [])
    
    # Pick the primary send-as address
    for entry in send_as_list:
        if entry.get("isPrimary"):
            return entry.get("signature", "")

    return ""
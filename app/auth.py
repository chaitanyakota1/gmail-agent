import os
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse,JSONResponse
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from app.firestore import save_user_tokens,update_user_signature
from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, GOOGLE_SCOPES
from uuid import uuid4
from pydantic import BaseModel

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

def get_gmail_signature(creds):
    service = build("gmail", "v1", credentials=creds)
    results = service.users().settings().sendAs().list(userId="me").execute()
    send_as_list = results.get("sendAs", [])
    
    # Pick the primary send-as address
    for entry in send_as_list:
        if entry.get("isPrimary"):
            return entry.get("signature", "")

    return ""

@router.get("/auth/login")
async def login():
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
    # Rebuild flow and pass full URL back into it
    flow = create_flow()

    try:
        flow.fetch_token(authorization_response=str(request.url))
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

    creds = flow.credentials
    signature = get_gmail_signature(creds) or "Best regards,\n"
    # Use OAuth2 API to get user's email address
    user_info_service = build("oauth2", "v2", credentials=creds)
    user_info = user_info_service.userinfo().get().execute()
    user_email = user_info["email"]

    save_user_tokens(user_email, {
        "access_token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_expiry": creds.expiry.isoformat(),
    },signature=signature)

    return JSONResponse(content={"message": f"Login successful for {user_email}"})

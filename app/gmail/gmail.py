import os
import base64
import re
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from app.gmail.secret_manager import get_user_tokens
from app.config import GOOGLE_SCOPES
from app.llm_utils import classify_email, generate_reply
from email.mime.text import MIMEText
from email.utils import parseaddr
from datetime import datetime


def extract_plain_text(payload):
    if payload.get("mimeType") == "text/plain" and "data" in payload.get("body", {}):
        return base64.urlsafe_b64decode(payload["body"]["data"]).decode("utf-8")

    # Look inside parts (multi-part emails)
    for part in payload.get("parts", []):
        text = extract_plain_text(part)
        if text:
            return text
    return ""

def get_or_create_label(service, label_name):
    # Get existing labels
    labels_response = service.users().labels().list(userId="me").execute()
    labels = labels_response.get("labels", [])

    for label in labels:
        if label["name"] == label_name:
            return label["id"]

    # If label doesn't exist, create it
    new_label = {
        "name": label_name,
        "labelListVisibility": "labelShow",
        "messageListVisibility": "show"
    }
    label = service.users().labels().create(userId="me", body=new_label).execute()
    return label["id"]

def clean_email_body(body: str, max_chars=2000) -> str:
    if not body:
        return ""

    # Remove zero-width and non-breaking spaces
    body = body.replace('\u200c', ' ').replace('\xa0', ' ')

    # Normalize line endings and remove excessive \r
    body = body.replace('\r\n', '\n').replace('\r', '\n')

    # Remove repeated blank lines
    body = re.sub(r'\n{2,}', '\n\n', body)

    # Collapse excessive space
    body = re.sub(r'[ \t]{2,}', ' ', body)

    # Strip HTML-style "VIEW JOB", "SIGN IN", "CLICK HERE", "UPDATE", etc.
    body = re.sub(r'\b(VIEW JOB|SIGN IN|CLICK HERE|VIEW ALL JOBS|LOGIN|UPDATE).*', '', body, flags=re.IGNORECASE)

    # Remove common footer lines
    footer_keywords = [
        r'this email was sent to',
        r'unsubscribe',
        r'manage your .* preferences',
        r'privacy policy',
        r'copyright',
        r'©.*monster',
        r'monster worldwide',
        r'contact us',
        r'terms & conditions'
    ]
    for kw in footer_keywords:
        body = re.sub(kw + r'.*', '', body, flags=re.IGNORECASE)

    # Remove any remaining URLs
    body = re.sub(r'https?://\S+', '', body)

    # Remove any lines that are mostly filler characters
    body = re.sub(r'^[\s\|\-_=]{4,}$', '', body, flags=re.MULTILINE)

    # Trim the result
    clean = body.strip()

    return clean[:max_chars]

def get_gmail_service(user_id: str):
    tokens = get_user_tokens(user_id)
    signature = tokens.get("signature", "Best regards,\n")
    if not tokens:
        raise Exception("User tokens not found.")
    
    token_expiry = tokens.get("token_expiry")
    if isinstance(token_expiry, str):
        token_expiry = datetime.fromisoformat(token_expiry)

    creds = Credentials(
        token=tokens["access_token"],
        refresh_token=tokens["refresh_token"],
        token_uri="https://oauth2.googleapis.com/token",
        client_id=os.getenv("GOOGLE_CLIENT_ID"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
        scopes=GOOGLE_SCOPES,
        expiry=token_expiry
    )

    return build("gmail", "v1", credentials=creds)


def fetch_unread_emails(user_id: str, max_results: int = 5):
    service = get_gmail_service(user_id)

    response = service.users().messages().list(
        userId='me',
        labelIds=['UNREAD'],
        maxResults=max_results
    ).execute()

    messages = response.get("messages", [])
    results = []

    for msg in messages:
        detail = service.users().messages().get(userId="me", id=msg["id"],format='full').execute()
        headers = detail["payload"]["headers"]
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(No Subject)")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "(Unknown Sender)")
        snippet = detail.get("snippet", "")

        body = extract_plain_text(detail["payload"])
        if not body:
            body = snippet
        
        cleaned_body = clean_email_body(body)

        results.append({
            "id": msg["id"],
            "threadId": msg["threadId"],
            "from": sender,
            "subject": subject,
            "snippet": snippet,
            "body": cleaned_body
        })

    return results

def fetch_and_classify_emails(user_id: str, max_results: int = 3):
    service = get_gmail_service(user_id)
    tokens = get_user_tokens(user_id)
    signature = tokens.get("signature", "Best regards,\n")

    response = service.users().messages().list(
        userId='me', labelIds=['UNREAD'], maxResults=max_results
    ).execute()

    messages = response.get("messages", [])
    results = []

    for msg in messages:
        detail = service.users().messages().get(userId="me", id=msg["id"],format='full').execute()

        headers = detail["payload"]["headers"]
        subject = next((h["value"] for h in headers if h["name"] == "Subject"), "(No Subject)")
        sender = next((h["value"] for h in headers if h["name"] == "From"), "(Unknown Sender)")
        snippet = detail.get("snippet", "")

        # 🔍 Extract full plain text body
        body = extract_plain_text(detail["payload"])
        if not body:
            body = snippet

        cleaned_body = clean_email_body(body)

        classification = classify_email(sender, subject, body)
        reply = None
        if classification in ["RESPONSE_NEEDED", "IMMEDIATE_RESPONSE"]:
            reply = generate_reply(sender, subject, snippet,signature)

        results.append({
            "id": msg["id"],
            "threadId": msg["threadId"],
            "from": sender,
            "subject": subject,
            "snippet": snippet,
            "body": cleaned_body,
            "classification": classification,
            "suggested_reply": reply
        })

    return results

def send_reply_email(user_id: str, to_email: str, subject: str, reply_body: str, thread_id: str):
    service = get_gmail_service(user_id)

    message = MIMEText(reply_body)
    name, email = parseaddr(to_email)

    message["to"] = email
    message["subject"] = f"Re: {subject}"
    message["from"] = "me"

    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    message = {
        "raw": raw,
        "threadId": thread_id,
    }

    sent = service.users().messages().send(userId="me", body=message).execute()

    # --- Mark the thread as read ---
    service.users().threads().modify(
        userId="me",
        id=thread_id,
        body={"removeLabelIds": ["UNREAD"]}
    ).execute()

    # --- Add custom label ---
    label_id = get_or_create_label(service, "GMAIL_ASSISTANT")
    service.users().threads().modify(
        userId="me",
        id=thread_id,
        body={"addLabelIds": [label_id]}
    ).execute()

    return sent

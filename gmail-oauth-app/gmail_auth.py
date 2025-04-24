import os
import pickle
import json
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

# If modifying these SCOPES, delete token.json
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def authenticate_gmail():
    creds = None

    # Load token if it exists
    if os.path.exists("token.json"):
        with open("token.json", "r") as token:
            creds_data = json.load(token)
        # creds = Request().from_authorized_user_info(creds_data, SCOPES)
        creds = Credentials.from_authorized_user_info(info=creds_data,scopes=SCOPES)

    # If no valid creds, login
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("client_secret.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    service = build('gmail', 'v1', credentials=creds)
    return service

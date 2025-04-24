#%%
import os
from dotenv import load_dotenv
load_dotenv()

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")
GOOGLE_SCOPES = os.getenv("GOOGLE_SCOPES", "").split(",")
FIREBASE_CREDENTIALS = os.getenv("FIREBASE_CREDENTIALS", "firebase-key.json")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")


# %%

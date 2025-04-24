#%%
from google.cloud import firestore
from app.config import FIREBASE_CREDENTIALS

db = firestore.Client.from_service_account_json(FIREBASE_CREDENTIALS)


def save_user_tokens(user_id, tokens, signature="Best regards"):
    doc_ref = db.collection("users").document(user_id)
    doc_ref.set({**tokens, "signature": signature})

def get_user_tokens(user_id):
    doc_ref = db.collection("users").document(user_id)
    doc = doc_ref.get()
    print(doc.to_dict())
    return doc.to_dict() if doc.exists else None


def update_user_signature(user_id: str, signature: str):
    doc_ref = db.collection("users").document(user_id)
    doc_ref.update({"signature": signature})

# %%

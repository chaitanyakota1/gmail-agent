#%%
import os
import re
import json
from google.cloud import secretmanager
from dotenv import load_dotenv

load_dotenv()

secret_client = secretmanager.SecretManagerServiceClient()
project_id = os.getenv("GCP_PROJECT_ID")
#%%
def _get_secret_name(user_id):
    return f"projects/{project_id}/secrets/user-tokens-{user_id}"

def save_user_tokens(user_id, tokens, signature="Best regards"):
    payload = json.dumps({**tokens, "signature": signature})
    print(f"🔐 Payload being saved: {payload}")

    parent = f"projects/{project_id}"
    print(parent)
    safe_user_id = re.sub(r'[^a-zA-Z0-9_-]', '_', user_id)
    secret_id = f"user_tokens_{safe_user_id}"
    print(secret_id)
    secret_name = f"{parent}/secrets/{secret_id}"
    print(secret_name)

    # Create the secret if it doesn't exist
    try:
        secret_client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": {
                    "replication": {"automatic": {}}
                },
            }
        )
        print(f"✅ Secret created for {user_id}")
    except Exception as e:
        if "already exists" not in str(e):
            raise e  # Only ignore 'already exists' errors

    # Add a new version with the token payload
    secret_client.add_secret_version(
        request={
            "parent": secret_name,
            "payload": {"data": payload.encode("UTF-8")}
        }
    )
    print(f"✅ Tokens saved to Secret Manager for {user_id}")

def get_user_tokens(user_id):

    secret_client = secretmanager.SecretManagerServiceClient()
    safe_user_id = user_id.replace('@', '_').replace('.', '_')
    secret_name = f"projects/{project_id}/secrets/user_tokens_{safe_user_id}/versions/latest"

    try:
        response = secret_client.access_secret_version(request={"name": secret_name})
        payload = response.payload.data.decode("UTF-8")
        return json.loads(payload)
    except Exception as e:
        print(f"❌ Error retrieving secret for {user_id}: {e}")
        return None
# app/session_store.py
#%%
import redis
import json
from datetime import timedelta

# Initialize Redis client
r = redis.Redis(
    host="10.246.34.35",  
    port=6379,
    decode_responses=True  
)

# Set session (expires in 10 min)
def set_user_session(user_id: str, state: dict):
    key = f"session:{user_id}"
    r.setex(key, timedelta(minutes=10), json.dumps(state))
#%%
# Get session
def get_user_session(user_id: str):
    key = f"session:{user_id}"
    data = r.get(key)
    return json.loads(data) if data else None

# Delete session
def delete_user_session(user_id: str):
    key = f"session:{user_id}"
    r.delete(key)

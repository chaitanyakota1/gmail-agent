from fastapi import APIRouter
from pydantic import BaseModel
from app.firestore import update_user_signature

router = APIRouter()

class SignatureUpdateRequest(BaseModel):
    signature: str

@router.put("/users/{user_id}/signature")
async def update_signature(user_id: str, request: SignatureUpdateRequest):
    update_user_signature(user_id, request.signature)
    return {"message": f"Signature updated for {user_id}"}
"""TICKR — Profile API routes"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.auth.jwt import get_current_user

router = APIRouter(prefix="/api/profile", tags=["profile"])


class UpdateProfileReq(BaseModel):
    full_name: str | None = None
    email: str | None = None


@router.get("")
def get_profile(current_user: User = Depends(get_current_user)):
    return {
        "id": current_user.id,
        "username": current_user.username,
        "full_name": current_user.full_name,
        "email": current_user.email,
        "avatar_initials": current_user.avatar_initials,
        "created_at": current_user.created_at.isoformat(),
    }


@router.put("")
def update_profile(req: UpdateProfileReq, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current_user.id).first()
    if req.full_name:
        user.full_name = req.full_name
        user.avatar_initials = "".join(w[0].upper() for w in req.full_name.split()[:2])
    if req.email:
        user.email = req.email
    db.commit()
    return {"ok": True, "full_name": user.full_name, "avatar_initials": user.avatar_initials}

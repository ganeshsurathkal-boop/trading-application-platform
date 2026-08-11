"""TICKR — Auth routes (login, register, refresh-token)"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.user import User
from app.auth.jwt import hash_password, verify_password, create_access_token
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    username: str
    email: str
    full_name: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


@router.post("/register", status_code=201)
def register(req: RegisterRequest, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == req.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.query(User).filter(User.email == req.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    initials = "".join(w[0].upper() for w in req.full_name.split()[:2])
    user = User(
        username=req.username,
        email=req.email,
        full_name=req.full_name,
        hashed_password=hash_password(req.password),
        avatar_initials=initials,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    token = create_access_token({"sub": user.username})
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "username": user.username, "full_name": user.full_name,
              "email": user.email, "avatar_initials": user.avatar_initials}
    )


@router.post("/login", response_model=TokenResponse)
def login(form: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form.username).first()
    if not user or not verify_password(form.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
    token = create_access_token({"sub": user.username})
    return TokenResponse(
        access_token=token,
        user={"id": user.id, "username": user.username, "full_name": user.full_name,
              "email": user.email, "avatar_initials": user.avatar_initials}
    )

"""Registration and JWT authentication endpoints."""

from datetime import UTC, datetime

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    password_hash,
    verify_password,
)
from app.models import RefreshToken, User

router = APIRouter(prefix="/auth", tags=["auth"])
bearer_scheme = HTTPBearer()


class Credentials(BaseModel):
    email: str = Field(min_length=3, max_length=320)
    password: str = Field(min_length=8, max_length=128)


class RefreshRequest(BaseModel):
    refresh_token: str = Field(min_length=1)


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


def _normalise_email(email: str) -> str:
    value = email.strip().lower()
    if "@" not in value:
        raise HTTPException(status_code=422, detail="email must be a valid email address")
    return value


def _issue_tokens(db: Session, user: User) -> TokenPair:
    refresh_token, token_id, expires_at = create_refresh_token(user.id)
    db.add(
        RefreshToken(
            id=token_id,
            user_id=user.id,
            token_hash=hash_password(refresh_token),
            expires_at=expires_at,
        )
    )
    db.commit()
    return TokenPair(access_token=create_access_token(user.id), refresh_token=refresh_token)


@router.post("/register", response_model=TokenPair, status_code=status.HTTP_201_CREATED)
def register(credentials: Credentials, db: Session = Depends(get_db)) -> TokenPair:
    email = _normalise_email(credentials.email)
    if db.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status_code=409, detail="email is already registered")
    user = User(email=email, password_hash=hash_password(credentials.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return _issue_tokens(db, user)


@router.post("/login", response_model=TokenPair)
def login(credentials: Credentials, db: Session = Depends(get_db)) -> TokenPair:
    user = db.scalar(select(User).where(User.email == _normalise_email(credentials.email)))
    if user is None or not verify_password(credentials.password, user.password_hash):
        raise HTTPException(status_code=401, detail="invalid email or password")
    return _issue_tokens(db, user)


@router.post("/refresh", response_model=TokenPair)
def refresh(request: RefreshRequest, db: Session = Depends(get_db)) -> TokenPair:
    try:
        payload = decode_token(request.refresh_token, "refresh")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="invalid refresh token") from None

    stored_token = db.get(RefreshToken, payload["jti"])
    if (
        stored_token is None
        or stored_token.user_id != payload["sub"]
        or stored_token.revoked_at is not None
        or stored_token.expires_at.replace(tzinfo=UTC) <= datetime.now(UTC)
        or not password_hash.verify(request.refresh_token, stored_token.token_hash)
    ):
        raise HTTPException(status_code=401, detail="invalid refresh token")
    stored_token.revoked_at = datetime.now(UTC)
    db.commit()
    user = db.get(User, payload["sub"])
    if user is None:
        raise HTTPException(status_code=401, detail="invalid refresh token")
    return _issue_tokens(db, user)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    try:
        payload = decode_token(credentials.credentials, "access")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="invalid access token") from None
    user = db.get(User, payload["sub"])
    if user is None:
        raise HTTPException(status_code=401, detail="invalid access token")
    return user


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)) -> dict[str, str]:
    return {"id": current_user.id, "email": current_user.email}

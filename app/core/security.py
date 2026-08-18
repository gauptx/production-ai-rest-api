"""Password hashing and signed access/refresh token helpers."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
from pwdlib import PasswordHash

from app.core.config import ACCESS_TOKEN_MINUTES, JWT_ALGORITHM, JWT_SECRET, REFRESH_TOKEN_DAYS

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    return password_hash.hash(password)


def verify_password(password: str, hashed_password: str) -> bool:
    return password_hash.verify(password, hashed_password)


def create_access_token(user_id: str) -> str:
    return _encode_token(user_id, "access", timedelta(minutes=ACCESS_TOKEN_MINUTES))[0]


def create_refresh_token(user_id: str) -> tuple[str, str, datetime]:
    token, token_id, expires_at = _encode_token(
        user_id, "refresh", timedelta(days=REFRESH_TOKEN_DAYS)
    )
    return token, token_id, expires_at


def decode_token(token: str, expected_type: str) -> dict[str, str]:
    payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    if payload.get("type") != expected_type or not payload.get("sub"):
        raise jwt.InvalidTokenError("Unexpected token type")
    return payload


def _encode_token(user_id: str, token_type: str, lifetime: timedelta) -> tuple[str, str, datetime]:
    now = datetime.now(UTC)
    expires_at = now + lifetime
    token_id = str(uuid4())
    payload = {"sub": user_id, "type": token_type, "jti": token_id, "iat": now, "exp": expires_at}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM), token_id, expires_at

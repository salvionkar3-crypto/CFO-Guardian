"""Security, Password Hashing, and JWT Utilities

Fintech grade security:
- bcrypt password hashing with salt (never stores plain-text passwords)
- PyJWT cryptographic token issuance and verification
- Secret redaction and input sanitization
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import bcrypt
import jwt
from app.core.config import settings
from app.core.logging_config import logger


def hash_password(password: str) -> str:
    """Hashes a plain text password with a secure salted bcrypt round."""
    pwd_bytes = password.encode("utf-8")
    salt = bcrypt.gensalt(rounds=12)
    hashed = bcrypt.hashpw(pwd_bytes, salt)
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Safely verifies a candidate password against the stored bcrypt hash."""
    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8")
        )
    except Exception as exc:
        logger.error(f"Password verification error: {exc}")
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """Encodes a JWT with claims and expiration."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "iat": datetime.utcnow()})
    encoded_jwt = jwt.encode(to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """Decodes and validates a JWT token. Raises PyJWT exceptions if expired or invalid."""
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


def mask_secret(secret: Optional[str], visible_chars: int = 4) -> str:
    """Masks sensitive strings, leaving only a small suffix for verification."""
    if not secret:
        return "[NOT SET]"
    if len(secret) <= visible_chars:
        return "****"
    return f"{'*' * (len(secret) - visible_chars)}{secret[-visible_chars:]}"


def sanitize_string(text: str, max_length: int = 1000) -> str:
    """Strips control chars to protect against injection."""
    if not text:
        return ""
    cleaned = "".join(char for char in text if char.isprintable() or char in "\n\r\t")
    return cleaned[:max_length].strip()

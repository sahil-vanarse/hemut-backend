import types
import bcrypt
from passlib.context import CryptContext
import jwt
from jwt.exceptions import InvalidTokenError
from fastapi import HTTPException
from config import JWT_SECRET, MAX_PASSWORD_BYTES

# Some bcrypt builds ship without __about__.__version__, which passlib expects.
if not hasattr(bcrypt, "__about__"):
    bcrypt.__about__ = types.SimpleNamespace(
        __version__=getattr(bcrypt, "__version__", "unknown")
    )

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def validate_password_length(password: str):
    """Validate password length to ensure it doesn't exceed bcrypt's limit."""
    if len(password.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise HTTPException(
            status_code=400,
            detail=f"Password cannot be longer than {MAX_PASSWORD_BYTES} bytes. "
            "Please choose a shorter password.",
        )


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    validate_password_length(password)
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    validate_password_length(plain_password)
    return pwd_context.verify(plain_password, hashed_password)


def create_token(user_id: int, email: str) -> str:
    """Create a JWT token for a user."""
    payload = {"user_id": user_id, "email": email}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def verify_token(token: str) -> dict:
    """Verify and decode a JWT token."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

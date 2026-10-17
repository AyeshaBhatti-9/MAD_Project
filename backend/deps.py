import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from .database import get_db
from .models import User
from .security import decode_token

bearer = HTTPBearer()

def get_current_user(
    creds: HTTPAuthorizationCredentials = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    try:
        user_id = decode_token(creds.credentials)
    except (jwt.PyJWTError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return user

bearer_optional = HTTPBearer(auto_error=False)

def get_optional_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer_optional),
    db: Session = Depends(get_db),
) -> User | None:
    """Returns the user if a valid token is sent, otherwise None (guest)."""
    if creds is None:
        return None
    try:
        return db.get(User, decode_token(creds.credentials))
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
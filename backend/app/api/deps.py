from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError, jwt

from ..core.database import get_db
from ..core.config import settings
from ..core.security import verify_token

security = HTTPBearer()


def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = None,
    db: Session = Depends(get_db)
) -> str:
    """
    Bypass authentication - return default user
    Authentication will be handled by Cloudflare
    """
    # Always return the default admin user
    # Cloudflare will handle actual authentication
    return settings.ADMIN_EMAIL


def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[str]:
    """
    Optional authentication - returns username if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    token = credentials.credentials
    return verify_token(token)
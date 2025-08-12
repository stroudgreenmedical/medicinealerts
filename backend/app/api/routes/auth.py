from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ...core.database import get_db
from ...core.config import settings
from ...core.security import verify_password, create_access_token, get_password_hash
from ...schemas.alert import LoginRequest, TokenResponse, UserResponse
from ..deps import get_current_user

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/login", response_model=TokenResponse)
async def login(
    login_data: LoginRequest,
    db: Session = Depends(get_db)
):
    """
    Login endpoint - validates credentials and returns JWT token
    """
    # Check if username matches admin email
    if login_data.username != settings.ADMIN_EMAIL:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # In production, store hashed password in database
    # For now, compare with environment variable
    stored_password_hash = get_password_hash(settings.ADMIN_PASSWORD)
    
    if not verify_password(login_data.password, stored_password_hash):
        # For simplicity in development, also check plain password
        if login_data.password != settings.ADMIN_PASSWORD:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password"
            )
    
    # Create access token
    access_token = create_access_token(data={"sub": login_data.username})
    
    return TokenResponse(access_token=access_token)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: str = Depends(get_current_user)
):
    """
    Get current user information
    """
    return UserResponse(
        username=current_user,
        email=current_user
    )


@router.post("/logout")
async def logout(
    current_user: str = Depends(get_current_user)
):
    """
    Logout endpoint (client should discard token)
    """
    return {"message": "Successfully logged out"}
"""
Authentication endpoints
"""
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request, Response, Body
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from slowapi import Limiter
from slowapi.util import get_remote_address

from config import settings
from utils.database import get_db
from models import User, RefreshToken
from schemas import UserCreate, UserResponse, Token, TokenRefreshRequest
from services.auth_service import (
    get_password_hash,
    authenticate_user,
    create_access_token,
    create_refresh_token
)
from dependencies import get_current_active_user

router = APIRouter(prefix="", tags=["auth"])
limiter = Limiter(key_func=get_remote_address)


def _cookie_params(max_age: int) -> dict:
    """Общие параметры для httpOnly cookie (access/refresh)."""
    params = {
        "httponly": True,
        "secure": settings.COOKIE_SECURE,
        "samesite": settings.COOKIE_SAMESITE,
        "max_age": max_age,
        "path": "/",
    }
    if settings.COOKIE_DOMAIN:
        params["domain"] = settings.COOKIE_DOMAIN
    return params


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    """Ставит httpOnly cookie для access/refresh токенов."""
    response.set_cookie(
        settings.ACCESS_TOKEN_COOKIE_NAME,
        access_token,
        **_cookie_params(settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    )
    response.set_cookie(
        settings.REFRESH_TOKEN_COOKIE_NAME,
        refresh_token,
        **_cookie_params(settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
    )


def _clear_auth_cookies(response: Response) -> None:
    """Удаляет httpOnly cookies c токенами."""
    delete_kwargs = {"path": "/"}
    if settings.COOKIE_DOMAIN:
        delete_kwargs["domain"] = settings.COOKIE_DOMAIN
    response.delete_cookie(settings.ACCESS_TOKEN_COOKIE_NAME, **delete_kwargs)
    response.delete_cookie(settings.REFRESH_TOKEN_COOKIE_NAME, **delete_kwargs)


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@limiter.limit("5/minute")
def register(user_data: UserCreate, request: Request, db: Session = Depends(get_db)):
    """Регистрация нового пользователя"""
    # Проверка существования пользователя
    from services.auth_service import get_user_by_email
    db_user = get_user_by_email(db, email=user_data.email)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Создание пользователя
    hashed_password = get_password_hash(user_data.password)
    db_user = User(
        email=user_data.email,
        hashed_password=hashed_password,
        full_name=user_data.full_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    
    return UserResponse(
        id=db_user.id,
        email=db_user.email,
        full_name=db_user.full_name,
        is_active=db_user.is_active,
        created_at=db_user.created_at
    )


@router.post("/token", response_model=Token)
@limiter.limit("10/minute")
def login(
    request: Request,
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Логин и получение JWT токена"""
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires
    )
    
    refresh_token = create_refresh_token(user.id, db)

    # Ставим httpOnly cookies, чтобы фронт не хранил токены в localStorage
    _set_auth_cookies(response, access_token, refresh_token)
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
@limiter.limit("10/minute")
def refresh_token_endpoint(
    request: Request,
    response: Response,
    token_data: Optional[TokenRefreshRequest] = Body(default=None),
    db: Session = Depends(get_db)
):
    """Обновление access токена с помощью refresh токена"""
    incoming_token = (token_data.refresh_token if token_data else None) or request.cookies.get(
        settings.REFRESH_TOKEN_COOKIE_NAME
    )

    if not incoming_token:
        raise HTTPException(status_code=401, detail="Refresh token is missing")

    refresh_token = db.query(RefreshToken).filter(
        RefreshToken.token == incoming_token
    ).first()
    
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Invalid refresh token")
    
    if refresh_token.revoked:
        raise HTTPException(status_code=401, detail="Token revoked")
    
    if refresh_token.expires_at < datetime.utcnow():
        raise HTTPException(status_code=401, detail="Token expired")
    
    # Генерируем новый access token
    access_token_expires = timedelta(minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(refresh_token.user_id)},
        expires_delta=access_token_expires
    )
    
    # Ротация refresh токена (удаляем старый, создаем новый)
    refresh_token.revoked = True
    new_refresh_token = create_refresh_token(refresh_token.user_id, db)
    
    db.commit()

    # Обновляем httpOnly cookies
    _set_auth_cookies(response, access_token, new_refresh_token)
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


@router.post("/logout")
def logout(
    request: Request,
    response: Response,
    token_data: Optional[TokenRefreshRequest] = Body(default=None),
    db: Session = Depends(get_db)
):
    """Отзыв refresh токена"""
    incoming_token = (token_data.refresh_token if token_data else None) or request.cookies.get(
        settings.REFRESH_TOKEN_COOKIE_NAME
    )
    if incoming_token:
        refresh_token = db.query(RefreshToken).filter(
            RefreshToken.token == incoming_token
        ).first()
        if refresh_token:
            refresh_token.revoked = True
            db.commit()

    _clear_auth_cookies(response)
    return {"message": "Logged out successfully"}


@router.get("/me", response_model=UserResponse)
def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Получение информации о текущем пользователе"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        is_active=current_user.is_active,
        created_at=current_user.created_at
    )


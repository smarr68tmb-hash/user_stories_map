"""
User schemas
"""
import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator


class UserCreate(BaseModel):
    """Схема для создания пользователя"""
    email: EmailStr
    password: str
    full_name: Optional[str] = None
    
    @field_validator('password')
    @classmethod
    def validate_password(cls, v: str) -> str:
        """
        Валидация силы пароля:
        - Минимум 8 символов
        - Минимум 1 заглавная буква
        - Минимум 1 строчная буква
        - Минимум 1 цифра
        """
        if len(v) < 8:
            raise ValueError('Пароль должен содержать минимум 8 символов')
        
        if not re.search(r'[A-Z]', v):
            raise ValueError('Пароль должен содержать минимум 1 заглавную букву')
        
        if not re.search(r'[a-z]', v):
            raise ValueError('Пароль должен содержать минимум 1 строчную букву')
        
        if not re.search(r'\d', v):
            raise ValueError('Пароль должен содержать минимум 1 цифру')
        
        return v


class UserResponse(BaseModel):
    """Схема ответа с информацией о пользователе"""
    id: int
    email: str
    full_name: Optional[str]
    is_active: bool
    created_at: datetime
    
    class Config:
        from_attributes = True


class Token(BaseModel):
    """Схема ответа с JWT токенами"""
    access_token: str
    refresh_token: str
    token_type: str


class TokenRefreshRequest(BaseModel):
    """Схема запроса на обновление токена"""
    refresh_token: Optional[str] = None


class TokenData(BaseModel):
    """Схема данных из JWT токена"""
    user_id: Optional[int] = None


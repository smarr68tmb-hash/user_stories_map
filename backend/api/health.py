"""
Health check endpoints
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text

from utils.database import get_db
from config import settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/ready")
def readiness_check(db: Session = Depends(get_db)):
    """Readiness check - проверяет подключение к БД"""
    try:
        db.execute(text("SELECT 1"))
        db_status = "ok"
    except Exception as e:
        db_status = "error"
        raise HTTPException(status_code=503, detail="Database not ready")
    
    # Redis проверка (опционально, если нужен)
    # redis_status = "ok" if redis_client and redis_client.ping() else "unavailable"
    
    return {
        "status": "ready" if db_status == "ok" else "not_ready",
        "database": db_status,
        "timestamp": datetime.utcnow().isoformat()
    }


@router.get("/debug/cookies")
def debug_cookies(request: Request):
    """Debug endpoint для проверки настроек cookies (только для диагностики)"""
    return {
        "cookie_settings": {
            "samesite": settings.COOKIE_SAMESITE,
            "secure": settings.COOKIE_SECURE,
            "domain": settings.COOKIE_DOMAIN or "(not set)",
        },
        "cors_origins": settings.get_allowed_origins_list(),
        "environment": settings.ENVIRONMENT,
        "received_cookies": list(request.cookies.keys()),
        "request_origin": request.headers.get("origin", "(not set)"),
    }


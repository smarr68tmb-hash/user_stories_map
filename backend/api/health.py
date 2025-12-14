"""
Health check endpoints
"""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text

from utils.database import get_db
from config import settings

# Безопасный импорт AI сервиса (может быть не инициализирован при старте)
try:
    from services import ai_service
    _ai_service_available = True
except Exception as e:
    _ai_service_available = False
    import logging
    logger = logging.getLogger(__name__)
    logger.warning(f"AI service not available: {e}")

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


@router.get("/debug/ai-providers")
def debug_ai_providers():
    """Debug endpoint для проверки статуса AI провайдеров"""
    if not _ai_service_available:
        return {
            "error": "AI service not available",
            "timestamp": datetime.utcnow().isoformat(),
        }
    
    clients = getattr(ai_service, "clients", {})
    gemini_client = getattr(ai_service, "gemini_client", None)
    
    providers_status = {}
    
    # Проверяем AgentRouter
    if "agentrouter" in clients:
        providers_status["agentrouter"] = {
            "status": "initialized",
            "model": settings.AGENTROUTER_MODEL,
            "base_url": settings.AGENTROUTER_BASE_URL,
            "has_api_key": bool(settings.AGENTROUTER_API_KEY),
        }
    else:
        providers_status["agentrouter"] = {
            "status": "not_initialized",
            "has_api_key": bool(settings.AGENTROUTER_API_KEY),
            "reason": "Client not initialized (check API key and base_url)" if settings.AGENTROUTER_API_KEY else "API key not set",
        }
    
    # Проверяем Gemini
    if gemini_client:
        providers_status["gemini"] = {
            "status": "initialized",
            "has_api_key": bool(settings.GEMINI_API_KEY),
            "models": {
                "pro": settings.GEMINI_PRO_MODEL,
                "flash": settings.GEMINI_FLASH_MODEL,
            }
        }
    else:
        providers_status["gemini"] = {
            "status": "not_initialized",
            "has_api_key": bool(settings.GEMINI_API_KEY),
            "reason": "Client not initialized" if settings.GEMINI_API_KEY else "API key not set",
        }
    
    # Проверяем остальные OpenAI-совместимые провайдеры
    for provider_name in ["groq", "perplexity", "openai"]:
        if provider_name in clients:
            providers_status[provider_name] = {
                "status": "initialized",
                "has_api_key": bool(getattr(settings, f"{provider_name.upper()}_API_KEY", "")),
            }
        else:
            api_key_attr = f"{provider_name.upper()}_API_KEY"
            has_key = bool(getattr(settings, api_key_attr, ""))
            providers_status[provider_name] = {
                "status": "not_initialized",
                "has_api_key": has_key,
                "reason": "Client not initialized" if has_key else "API key not set",
            }
    
    # Получаем список доступных провайдеров по типу задачи
    available_for_generation = settings.get_providers_for_task("generation")
    available_for_enhancement = settings.get_providers_for_task("enhancement")
    
    return {
        "providers": providers_status,
        "available_providers": {
            "all": settings.get_available_providers(),
            "generation": available_for_generation,
            "enhancement": available_for_enhancement,
        },
        "priority_order": {
            "generation": "agentrouter → gemini-pro → gemini-flash → groq",
            "enhancement": "gemini-pro → gemini-flash → groq (agentrouter не используется для экономии)",
        },
        "timestamp": datetime.utcnow().isoformat(),
    }


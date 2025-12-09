"""
AI service - генерация User Story Map через AI API
Поддерживает fallback между провайдерами: Gemini → Groq → Perplexity → OpenAI
С умным rate limiting и проактивным переключением провайдеров
"""
import json
import hashlib
import logging
import os
import copy
from typing import Optional, Dict, List
from datetime import datetime, timedelta
from fastapi import HTTPException
from openai import OpenAI, RateLimitError, APIError, APITimeoutError, APIConnectionError
import google.generativeai as genai
from google.generativeai.types import HarmCategory, HarmBlockThreshold

from config import settings

logger = logging.getLogger(__name__)


# ============================================================================
# Rate Limiting Tracker
# ============================================================================

class RateLimitTracker:
    """Отслеживает использование API запросов для проактивного переключения"""

    def __init__(self):
        self.usage: Dict[str, Dict] = {}  # {provider: {date: count}}

    def _get_today_key(self) -> str:
        """Возвращает ключ для сегодняшней даты (UTC)"""
        return datetime.utcnow().strftime("%Y-%m-%d")

    def increment(self, provider: str, model: str = None):
        """Увеличивает счетчик использования для провайдера"""
        today = self._get_today_key()
        key = f"{provider}:{model}" if model else provider

        if key not in self.usage:
            self.usage[key] = {}

        if today not in self.usage[key]:
            self.usage[key][today] = 0

        self.usage[key][today] += 1
        logger.debug(f"Rate limit tracker: {key} = {self.usage[key][today]} requests today")

    def get_count(self, provider: str, model: str = None) -> int:
        """Возвращает количество запросов сегодня"""
        today = self._get_today_key()
        key = f"{provider}:{model}" if model else provider
        return self.usage.get(key, {}).get(today, 0)

    def should_skip_provider(self, provider: str, model: str = None) -> bool:
        """Проверяет, нужно ли пропустить провайдера из-за приближения к лимиту"""
        if provider != "gemini":
            return False  # Пока отслеживаем только Gemini

        count = self.get_count(provider, model)

        # Проверяем лимиты для Gemini моделей
        if model and "flash" in model.lower():
            return count >= settings.GEMINI_FLASH_LIMIT
        elif model and "pro" in model.lower():
            return count >= settings.GEMINI_PRO_LIMIT

        # По умолчанию для Gemini используем Flash лимит
        return count >= settings.GEMINI_FLASH_LIMIT

    def cleanup_old_entries(self):
        """Очищает старые записи (старше 2 дней)"""
        today = self._get_today_key()
        today_date = datetime.strptime(today, "%Y-%m-%d")

        for key in list(self.usage.keys()):
            dates_to_remove = []
            for date_str in self.usage[key]:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                if (today_date - date_obj).days > 2:
                    dates_to_remove.append(date_str)

            for date_str in dates_to_remove:
                del self.usage[key][date_str]


# Глобальный трекер лимитов
rate_limiter = RateLimitTracker()

# Инициализация AI клиентов для всех доступных провайдеров
clients: Dict[str, OpenAI] = {}
gemini_client = None  # Gemini использует свой SDK


def _initialize_clients():
    """Инициализирует клиенты для всех доступных провайдеров"""
    global clients, gemini_client

    # Gemini
    if settings.GEMINI_API_KEY:
        try:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            gemini_client = genai
            logger.info("✅ Initialized Gemini API client")
        except Exception as e:
            logger.warning(f"Failed to initialize Gemini client: {e}")

    # Groq
    if settings.GROQ_API_KEY:
        try:
            clients["groq"] = OpenAI(
                api_key=settings.GROQ_API_KEY,
                base_url="https://api.groq.com/openai/v1"
            )
            logger.info("✅ Initialized Groq API client")
        except Exception as e:
            logger.warning(f"Failed to initialize Groq client: {e}")

    # Perplexity
    if settings.PERPLEXITY_API_KEY:
        try:
            clients["perplexity"] = OpenAI(
                api_key=settings.PERPLEXITY_API_KEY,
                base_url="https://api.perplexity.ai"
            )
            logger.info("✅ Initialized Perplexity API client")
        except Exception as e:
            logger.warning(f"Failed to initialize Perplexity client: {e}")

    # OpenAI
    if settings.OPENAI_API_KEY:
        try:
            clients["openai"] = OpenAI(api_key=settings.OPENAI_API_KEY)
            logger.info("✅ Initialized OpenAI API client")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client: {e}")

    if not clients and not gemini_client:
        logger.warning("⚠️ No AI API clients configured. AI functions will be unavailable.")


# Инициализируем клиенты при импорте модуля
_initialize_clients()

# Обратная совместимость: один клиент для старого кода
client: Optional[OpenAI] = None
available_providers = settings.get_available_providers()
if available_providers:
    primary_provider = available_providers[0]
    client = clients.get(primary_provider)


def get_cache_key(requirements_text: str, prefix: str = "ai_map") -> str:
    """Генерирует ключ для кеша на основе текста требований"""
    text_hash = hashlib.sha256(requirements_text.encode()).hexdigest()
    return f"{prefix}:{text_hash}"


def _get_model_for_provider(provider: str, is_enhancement: bool = False, task_type: str = None) -> str:
    """
    Возвращает модель для конкретного провайдера с учетом типа задачи

    Args:
        provider: Имя провайдера (gemini, groq, perplexity, openai)
        is_enhancement: True для Stage 1 (Enhancement)
        task_type: Тип задачи ('enhancement', 'generation', 'assistant')

    Returns:
        Название модели для использования
    """
    # Gemini - используем оптимальные модели для каждой задачи
    if provider == "gemini":
        if task_type == "enhancement" or is_enhancement:
            return settings.GEMINI_ENHANCEMENT_MODEL or settings.API_MODEL or "gemini-2.0-flash-exp"
        elif task_type == "assistant":
            return settings.GEMINI_ASSISTANT_MODEL or settings.API_MODEL or "gemini-2.0-flash-exp"
        else:  # generation
            return settings.GEMINI_GENERATION_MODEL or settings.API_MODEL or "gemini-2.0-flash-exp"

    # Groq
    if is_enhancement:
        if provider == "groq":
            return os.getenv("GROQ_ENHANCEMENT_MODEL", "llama-3.1-8b-instant")
        elif provider == "perplexity":
            return os.getenv("PERPLEXITY_ENHANCEMENT_MODEL", "llama-3.1-sonar-small-32k-online")
        elif provider == "openai":
            return os.getenv("OPENAI_ENHANCEMENT_MODEL", "gpt-4o-mini")
    else:
        # Для основной генерации
        if provider == "groq":
            return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        elif provider == "perplexity":
            return os.getenv("PERPLEXITY_MODEL", "llama-3.1-sonar-large-128k-online")
        elif provider == "openai":
            return os.getenv("OPENAI_MODEL", "gpt-4o")

    # Fallback на настройки из settings
    if is_enhancement:
        return settings.get_enhancement_model()
    return settings.API_MODEL


def _call_gemini_api(messages: List[dict], model: str, temperature: float, timeout: float = 60.0) -> str:
    """
    Вызывает Gemini API и возвращает текстовый ответ

    Args:
        messages: Список сообщений [{role, content}]
        model: Название модели
        temperature: Температура генерации
        timeout: Таймаут в секундах

    Returns:
        Текстовый ответ от модели

    Raises:
        Exception: При ошибке API
    """
    if not gemini_client:
        raise Exception("Gemini client not initialized")

    # Собираем промпт из messages
    # Gemini API работает по-другому - нужно объединить system и user prompts
    system_parts = []
    user_parts = []

    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")

        if role == "system":
            system_parts.append(content)
        elif role == "user":
            user_parts.append(content)
        elif role == "assistant":
            # Gemini не поддерживает assistant role в истории для одного запроса
            # Просто добавляем в user context
            user_parts.append(f"[Previous response]: {content}")

    # Формируем финальный промпт
    full_prompt = ""
    if system_parts:
        full_prompt += "\n\n".join(system_parts) + "\n\n"
    if user_parts:
        full_prompt += "\n\n".join(user_parts)

    # Создаем модель с настройками безопасности
    generation_config = {
        "temperature": temperature,
        "top_p": 0.95,
        "top_k": 40,
        "max_output_tokens": 8192,
    }

    safety_settings = {
        HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
    }

    model_obj = gemini_client.GenerativeModel(
        model_name=model,
        generation_config=generation_config,
        safety_settings=safety_settings
    )

    # Вызываем API
    response = model_obj.generate_content(full_prompt)

    # Проверяем блокировку контента
    if not response.text:
        if hasattr(response, 'prompt_feedback'):
            raise Exception(f"Content was blocked: {response.prompt_feedback}")
        raise Exception("Empty response from Gemini API")

    return response.text


def _should_retry_error(error: Exception, provider: str) -> bool:
    """Определяет, стоит ли повторять запрос с другим провайдером при этой ошибке"""
    if isinstance(error, RateLimitError):
        return True  # Лимиты - переключаемся
    if isinstance(error, APIConnectionError):
        return True  # Проблемы с сетью - переключаемся
    if isinstance(error, APIError):
        # Проверяем код ошибки
        error_str = str(error).lower()
        if "429" in error_str or "rate limit" in error_str or "quota" in error_str:
            return True
        if "503" in error_str or "service unavailable" in error_str:
            return True

    # Gemini ошибки
    error_str = str(error).lower()
    if "429" in error_str or "quota" in error_str or "rate" in error_str:
        return True
    if "503" in error_str or "unavailable" in error_str:
        return True

    # Timeout и JSON ошибки не переключаем - это может быть проблема запроса
    return False


def _make_request_with_fallback(
    request_params: dict,
    providers: Optional[List[str]] = None,
    is_enhancement: bool = False,
    task_type: str = None
) -> tuple:
    """
    Выполняет запрос к AI API с автоматическим fallback между провайдерами

    Args:
        request_params: Параметры запроса (model будет заменен для каждого провайдера)
        providers: Список провайдеров для попыток (по умолчанию из настроек)
        is_enhancement: Используется ли для enhancement (влияет на выбор модели)
        task_type: Тип задачи ('enhancement', 'generation', 'assistant')

    Returns:
        tuple: (completion, provider_name) - результат и имя провайдера, который ответил

    Raises:
        HTTPException: Если все провайдеры недоступны
    """
    if providers is None:
        providers = settings.get_available_providers()

    if not providers:
        raise HTTPException(
            status_code=503,
            detail="No AI providers configured. Set GEMINI_API_KEY, GROQ_API_KEY, PERPLEXITY_API_KEY, or OPENAI_API_KEY."
        )

    # Очищаем старые записи rate limiter
    rate_limiter.cleanup_old_entries()

    last_error = None
    last_provider = None

    for provider in providers:
        # Проверяем, нужно ли пропустить провайдера из-за лимитов
        model = _get_model_for_provider(provider, is_enhancement, task_type)
        if rate_limiter.should_skip_provider(provider, model):
            logger.info(f"⏩ Skipping {provider.upper()} - approaching rate limit")
            continue

        # Проверяем инициализацию клиента (кроме Gemini)
        if provider != "gemini" and provider not in clients:
            logger.debug(f"Skipping {provider} - client not initialized")
            continue

        if provider == "gemini" and not gemini_client:
            logger.debug(f"Skipping gemini - client not initialized")
            continue

        try:
            # Получаем модель для этого провайдера
            model = _get_model_for_provider(provider, is_enhancement, task_type)

            logger.info(f"Trying {provider.upper()} with model {model}")

            # Gemini использует свой API
            if provider == "gemini":
                # Создаем копию параметров
                messages = copy.deepcopy(request_params.get("messages", []))
                temperature = request_params.get("temperature", 0.7)
                timeout = request_params.get("timeout", 60.0)

                # Добавляем инструкцию для JSON (для не-OpenAI провайдеров)
                if len(messages) > 0:
                    last_msg = messages[-1]
                    if isinstance(last_msg, dict) and "content" in last_msg:
                        if "IMPORTANT: Return ONLY valid JSON" not in last_msg["content"]:
                            messages[-1]["content"] += "\n\nIMPORTANT: Return ONLY valid JSON, no additional text or markdown formatting."

                # Вызываем Gemini API
                response_text = _call_gemini_api(messages, model, temperature, timeout)

                # Создаем объект completion для совместимости
                class GeminiCompletion:
                    def __init__(self, text):
                        self.choices = [type('obj', (object,), {
                            'message': type('obj', (object,), {'content': text})()
                        })()]

                completion = GeminiCompletion(response_text)

                # Увеличиваем счетчик rate limiter
                rate_limiter.increment(provider, model)

                logger.info(f"✅ Successfully got response from {provider.upper()}")
                return completion, provider

            # OpenAI-совместимые провайдеры (Groq, Perplexity, OpenAI)
            else:
                # Создаем deep copy параметров запроса
                provider_params = copy.deepcopy(request_params)
                provider_params["model"] = model

                # JSON mode только для OpenAI
                if provider == "openai":
                    if "response_format" not in provider_params:
                        provider_params["response_format"] = {"type": "json_object"}
                else:
                    # Для Groq, Perplexity: убираем response_format
                    provider_params.pop("response_format", None)
                    # Добавляем инструкцию в промпт
                    if len(provider_params["messages"]) > 0:
                        last_msg = provider_params["messages"][-1]
                        if isinstance(last_msg, dict) and "content" in last_msg:
                            if "IMPORTANT: Return ONLY valid JSON" not in last_msg["content"]:
                                provider_params["messages"][-1]["content"] += "\n\nIMPORTANT: Return ONLY valid JSON, no additional text or markdown formatting."

                completion = clients[provider].chat.completions.create(**provider_params)

                # Увеличиваем счетчик rate limiter
                rate_limiter.increment(provider, model)

                logger.info(f"✅ Successfully got response from {provider.upper()}")
                return completion, provider
            
        except (RateLimitError, APIConnectionError) as e:
            last_error = e
            last_provider = provider
            logger.warning(f"❌ {provider.upper()} failed ({type(e).__name__}): {e}. Trying next provider...")
            continue
        except APIError as e:
            if _should_retry_error(e, provider):
                last_error = e
                last_provider = provider
                logger.warning(f"❌ {provider.upper()} failed (APIError): {e}. Trying next provider...")
                continue
            else:
                # Не переключаемся на другие провайдеры для этой ошибки
                raise HTTPException(
                    status_code=502,
                    detail=f"{provider.upper()} API error: {str(e)}"
                )
        except Exception as e:
            last_error = e
            last_provider = provider
            logger.warning(f"❌ {provider.upper()} failed (unexpected): {e}. Trying next provider...")
            continue
    
    # Все провайдеры не сработали
    if last_error and last_provider:
        error_msg = f"All AI providers failed. Last error from {last_provider.upper()}: {str(last_error)}"
    elif last_error:
        error_msg = f"All AI providers failed. Last error: {str(last_error)}"
    else:
        error_msg = "All AI providers unavailable"
    
    logger.error(f"❌ {error_msg}")
    raise HTTPException(
        status_code=503,
        detail=error_msg
    )


def enhance_requirements(raw_text: str, redis_client=None, use_cache: bool = True) -> dict:
    """
    Stage 1: Улучшает пользовательские требования перед генерацией карты
    
    Принимает неструктурированный текст и возвращает:
    - enhanced_text: улучшенный, структурированный текст
    - added_aspects: что было добавлено
    - missing_info: что всё ещё не хватает
    - confidence: уверенность в улучшении (0-1)
    
    Args:
        raw_text: Исходный текст требований от пользователя
        redis_client: Redis клиент для кеширования
        use_cache: Использовать ли кеш
    
    Returns:
        dict: Результат улучшения
    """
    
    # Проверяем наличие доступных провайдеров
    available_providers = settings.get_available_providers()
    if not available_providers:
        raise HTTPException(
            status_code=503,
            detail="AI API key not configured. Set GROQ_API_KEY, PERPLEXITY_API_KEY, or OPENAI_API_KEY environment variable."
        )
    
    # Валидация размера входных данных
    if len(raw_text.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Requirements text is too short. Please provide at least 10 characters."
        )
    
    if len(raw_text) > 10000:
        raise HTTPException(
            status_code=400,
            detail="Requirements text is too long. Maximum 10000 characters allowed."
        )
    
    # Проверяем кеш перед запросом к AI
    cache_key = get_cache_key(raw_text, prefix="enhance")
    if use_cache and redis_client:
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                logger.info("Using cached enhancement response")
                return json.loads(cached_result)
        except Exception as e:
            logger.warning(f"Redis cache read failed: {e}")
    
    system_prompt = """Ты — эксперт по написанию product requirements для IT-продуктов.
Твоя задача: улучшить неструктурированные требования пользователя, добавив недостающие детали и структуру, НО не выдумывая лишнего.

Что добавить (если применимо и очевидно из контекста):
1. Чёткое описание типа продукта (web/mobile/desktop/SaaS)
2. Полный список ролей пользователей с их основными задачами
3. Основные функции, которые логически следуют из описания
4. Типичные нефункциональные требования:
   - Платформы (iOS/Android/Web)
   - Уведомления (push, email, SMS)
   - Офлайн режим (для mobile)
   - Оплата (для e-commerce, marketplace)
   - Безопасность (для sensitive data)

Что НЕ добавлять:
- Специфичные бизнес-правила (если не указаны пользователем)
- Конкретные технологии (React, PostgreSQL и т.д.)
- Детали UI/UX дизайна
- Функции, которые не очевидны из контекста

ВАЖНО: Все тексты должны быть на РУССКОМ языке.
Возвращай ТОЛЬКО валидный JSON без дополнительного текста."""

    user_prompt = f"""Исходные требования пользователя:
\"\"\"
{raw_text}
\"\"\"

Улучши эти требования, добавив структуру и недостающие стандартные детали.
Сохрани ВСЕ специфичные детали, которые указал пользователь.

Верни JSON в точно таком формате:
{{
  "enhanced_text": "Улучшенный структурированный текст требований (1-2 абзаца)",
  "added_aspects": ["Список добавленных аспектов, например: 'Добавлены роли: Администратор'"],
  "missing_info": ["Список того, что рекомендуется уточнить, например: 'Не указан способ оплаты'"],
  "detected_product_type": "web/mobile/desktop/saas/other",
  "detected_roles": ["Список выявленных ролей"],
  "confidence": 0.85
}}

confidence должен быть от 0.5 до 1.0:
- 0.9-1.0: требования понятны, добавлены только стандартные детали
- 0.7-0.9: требования понятны, но пришлось сделать предположения
- 0.5-0.7: требования размытые, много предположений"""

    try:
        logger.info(f"Enhancing requirements (length: {len(raw_text)} chars)")
        
        request_params = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.5,  # Меньше креатива, больше точности
            "timeout": 30.0,  # 30 секунд должно хватить
        }
        
        # Используем fallback механизм
        completion, used_provider = _make_request_with_fallback(
            request_params,
            providers=available_providers,
            is_enhancement=True,
            task_type="enhancement"
        )
        
        response_text = completion.choices[0].message.content
        logger.info(f"Successfully received enhancement response from {used_provider.upper()}")
        
        # Очистка ответа от markdown
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        result = json.loads(response_text)
        
        # Добавляем оригинальный текст для сравнения
        result["original_text"] = raw_text
        
        # Кешируем результат на 24 часа
        if use_cache and redis_client:
            try:
                redis_client.setex(
                    cache_key,
                    86400,  # 24 часа
                    json.dumps(result)
                )
                logger.info("Enhancement result cached in Redis")
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
        
        logger.info(f"Requirements enhanced. Confidence: {result.get('confidence', 'N/A')}")
        return result
        
    except APITimeoutError as e:
        logger.error(f"Request timeout: {e}")
        raise HTTPException(
            status_code=504,
            detail="Request to AI service timed out. Please try again."
        )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from AI enhancement: {e}")
        # Fallback: возвращаем оригинал если AI вернул невалидный JSON
        return {
            "enhanced_text": raw_text,
            "original_text": raw_text,
            "added_aspects": [],
            "missing_info": [],
            "detected_product_type": "unknown",
            "detected_roles": [],
            "confidence": 1.0,
            "fallback": True,
            "error": "Failed to parse AI response"
        }
    except Exception as e:
        error_msg = str(e) if str(e) else repr(e)
        if not error_msg:
            error_msg = f"{type(e).__name__}: An unexpected error occurred"
        logger.error(f"Unexpected error in requirements enhancement: {error_msg}", exc_info=True)
        # Fallback: возвращаем оригинал
        return {
            "enhanced_text": raw_text,
            "original_text": raw_text,
            "added_aspects": [],
            "missing_info": [],
            "detected_product_type": "unknown",
            "detected_roles": [],
            "confidence": 1.0,
            "fallback": True,
            "error": error_msg
        }


def generate_ai_map(requirements_text: str, redis_client=None, use_cache: bool = True) -> dict:
    """Отправляет запрос в AI API и получает структурированную User Story Map"""
    
    # Проверяем наличие доступных провайдеров
    available_providers = settings.get_available_providers()
    if not available_providers:
        raise HTTPException(
            status_code=503,
            detail="AI API key not configured. Set GROQ_API_KEY, PERPLEXITY_API_KEY, or OPENAI_API_KEY environment variable."
        )
    
    # Валидация размера входных данных
    if len(requirements_text.strip()) < 10:
        raise HTTPException(
            status_code=400,
            detail="Requirements text is too short. Please provide at least 10 characters."
        )
    
    if len(requirements_text) > 10000:
        raise HTTPException(
            status_code=400,
            detail="Requirements text is too long. Maximum 10000 characters allowed."
        )
    
    # Проверяем кеш перед запросом к AI
    cache_key = get_cache_key(requirements_text)
    if use_cache and redis_client:
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                logger.info("Using cached AI response")
                return json.loads(cached_result)
        except Exception as e:
            logger.warning(f"Redis cache read failed: {e}")
    
    system_prompt = """Ты — эксперт Product Manager и Business Analyst, специализирующийся на User Story Mapping (USM). 
Твоя задача — анализировать неструктурированные требования к продукту и преобразовывать их в структурированную User Story Map в формате JSON.

ВАЖНО: Все тексты должны быть на РУССКОМ языке.
Строго следуй структуре JSON для вывода. Не добавляй никакого разговорного текста, только JSON объект."""

    user_prompt = f"""Проанализируй следующие требования к продукту, указанные в тройных кавычках:

\"\"\"
{requirements_text}
\"\"\"

Твоя задача:
1. Определить основные User Personas (роли пользователей).
2. Создать "Backbone" (основу) карты, состоящую из высокоуровневых "Activities" (Активностей/Целей пользователя) и последовательных "User Tasks" (Шагов для достижения целей).
3. Разбить каждую User Task на конкретные "User Stories" (Пользовательские истории).
4. Назначить приоритет каждой истории: "MVP", "Release 1" или "Later".
5. Сгенерировать базовые Acceptance Criteria (Критерии приемки) для каждой истории.

ВАЖНО: Все названия, описания и критерии должны быть на РУССКОМ языке.

Верни ТОЛЬКО валидный JSON в точно такой структуре:
{{
  "productName": "Предложенное название продукта",
  "personas": ["Список выявленных персон"],
  "map": [
    {{
      "activity": "Высокоуровневая активность (например, Управление аккаунтом)",
      "tasks": [
        {{
          "taskTitle": "Конкретный шаг пользователя (например, Регистрация)",
          "stories": [
            {{
              "title": "Название пользовательской истории (например, Регистрация через Email)",
              "description": "Как [персона], я хочу..., чтобы...",
              "priority": "MVP",
              "acceptanceCriteria": [
                "Критерий 1",
                "Критерий 2"
              ]
            }}
          ]
        }}
      ]
    }}
  ]
}}"""

    try:
        logger.info(f"Generating map for requirements (length: {len(requirements_text)} chars)")

        # Подготовка параметров запроса
        request_params = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": settings.API_TEMPERATURE,
            "timeout": 60.0,  # 60 секунд таймаут
        }

        # Используем fallback механизм
        completion, used_provider = _make_request_with_fallback(
            request_params,
            providers=available_providers,
            is_enhancement=False,
            task_type="generation"
        )
        
        response_text = completion.choices[0].message.content
        logger.info(f"Successfully received AI response from {used_provider.upper()}")
        
        # Очистка ответа от возможных markdown форматирования (для Perplexity)
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]  # Убираем ```json
        if response_text.startswith("```"):
            response_text = response_text[3:]  # Убираем ```
        if response_text.endswith("```"):
            response_text = response_text[:-3]  # Убираем закрывающий ```
        response_text = response_text.strip()
        
        # Проверяем, что ответ не пустой
        if not response_text:
            logger.error("Empty response from AI service")
            raise HTTPException(
                status_code=502,
                detail="AI service returned an empty response. Please try again."
            )
        
        try:
            result = json.loads(response_text)
        except json.JSONDecodeError as json_err:
            logger.error(f"Failed to parse AI response as JSON. Response preview: {response_text[:200]}")
            logger.error(f"JSON decode error: {json_err}")
            raise HTTPException(
                status_code=502,
                detail=f"Invalid JSON response from AI service: {str(json_err)}"
            )
        
        # Валидация структуры ответа
        if not isinstance(result, dict):
            logger.error(f"AI response is not a dictionary: {type(result)}")
            raise HTTPException(
                status_code=502,
                detail="AI service returned invalid response format. Expected a JSON object."
            )
        
        if "map" not in result:
            logger.error(f"AI response missing 'map' field. Keys: {list(result.keys())}")
            raise HTTPException(
                status_code=502,
                detail="AI service response is missing required 'map' field."
            )
        
        if not isinstance(result.get("map"), list):
            logger.error(f"AI response 'map' field is not a list: {type(result.get('map'))}")
            raise HTTPException(
                status_code=502,
                detail="AI service response 'map' field must be a list."
            )
        
        # Сохранение в кеш Redis (TTL 24 часа)
        if use_cache and redis_client:
            try:
                redis_client.setex(
                    cache_key,
                    86400,  # 24 часа
                    json.dumps(result)
                )
                logger.info("Result cached in Redis")
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
        
        return result
        
    except APITimeoutError as e:
        logger.error(f"Request timeout: {e}")
        raise HTTPException(
            status_code=504,
            detail="Request to AI service timed out. Please try again."
        )
    except HTTPException:
        # Re-raise HTTPExceptions (from validation or inner handlers)
        raise
    except Exception as e:
        error_msg = str(e) if str(e) else repr(e)
        if not error_msg:
            error_msg = f"{type(e).__name__}: An unexpected error occurred"
        logger.error(f"Unexpected error in AI generation: {error_msg}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {error_msg}"
        )


def _summarize_project_snapshot(project_snapshot: dict) -> str:
    """Подготовка текста среза проекта для промпта wireframe."""
    name = project_snapshot.get("name", "Project")
    activities = project_snapshot.get("activities", [])
    releases = project_snapshot.get("releases", [])
    lines = [f"Проект: {name}", f"Всего активностей: {len(activities)}", f"Релизы: {', '.join(r.get('title','') for r in releases) or '—'}"]

    for act_idx, activity in enumerate(activities, 1):
        lines.append(f"\nActivity {act_idx}: {activity.get('title','')}")
        tasks = activity.get("tasks", [])
        lines.append(f"  Tasks: {len(tasks)}")
        for task_idx, task in enumerate(tasks, 1):
            lines.append(f"  Task {task_idx}: {task.get('title','')}")
            stories = task.get("stories", [])
            for story_idx, story in enumerate(stories, 1):
                ac_text = "; ".join(story.get("acceptance_criteria", [])[:3])
                lines.append(
                    f"    Story {story_idx}: {story.get('title','')} "
                    f"(priority: {story.get('priority','')}, status: {story.get('status','')})"
                )
                if story.get("description"):
                    lines.append(f"      Desc: {story.get('description')}")
                if ac_text:
                    lines.append(f"      AC: {ac_text}")
    return "\n".join(lines)


def generate_markdown_wireframe(project_snapshot: dict, timeout: float = 60.0) -> str:
    """
    Генерирует markdown wireframe (ASCII схема + список UI элементов + описание layout)
    для всей карты проекта.

    Args:
        project_snapshot: dict с полями name, activities[tasks[stories]], releases
        timeout: таймаут запроса к AI

    Returns:
        str: markdown текст wireframe
    """
    available_providers = settings.get_available_providers()
    if not available_providers:
        raise HTTPException(
            status_code=503,
            detail="AI API key not configured. Set GROQ_API_KEY, PERPLEXITY_API_KEY, or OPENAI_API_KEY environment variable."
        )

    # Валидация объёма (проверяем после создания summary, так как он более компактный)
    # Сначала создаем summary для проверки
    project_text = _summarize_project_snapshot(project_snapshot)
    
    if len(project_text) < 50:
        raise HTTPException(status_code=400, detail="Project snapshot is too small to generate wireframe.")
    
    # Увеличиваем лимит до 50000 символов (для больших проектов)
    # Проверяем размер summary, а не полного snapshot
    if len(project_text) > 50000:
        raise HTTPException(
            status_code=400,
            detail=f"Project snapshot is too large for wireframe generation ({len(project_text)} chars). "
                   f"Please reduce the number of activities, tasks, or stories."
        )
    
    # Логируем размер для отладки
    serialized = json.dumps(project_snapshot, ensure_ascii=False)
    logger.info(f"Wireframe generation: snapshot={len(serialized)} chars, summary={len(project_text)} chars")

    system_prompt = """Ты — эксперт по UX/UI и продуктовому дизайну. Твоя задача — создать детальную визуализацию интерфейса в формате ASCII wireframe.

КРИТИЧЕСКИ ВАЖНО:
- Используй детальные ASCII схемы с box-drawing символами (┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼ │ ─)
- Показывай ВСЕ UI элементы: кнопки [текст], поля ввода [______], выпадающие списки [▼], иконки (📁, 🗑, ✏️)
- Визуализируй структуру папок, списков, форм, модальных окон
- Показывай несколько экранов/состояний если нужно (например, список → форма создания)
- Используй стрелки ↓ для показа переходов между экранами
- Будь максимально детальным и визуальным

Важно:
- Русский язык
- Детально и визуально понятно
- Без HTML, только markdown и ASCII
"""

    example_ascii = """Пример ДЕТАЛЬНОГО ASCII wireframe:

┌──────────────────────────────────────────────────────────────────────┐
│ Shoppable Templates                                     [+ Create]    │
├──────────────────────────────────────────────────────────────────────┤
│                                                                       │
│ 📁 Folder 1                                                          │
│   ├─ Custom Template 1                              [🗑]            │
│   └─ Custom Template 2                              [🗑]            │
│                                                                       │
│ 📁 Folder 2                                                          │
│   ├─ 📁 Subfolder 2.1                                               │
│   │   └─ Template 3                                  [🗑]            │
│   └─ Template 4                                      [🗑]            │
│                                                                       │
│ [Нет шаблонов]                                                       │
│ Нажмите "+ Create" для создания первого шаблона                      │
└──────────────────────────────────────────────────────────────────────┘
                            ↓ КЛИК [+ Create]

┌──────────────────────────────────────────────────────────────────────┐
│ Create a template                            [Cancel] [Export ▼]     │
├──────────────────────────────────────────────────────────────────────┤
│ ┌─ PREVIEW ──────────────┐  ┌─ SETTINGS ───────────────────────┐   │
│ │ [Video 800x600]        │  │ General                          │   │
│ │ Time: 4/15s            │  │ Name: [______________]  (?)      │   │
│ │ [▶][❚❚] [X Guide: On] │  │ [+] Upload video                 │   │
│ └────────────────────────┘  │ Font: [Arial ▼]                  │   │
│                             │ Items: [6] [Calculate]           │   │
│                             │ Table of times: [таблица]        │   │
│                             │                                   │   │
│                             │ Elements (Product: All ▼)        │   │
│                             │ ├─ Logo #1      [Edit][Del]      │   │
│                             │ ├─ QRCode #1    [Edit][Del]      │   │
│                             │ └─ Text #1      [Edit][Del]      │   │
│                             │ [+ Image] [+ Text]               │   │
│                             └──────────────────────────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
"""

    project_text = _summarize_project_snapshot(project_snapshot)

    user_prompt = f"""Сгенерируй ДЕТАЛЬНЫЙ markdown wireframe для всей карты проекта User Story Map.

ВАЖНО: Создай визуально понятные ASCII схемы, которые показывают:
- Структуру интерфейса (header, sidebar, main area)
- Все кнопки, поля ввода, выпадающие списки
- Иконки и визуальные элементы
- Несколько экранов/состояний если нужно (список → детали → форма редактирования)
- Стрелки для показа переходов

Пример детального wireframe:
{example_ascii}

Структура ответа (строго):
1) ДЕТАЛЬНАЯ ASCII схема в блоке ```ascii ... ``` - покажи главный экран карты проекта
2) Если есть модальные окна/формы - покажи их отдельно со стрелкой перехода
3) ## Layout Description — детально опиши layout, зоны, расположение элементов
4) ## UI Elements — детальный список всех элементов:
   - [Button] Название (где находится, что делает)
   - [Input] Название поля (тип, валидация)
   - [Dropdown] Название (опции)
   - [Icon] Название (действие)
5) ## Navigation — основные переходы и пользовательские флоу
6) ## Additional Notes — важные нюансы, edge cases, состояния загрузки

Данные проекта:
{project_text}

Сгенерируй wireframe, который визуально показывает как будет выглядеть интерфейс для работы с этой картой пользовательских историй.
"""

    request_params = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.7,  # Немного выше для более креативной генерации wireframe
        "timeout": timeout,
    }

    try:
        completion, used_provider = _make_request_with_fallback(
            request_params,
            providers=available_providers,
            is_enhancement=False,
            task_type="generation",
        )
        logger.info(f"✅ Wireframe markdown received from {used_provider.upper()}")
        response_text = completion.choices[0].message.content or ""
        response_text = response_text.strip()
        # Убираем возможные markdown-ограждения
        if response_text.startswith("```"):
            response_text = response_text.lstrip("`")
        if response_text.endswith("```"):
            response_text = response_text[:-3].strip()
        return response_text
    except APITimeoutError as e:
        logger.error(f"Wireframe request timeout: {e}")
        raise HTTPException(status_code=504, detail="Wireframe generation timed out. Please try again.")
    except Exception as e:
        error_msg = str(e) if str(e) else repr(e)
        logger.error(f"Wireframe generation failed: {error_msg}", exc_info=True)
        raise HTTPException(status_code=502, detail=f"Wireframe generation failed: {error_msg}")


def ai_improve_story_content(
    story_data: dict,
    user_prompt: str,
    action: str = None,
    redis_client=None,
    use_cache: bool = True
) -> dict:
    """
    Улучшает содержимое пользовательской истории через AI
    
    Args:
        story_data: Текущие данные истории (title, description, acceptance_criteria, etc.)
        user_prompt: Запрос пользователя на улучшение
        action: Quick action ('details', 'criteria', 'split', 'edge_cases')
        redis_client: Redis клиент для кеширования
        use_cache: Использовать ли кеш
    
    Returns:
        dict: Улучшенные данные истории
    """
    
    # Проверяем наличие доступных провайдеров
    available_providers = settings.get_available_providers()
    if not available_providers:
        raise HTTPException(
            status_code=503,
            detail="AI API key not configured. Set GROQ_API_KEY, PERPLEXITY_API_KEY, or OPENAI_API_KEY environment variable."
        )
    
    # Валидация промпта
    if len(user_prompt.strip()) < 3:
        raise HTTPException(
            status_code=400,
            detail="Prompt is too short. Please provide at least 3 characters."
        )
    
    if len(user_prompt) > 1000:
        raise HTTPException(
            status_code=400,
            detail="Prompt is too long. Maximum 1000 characters allowed."
        )
    
    # Проверяем кеш
    cache_key = get_cache_key(f"improve:{story_data.get('title', '')}:{user_prompt}:{action}")
    if use_cache and redis_client:
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                logger.info("Using cached AI improvement response")
                return json.loads(cached_result)
        except Exception as e:
            logger.warning(f"Redis cache read failed: {e}")
    
    # Подготовка промпта в зависимости от действия
    action_prompts = {
        'details': 'Сделай лучше и понятнее описание по best практикам User Story. Добавь контекст использования, бизнес-ценность и детали реализации. Убедись, что описание следует формату "Как [роль], я хочу [действие], чтобы [результат]" и содержит достаточно информации для понимания функциональности.',
        'criteria': 'Улучши и расширь acceptance criteria. Сделай их более конкретными, измеримыми и полными. Каждый критерий должен быть проверяемым, содержать конкретные условия и ожидаемые результаты. Добавь критерии для успешных сценариев и обработки ошибок.',
        'split': 'Проанализируй историю и предложи, как её можно разделить на 2-3 более мелкие, независимые истории. Каждая новая история должна быть самодостаточной и иметь четкую бизнес-ценность.',
        'edge_cases': 'Добавь edge cases (граничные случаи) в acceptance criteria. Подумай об ошибках, крайних ситуациях, невалидных данных, сетевых проблемах и других исключительных сценариях, которые нужно обработать.'
    }
    
    action_instruction = action_prompts.get(action, '')
    
    system_prompt = """Ты — эксперт Product Manager и Business Analyst с глубоким пониманием best практик User Story.

Твоя задача — улучшать пользовательские истории (User Stories) на основе запросов пользователя, следуя industry best practices.

BEST PRACTICES USER STORY:
1. Формат: "Как [роль/персона], я хочу [действие/функциональность], чтобы [бизнес-ценность/результат]"
2. Описание должно быть понятным, конкретным и содержать достаточно контекста
3. Acceptance Criteria должны быть:
   - Конкретными и измеримыми (SMART)
   - Проверяемыми (можно написать тест)
   - Полными (успешные сценарии + обработка ошибок)
   - Сформулированными как условия выполнения (Given-When-Then или простой список)
4. История должна быть независимой, ценной и реализуемой (INVEST принцип)

ВАЖНО: 
- Все тексты должны быть на РУССКОМ языке
- Сохраняй структуру и формат истории
- Будь конкретным и практичным
- Следуй best практикам User Story
- Возвращай ТОЛЬКО валидный JSON без дополнительного текста"""
    
    current_story_info = f"""
Текущая история:
Название: {story_data.get('title', 'Без названия')}
Описание: {story_data.get('description', 'Нет описания')}
Приоритет: {story_data.get('priority', 'Later')}
Acceptance Criteria: {json.dumps(story_data.get('acceptance_criteria', []), ensure_ascii=False)}
"""
    
    user_full_prompt = f"""{current_story_info}

Запрос пользователя: {user_prompt}
{f'Действие: {action_instruction}' if action_instruction else ''}

Улучши эту историю согласно запросу пользователя, следуя best практикам User Story:
- Убедись, что название следует формату "Как [роль], я хочу [действие], чтобы [результат]"
- Описание должно быть понятным и содержать контекст
- Acceptance Criteria должны быть конкретными, измеримыми и проверяемыми
- Каждый критерий должен описывать конкретное условие и ожидаемый результат

Если действие "split" (разделить), верни JSON в формате:
{{
  "action": "split",
  "stories": [
    {{
      "title": "Название первой истории",
      "description": "Описание",
      "priority": "MVP",
      "acceptance_criteria": ["Критерий 1", "Критерий 2"]
    }},
    // ... еще истории
  ],
  "suggestion": "Пояснение, почему разделено именно так"
}}

Для всех остальных случаев верни JSON в формате:
{{
  "action": "improve",
  "title": "Улучшенное название (формат: 'Как [роль], я хочу [действие], чтобы [результат]')",
  "description": "Улучшенное описание с контекстом и деталями",
  "priority": "MVP/Release 1/Later",
  "acceptance_criteria": [
    "Конкретный, измеримый критерий с условиями и ожидаемым результатом",
    "Еще один критерий, описывающий успешный сценарий",
    "Критерий для обработки ошибок или граничных случаев"
  ],
  "suggestion": "Краткое пояснение изменений"
}}

ВАЖНО для Acceptance Criteria:
- Каждый критерий должен быть конкретным и проверяемым
- Используй формат: "Когда [условие], то [ожидаемый результат]" или "Система должна [действие] при [условие]"
- Включи критерии для успешных сценариев и обработки ошибок
- Избегай общих фраз типа "должно работать" - будь конкретным

Верни ТОЛЬКО валидный JSON, без markdown форматирования."""
    
    try:
        logger.info(f"Improving story with prompt length: {len(user_prompt)} chars, action: {action}")

        request_params = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_full_prompt},
            ],
            "temperature": 0.7,
            "timeout": 30.0,
        }

        # Используем fallback механизм
        completion, used_provider = _make_request_with_fallback(
            request_params,
            providers=available_providers,
            is_enhancement=False,
            task_type="assistant"
        )
        
        response_text = completion.choices[0].message.content
        logger.info(f"Successfully received AI improvement response from {used_provider.upper()}")
        
        # Очистка ответа от markdown
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        result = json.loads(response_text)
        
        # Кешируем результат на 1 час
        if use_cache and redis_client:
            try:
                redis_client.setex(
                    cache_key,
                    3600,  # 1 час
                    json.dumps(result)
                )
                logger.info("Improvement result cached in Redis")
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
        
        return result
        
    except APITimeoutError as e:
        logger.error(f"Request timeout: {e}")
        raise HTTPException(
            status_code=504,
            detail="Request to AI service timed out. Please try again."
        )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from AI: {e}")
        raise HTTPException(
            status_code=502,
            detail="Invalid response format from AI service. Please try again."
        )
    except Exception as e:
        error_msg = str(e) if str(e) else repr(e)
        if not error_msg:
            error_msg = f"{type(e).__name__}: An unexpected error occurred"
        logger.error(f"Unexpected error in AI improvement: {error_msg}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {error_msg}"
        )


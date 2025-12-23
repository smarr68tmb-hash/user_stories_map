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
from abc import ABC, abstractmethod
from typing import Optional, Dict, List, Tuple
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
        # Gemini Pro — отдельный лимит (50 RPD)
        if provider == "gemini-pro":
            count = self.get_count(provider, model)
            return count >= settings.GEMINI_PRO_LIMIT

        # Gemini Flash — отдельный лимит (250 RPD)
        if provider == "gemini-flash":
            count = self.get_count(provider, model)
            return count >= settings.GEMINI_FLASH_LIMIT

        # Legacy: старый провайдер "gemini"
        if provider == "gemini":
            count = self.get_count(provider, model)
            if model and "flash" in model.lower():
                return count >= settings.GEMINI_FLASH_LIMIT
            elif model and "pro" in model.lower():
                return count >= settings.GEMINI_PRO_LIMIT
            return count >= settings.GEMINI_FLASH_LIMIT

        # Остальные провайдеры пока без лимитов
        return False

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


# ============================================================================
# AI Provider Classes (Strategy Pattern)
# ============================================================================

class CompletionResult:
    """Унифицированный результат от любого провайдера"""
    def __init__(self, content: str):
        self.choices = [type('obj', (object,), {
            'message': type('obj', (object,), {'content': content})()
        })()]


class AIProvider(ABC):
    """Базовый класс для всех AI провайдеров"""
    
    def __init__(self, name: str, api_key: Optional[str] = None):
        self.name = name
        self.api_key = api_key
        self._client = None
    
    @abstractmethod
    def is_available(self) -> bool:
        """Проверяет, доступен ли провайдер"""
        pass
    
    @abstractmethod
    def get_model(self, is_enhancement: bool = False, task_type: str = None) -> str:
        """Возвращает модель для использования"""
        pass
    
    @abstractmethod
    def call(self, messages: List[dict], model: str, temperature: float, timeout: float = 60.0) -> str:
        """Выполняет запрос к API и возвращает текстовый ответ"""
        pass
    
    def should_retry_error(self, error: Exception) -> bool:
        """Определяет, стоит ли повторять запрос с другим провайдером"""
        error_str = str(error).lower()
        
        # Rate limit ошибки
        if isinstance(error, RateLimitError):
            return True
        if "429" in error_str or "rate limit" in error_str or "quota" in error_str:
            return True
        
        # Сетевые ошибки
        if isinstance(error, APIConnectionError):
            return True
        if "503" in error_str or "service unavailable" in error_str or "unavailable" in error_str:
            return True
        
        # Timeout и JSON ошибки не переключаем - это может быть проблема запроса
        return False


class GeminiProvider(AIProvider):
    """Провайдер для Gemini (Pro и Flash)"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__("gemini", api_key)
        if api_key:
            try:
                genai.configure(api_key=api_key)
                self._client = genai
                logger.info("✅ Initialized Gemini API client")
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini client: {e}")
    
    def is_available(self) -> bool:
        return self._client is not None
    
    def get_model(self, is_enhancement: bool = False, task_type: str = None) -> str:
        """Возвращает модель в зависимости от типа провайдера (pro/flash)"""
        # Это будет переопределено в подклассах
        if task_type == "enhancement" or is_enhancement:
            return settings.GEMINI_ENHANCEMENT_MODEL or settings.GEMINI_FLASH_MODEL
        elif task_type == "assistant":
            return settings.GEMINI_ASSISTANT_MODEL or settings.GEMINI_FLASH_MODEL
        else:
            return settings.GEMINI_GENERATION_MODEL or settings.GEMINI_PRO_MODEL
    
    def call(self, messages: List[dict], model: str, temperature: float, timeout: float = 60.0) -> str:
        """Вызывает Gemini API"""
        if not self._client:
            raise Exception("Gemini client not initialized")
        
        # Собираем промпт из messages
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
        
        model_obj = self._client.GenerativeModel(
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


class GeminiProProvider(GeminiProvider):
    """Провайдер для Gemini Pro (50 RPD лимит)"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.name = "gemini-pro"
    
    def get_model(self, is_enhancement: bool = False, task_type: str = None) -> str:
        return settings.GEMINI_PRO_MODEL


class GeminiFlashProvider(GeminiProvider):
    """Провайдер для Gemini Flash (250 RPD лимит)"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key)
        self.name = "gemini-flash"
    
    def get_model(self, is_enhancement: bool = False, task_type: str = None) -> str:
        return settings.GEMINI_FLASH_MODEL


class OpenAICompatibleProvider(AIProvider):
    """Базовый класс для OpenAI-совместимых провайдеров (Groq, Perplexity, OpenAI)"""
    
    def __init__(self, name: str, api_key: Optional[str] = None, base_url: Optional[str] = None):
        super().__init__(name, api_key)
        self.base_url = base_url
        if api_key:
            try:
                self._client = OpenAI(api_key=api_key, base_url=base_url)
                logger.info(f"✅ Initialized {name.upper()} API client")
            except Exception as e:
                logger.warning(f"Failed to initialize {name} client: {e}")
    
    def is_available(self) -> bool:
        return self._client is not None
    
    def call(self, messages: List[dict], model: str, temperature: float, timeout: float = 60.0) -> str:
        """Вызывает OpenAI-совместимый API"""
        if not self._client:
            raise Exception(f"{self.name} client not initialized")
        
        # Создаем копию messages для безопасности (не модифицируем оригинал)
        messages_copy = copy.deepcopy(messages)
        
        # Подготовка параметров запроса
        params = {
            "model": model,
            "messages": messages_copy,
            "temperature": temperature,
        }
        
        # JSON mode только для OpenAI
        if self.name == "openai":
            params["response_format"] = {"type": "json_object"}
        else:
            # Для других провайдеров добавляем инструкцию в промпт
            if len(messages_copy) > 0:
                last_msg = messages_copy[-1]
                if isinstance(last_msg, dict) and "content" in last_msg:
                    if "IMPORTANT: Return ONLY valid JSON" not in last_msg["content"]:
                        messages_copy[-1]["content"] += "\n\nIMPORTANT: Return ONLY valid JSON, no additional text or markdown formatting."
        
        completion = self._client.chat.completions.create(**params)
        return completion.choices[0].message.content


class GroqProvider(OpenAICompatibleProvider):
    """Провайдер для Groq
    
    Поддерживаемые модели:
    - llama-3.3-70b-versatile (по умолчанию для generation)
    - llama-3.1-8b-instant (по умолчанию для enhancement)
    - groq/compound (новая Compound система - быстрая, 450 T/SEC, 131K context)
    - groq/compound-mini (облегченная версия Compound)
    """
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            "groq",
            api_key,
            base_url="https://api.groq.com/openai/v1"
        )
    
    def get_model(self, is_enhancement: bool = False, task_type: str = None) -> str:
        """
        Возвращает модель Groq для использования
        
        Приоритет:
        1. Переменная окружения GROQ_MODEL / GROQ_ENHANCEMENT_MODEL
        2. Для enhancement: llama-3.1-8b-instant (быстрая)
        3. Для generation: llama-3.3-70b-versatile (качественная)
        
        Новые модели Compound можно использовать через переменные окружения:
        - export GROQ_MODEL="groq/compound" (для generation)
        - export GROQ_ENHANCEMENT_MODEL="groq/compound-mini" (для enhancement)
        """
        if is_enhancement or task_type == "enhancement":
            return os.getenv("GROQ_ENHANCEMENT_MODEL", "llama-3.1-8b-instant")
        return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")


class PerplexityProvider(OpenAICompatibleProvider):
    """Провайдер для Perplexity"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(
            "perplexity",
            api_key,
            base_url="https://api.perplexity.ai"
        )
    
    def get_model(self, is_enhancement: bool = False, task_type: str = None) -> str:
        if is_enhancement or task_type == "enhancement":
            return os.getenv("PERPLEXITY_ENHANCEMENT_MODEL", "llama-3.1-sonar-small-32k-online")
        return os.getenv("PERPLEXITY_MODEL", "llama-3.1-sonar-large-128k-online")


class OpenAIProvider(OpenAICompatibleProvider):
    """Провайдер для OpenAI"""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__("openai", api_key, base_url=None)
    
    def get_model(self, is_enhancement: bool = False, task_type: str = None) -> str:
        if is_enhancement or task_type == "enhancement":
            return os.getenv("OPENAI_ENHANCEMENT_MODEL", "gpt-4o-mini")
        return os.getenv("OPENAI_MODEL", "gpt-4o")


# ============================================================================
# Provider Registry
# ============================================================================

class ProviderRegistry:
    """Реестр всех доступных провайдеров"""
    
    def __init__(self):
        self.providers: Dict[str, AIProvider] = {}
        self._initialize_providers()
    
    def _initialize_providers(self):
        """Инициализирует все доступные провайдеры"""
        # Gemini провайдеры
        if settings.GEMINI_API_KEY:
            self.providers["gemini-pro"] = GeminiProProvider(settings.GEMINI_API_KEY)
            self.providers["gemini-flash"] = GeminiFlashProvider(settings.GEMINI_API_KEY)
            # Legacy поддержка
            self.providers["gemini"] = GeminiProvider(settings.GEMINI_API_KEY)
        
        # Groq
        if settings.GROQ_API_KEY:
            self.providers["groq"] = GroqProvider(settings.GROQ_API_KEY)
        
        # Perplexity
        if settings.PERPLEXITY_API_KEY:
            self.providers["perplexity"] = PerplexityProvider(settings.PERPLEXITY_API_KEY)
        
        # OpenAI
        if settings.OPENAI_API_KEY:
            self.providers["openai"] = OpenAIProvider(settings.OPENAI_API_KEY)
        
        if not self.providers:
            logger.warning("⚠️ No AI API clients configured. AI functions will be unavailable.")
    
    def get_provider(self, name: str) -> Optional[AIProvider]:
        """Возвращает провайдера по имени"""
        return self.providers.get(name)
    
    def get_available_providers(self) -> List[str]:
        """Возвращает список доступных провайдеров"""
        return [name for name, provider in self.providers.items() if provider.is_available()]


# Глобальный реестр провайдеров
provider_registry = ProviderRegistry()

# Обратная совместимость: старые переменные
clients: Dict[str, OpenAI] = {}
gemini_client = None
client: Optional[OpenAI] = None


def get_cache_key(requirements_text: str, prefix: str = "ai_map") -> str:
    """
    Генерирует ключ для кеша на основе текста требований.
    
    Нормализует текст перед хешированием для консистентности:
    - Убирает лишние пробелы в начале/конце строк
    - Нормализует множественные пробелы до одного
    - Сохраняет переносы строк (нормализует их до \n)
    - Использует UTF-8 кодировку
    
    Это гарантирует, что одинаковый текст с разными пробелами
    даст одинаковый хеш, но текст с переносами строк будет отличаться
    от текста без переносов (что правильно для кеширования).
    """
    import re
    
    # Нормализация текста для консистентного хеширования
    # Убираем лишние пробелы в начале/конце каждой строки
    lines = [line.strip() for line in requirements_text.split('\n')]
    # Убираем множественные пробелы внутри строк
    lines = [re.sub(r'\s+', ' ', line) for line in lines]
    # Собираем обратно, сохраняя переносы строк
    normalized_text = '\n'.join(lines)
    # Убираем лишние пробелы в начале/конце всего текста
    normalized_text = normalized_text.strip()
    
    text_hash = hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()
    cache_key = f"{prefix}:{text_hash}"
    logger.debug(f"Generated cache key: {cache_key[:50]}... (from text length: {len(requirements_text)})")
    return cache_key


def _get_model_for_provider(provider: str, is_enhancement: bool = False, task_type: str = None) -> str:
    """
    Возвращает модель для конкретного провайдера с учетом типа задачи
    
    DEPRECATED: Используйте provider.get_model() напрямую
    """
    provider_obj = provider_registry.get_provider(provider)
    if provider_obj:
        return provider_obj.get_model(is_enhancement, task_type)
    
    # Fallback на настройки из settings
    if is_enhancement:
        return settings.get_enhancement_model()
    return settings.API_MODEL


def _make_request_with_fallback(
    request_params: dict,
    providers: Optional[List[str]] = None,
    is_enhancement: bool = False,
    task_type: str = None
) -> Tuple[CompletionResult, str]:
    """
    Выполняет запрос к AI API с автоматическим fallback между провайдерами

    Args:
        request_params: Параметры запроса (model будет заменен для каждого провайдера)
        providers: Список провайдеров для попыток (по умолчанию определяется по task_type)
        is_enhancement: Используется ли для enhancement (влияет на выбор модели)
        task_type: Тип задачи ('enhancement', 'generation', 'assistant')

    Returns:
        tuple: (completion, provider_name) - результат и имя провайдера, который ответил

    Raises:
        HTTPException: Если все провайдеры недоступны
    """
    # Используем новую стратегию: провайдеры зависят от типа задачи
    if providers is None:
        effective_task_type = task_type or ("enhancement" if is_enhancement else "generation")
        providers = settings.get_providers_for_task(effective_task_type)
        logger.info(f"📋 Selected providers for task '{effective_task_type}': {providers}")

    if not providers:
        raise HTTPException(
            status_code=503,
            detail="No AI providers configured. Set GEMINI_API_KEY, GROQ_API_KEY, PERPLEXITY_API_KEY, or OPENAI_API_KEY."
        )

    # Очищаем старые записи rate limiter
    rate_limiter.cleanup_old_entries()

    last_error = None
    last_provider_name = None

    for provider_name in providers:
        # Логируем попытку использовать провайдера
        provider_index = providers.index(provider_name) + 1
        logger.info(f"🔄 [{provider_index}/{len(providers)}] Attempting provider: {provider_name.upper()}")
        
        # Получаем объект провайдера
        provider = provider_registry.get_provider(provider_name)
        if not provider or not provider.is_available():
            logger.info(f"⏩ Skipping {provider_name.upper()} - not available")
            continue
        
        # Получаем модель для этого провайдера
        model = provider.get_model(is_enhancement, task_type)
        
        # Проверяем, нужно ли пропустить провайдера из-за лимитов
        if rate_limiter.should_skip_provider(provider_name, model):
            logger.info(f"⏩ Skipping {provider_name.upper()} - approaching rate limit")
            continue

        try:
            logger.info(f"Trying {provider_name.upper()} with model {model}")

            # Подготовка параметров
            messages = copy.deepcopy(request_params.get("messages", []))
            temperature = request_params.get("temperature", 0.7)
            timeout = request_params.get("timeout", 60.0)

            # Добавляем инструкцию для JSON (для Gemini провайдеров, так как они не используют OpenAICompatibleProvider)
            is_gemini = provider_name in ("gemini", "gemini-pro", "gemini-flash")
            if is_gemini and len(messages) > 0:
                last_msg = messages[-1]
                if isinstance(last_msg, dict) and "content" in last_msg:
                    if "IMPORTANT: Return ONLY valid JSON" not in last_msg["content"]:
                        messages[-1]["content"] += "\n\nIMPORTANT: Return ONLY valid JSON, no additional text or markdown formatting."

            # Вызываем провайдера
            response_text = provider.call(messages, model, temperature, timeout)

            # Создаем объект completion для совместимости
            completion = CompletionResult(response_text)

            # Увеличиваем счетчик rate limiter
            rate_limiter.increment(provider_name, model)

            logger.info(f"✅ Successfully got response from {provider_name.upper()}")
            return completion, provider_name
            
        except APITimeoutError as e:
            last_error = e
            last_provider_name = provider_name
            logger.warning(f"❌ {provider_name.upper()} timeout: {e}. Trying next provider...")
            continue
        except (RateLimitError, APIConnectionError) as e:
            last_error = e
            last_provider_name = provider_name
            logger.warning(f"❌ {provider_name.upper()} failed ({type(e).__name__}): {e}. Trying next provider...")
            continue
        except APIError as e:
            if provider.should_retry_error(e):
                last_error = e
                last_provider_name = provider_name
                logger.warning(f"❌ {provider_name.upper()} failed (APIError): {e}. Trying next provider...")
                continue
            else:
                # Не переключаемся на другие провайдеры для этой ошибки
                raise HTTPException(
                    status_code=502,
                    detail=f"{provider_name.upper()} API error: {str(e)}"
                )
        except Exception as e:
            # Проверяем, стоит ли повторять с другим провайдером
            if provider.should_retry_error(e):
                last_error = e
                last_provider_name = provider_name
                logger.warning(f"❌ {provider_name.upper()} failed (unexpected): {e}. Trying next provider...")
                continue
            else:
                # Не переключаемся на другие провайдеры для этой ошибки
                raise HTTPException(
                    status_code=502,
                    detail=f"{provider_name.upper()} API error: {str(e)}"
                )
    
    # Все провайдеры не сработали
    if last_error and last_provider_name:
        error_msg = f"All AI providers failed. Last error from {last_provider_name.upper()}: {str(last_error)}"
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
    
    # Валидация размера входных данных (сначала валидируем входные данные)
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

    # Проверяем наличие доступных провайдеров
    available_providers = provider_registry.get_available_providers()
    if not available_providers:
        raise HTTPException(
            status_code=503,
            detail="AI API key not configured. Set GROQ_API_KEY, PERPLEXITY_API_KEY, or OPENAI_API_KEY environment variable."
        )
    
    # Проверяем кеш перед запросом к AI
    cache_key = get_cache_key(raw_text, prefix="enhance")
    if use_cache and redis_client:
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                logger.info(f"✅ Cache HIT for enhancement: {cache_key[:50]}...")
                return json.loads(cached_result)
            else:
                logger.info(f"Cache MISS for enhancement: {cache_key[:50]}...")
        except Exception as e:
            logger.warning(f"⚠️ Redis cache read failed for key {cache_key[:50]}...: {e}")
    elif use_cache and not redis_client:
        logger.warning(f"⚠️ Redis client not available, skipping cache check for enhancement")
    
    system_prompt = """Ты — эксперт по написанию product requirements для IT-продуктов.
Твоя задача: УЛУЧШИТЬ ФОРМУЛИРОВКИ требований пользователя, сохраняя ВСЮ информацию и структуру.

КРИТИЧЕСКИ ВАЖНО — СОХРАНЕНИЕ КОНТЕНТА:
- НЕ СОКРАЩАЙ и НЕ УДАЛЯЙ информацию из исходного текста
- СОХРАНЯЙ ВСЕ пункты, детали и специфику, которую указал пользователь
- Если пользователь написал 10 пунктов — в улучшенном тексте должно быть минимум 10 пунктов
- Улучшенный текст должен быть ТАКОЙ ЖЕ длины или ДЛИННЕЕ исходного

КРИТИЧЕСКИ ВАЖНО — СОХРАНЕНИЕ СТРУКТУРЫ:
- СОХРАНЯЙ структуру исходного текста: заголовки, списки, разделы, форматирование
- Если в исходном тексте есть разделы (Функционал, Ограничения, Целевая аудитория и т.д.) — сохрани их
- Если есть списки — сохрани их как списки (каждый пункт на новой строке с "- ")
- Если есть абзацы — сохрани их как абзацы
- НЕ превращай структурированный текст в один сплошной абзац
- Используй переносы строк (\\n) для разделения абзацев и разделов

ЧТО ДЕЛАТЬ:
1. Улучшай формулировки (делай яснее, конкретнее)
2. Добавляй очевидные типы продукта (web/mobile/desktop/SaaS)
3. Уточняй роли пользователей, если они упомянуты
4. Добавляй ТОЛЬКО очевидные детали (уведомления для бронирования, оплата для e-commerce)

ЧТО НЕ ДЕЛАТЬ:
- НЕ сокращай текст
- НЕ удаляй пункты
- НЕ объединяй несколько пунктов в один
- НЕ добавляй специфичные бизнес-правила (если не указаны пользователем)
- НЕ добавляй технологии (React, PostgreSQL и т.д.)
- НЕ добавляй детали UI/UX дизайна

ВАЖНО: Все тексты должны быть на РУССКОМ языке.
Возвращай ТОЛЬКО валидный JSON без дополнительного текста."""

    user_prompt = f"""Исходные требования пользователя:
\"\"\"
{raw_text}
\"\"\"

ТВОЯ ЗАДАЧА: Улучши формулировки, сохраняя ВСЮ информацию и структуру.

ПРАВИЛА:
1. СОХРАНИ ВСЕ пункты из исходного текста — ничего не удаляй
2. СОХРАНИ структуру: если есть разделы (Функционал:, Ограничения:) — оставь их
3. СОХРАНИ списки: если есть "- пункт", оставь как "- пункт"
4. Улучшенный текст должен быть НЕ КОРОЧЕ исходного
5. Можешь добавить очевидные детали, но НЕ удаляй существующие

ПРИМЕР ПРАВИЛЬНОГО улучшения:
Исходный текст:
\"\"\"
Функционал: Онлайн-бронирование столиков
- Просматривать рестораны на карте
- Выбирать дату и время

Ограничения:
- Бронирование за 30 дней вперёд
\"\"\"

Улучшенный текст (ПРАВИЛЬНО):
\"\"\"
Тип продукта: Мобильное приложение

Функционал: Онлайн-бронирование столиков в ресторанах
- Просматривать доступные рестораны на интерактивной карте города
- Выбирать дату, время и количество гостей для бронирования
- Получать подтверждение бронирования

Ограничения:
- Бронирование возможно за 30 дней вперёд
- Минимальное время для отмены — 2 часа до визита
\"\"\"

НЕПРАВИЛЬНО (так делать НЕЛЬЗЯ):
\"\"\"
Мобильное приложение для бронирования столиков. Пользователь может выбирать рестораны и бронировать.
\"\"\"
(Это плохо — потеряна структура и детали!)

Верни JSON:
{{
  "enhanced_text": "Полный улучшенный текст с сохранением ВСЕЙ структуры и ВСЕХ пунктов. Используй \\n для переносов строк. Списки оформляй как '- пункт'. Разделы оформляй как 'Название раздела:\\n- пункт 1\\n- пункт 2'",
  "added_aspects": ["Что добавлено, например: 'Добавлен тип продукта: mobile'"],
  "missing_info": ["Что рекомендуется уточнить"],
  "detected_product_type": "web/mobile/desktop/saas/other",
  "detected_roles": ["Список ролей"],
  "confidence": 0.85
}}

confidence: 0.9-1.0 (понятно), 0.7-0.9 (есть предположения), 0.5-0.7 (много неясностей)"""

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
                result_json = json.dumps(result, ensure_ascii=False)
                redis_client.setex(
                    cache_key,
                    86400,  # 24 часа
                    result_json
                )
                # Проверяем, что данные действительно записались
                verify = redis_client.get(cache_key)
                if verify:
                    logger.info(f"✅ Enhancement result cached in Redis: {cache_key[:50]}... (TTL: 86400s, size: {len(result_json)} bytes)")
                else:
                    logger.warning(f"⚠️ Redis cache write verification failed for key: {cache_key[:50]}...")
            except Exception as e:
                logger.error(f"❌ Redis cache write failed for key {cache_key[:50]}...: {e}", exc_info=True)
        elif use_cache and not redis_client:
            logger.warning(f"⚠️ Redis client not available, skipping cache write for key: {cache_key[:50]}...")
        
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

    # Валидация размера входных данных (сначала валидируем входные данные)
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

    # Проверяем наличие доступных провайдеров
    available_providers = provider_registry.get_available_providers()
    if not available_providers:
        raise HTTPException(
            status_code=503,
            detail="AI API key not configured. Set GROQ_API_KEY, PERPLEXITY_API_KEY, or OPENAI_API_KEY environment variable."
        )
    
    # Проверяем кеш перед запросом к AI
    cache_key = get_cache_key(requirements_text)
    if use_cache and redis_client:
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                logger.info(f"✅ Cache HIT for AI map: {cache_key[:50]}...")
                return json.loads(cached_result)
            else:
                logger.info(f"Cache MISS for AI map: {cache_key[:50]}...")
        except Exception as e:
            logger.warning(f"⚠️ Redis cache read failed for key {cache_key[:50]}...: {e}")
    elif use_cache and not redis_client:
        logger.warning(f"⚠️ Redis client not available, skipping cache check for AI map")
    
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
                result_json = json.dumps(result, ensure_ascii=False)
                redis_client.setex(
                    cache_key,
                    86400,  # 24 часа
                    result_json
                )
                # Проверяем, что данные действительно записались
                verify = redis_client.get(cache_key)
                if verify:
                    logger.info(f"✅ AI map result cached in Redis: {cache_key[:50]}... (TTL: 86400s, size: {len(result_json)} bytes)")
                else:
                    logger.warning(f"⚠️ Redis cache write verification failed for key: {cache_key[:50]}...")
            except Exception as e:
                logger.error(f"❌ Redis cache write failed for key {cache_key[:50]}...: {e}", exc_info=True)
        elif use_cache and not redis_client:
            logger.warning(f"⚠️ Redis client not available, skipping cache write for key: {cache_key[:50]}...")
        
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

    system_prompt = """Ты — эксперт по UX/UI и продуктовому дизайну. Твоя задача — создать детальную визуализацию интерфейса САМОГО ПРОДУКТА/ПРИЛОЖЕНИЯ в формате ASCII wireframe.

КРИТИЧЕСКИ ВАЖНО:
- Создавай wireframe для САМОГО ПРОДУКТА (приложения), описанного в карте историй, а НЕ для интерфейса управления картой историй
- НЕ упоминай в wireframe "карту пользовательских историй", "активности", "задачи", "истории" - это метаданные проекта
- Используй детальные ASCII схемы с box-drawing символами (┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼ │ ─)
- Показывай ВСЕ UI элементы: кнопки [текст], поля ввода [______], выпадающие списки [▼], иконки (📁, 🗑, ✏️)
- Визуализируй структуру папок, списков, форм, модальных окон
- Показывай несколько экранов/состояний если нужно (например, список → форма создания)
- Используй стрелки ↓ для показа переходов между экранами
- Будь максимально детальным и визуальным

СТРОГО ЗАПРЕЩЕНО:
- ❌ НЕ используй JSON формат ({"wireframe": "..."}, "layoutDescription": "...")
- ❌ НЕ используй текстовые описания со скобками [элемент] |\n| вместо визуальных схем
- ❌ НЕ создавай структурированные объекты вместо визуального ASCII wireframe
- ❌ НЕ используй формат типа {"uiElements": [...]} - это НЕ wireframe
- ❌ НЕ создавай wireframe для интерфейса управления картой историй - только для самого продукта

ОБЯЗАТЕЛЬНО:
- ✅ ТОЛЬКО визуальные ASCII схемы с box-drawing символами
- ✅ Визуальное представление интерфейса ПРОДУКТА, которое можно "увидеть"
- ✅ Структурированные блоки с рамками и четкими границами
- ✅ Wireframe должен отражать функциональность ПРОДУКТА из карты историй

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

    user_prompt = f"""Сгенерируй ДЕТАЛЬНЫЙ markdown wireframe для ПРОДУКТА/ПРИЛОЖЕНИЯ, описанного в карте пользовательских историй.

КРИТИЧЕСКИ ВАЖНО: 
Ты ДОЛЖЕН создать ВИЗУАЛЬНЫЙ ASCII wireframe для САМОГО ПРОДУКТА (приложения), а НЕ для интерфейса управления картой историй!
Например:
- Если карта про "бронирование билетов" → создай wireframe интерфейса бронирования билетов
- Если карта про "рекламную кампанию с баннером" → создай wireframe интерфейса управления рекламными кампаниями и баннерами
- Если карта про "онлайн-бронирование столиков" → создай wireframe интерфейса бронирования столиков в ресторане

НЕ создавай wireframe для интерфейса управления картой историй (активности, задачи, истории)!
НЕ упоминай в wireframe слова "карта пользовательских историй", "активности", "задачи", "истории" - это метаданные проекта, а не часть продукта!
НЕ создавай JSON объекты или текстовые описания со скобками - это НЕ wireframe!

ВАЖНО: Создай визуально понятные ASCII схемы, которые показывают:
- Структуру интерфейса САМОГО ПРОДУКТА (header, sidebar, main area) с box-drawing символами
- Все кнопки, поля ввода, выпадающие списки как визуальные элементы
- Иконки и визуальные элементы
- Несколько экранов/состояний если нужно (список → детали → форма редактирования)
- Стрелки для показа переходов

Пример ПРАВИЛЬНОГО детального wireframe (ИМЕННО ТАК нужно делать):
{example_ascii}

НЕПРАВИЛЬНЫЙ формат (НЕ ДЕЛАЙ ТАК):
{{"wireframe": "[Кампании] [Статистика] |\\n| Баннер 1"}}
"layoutDescription": "..."
"uiElements": [...]

Структура ответа (строго):
1) ДЕТАЛЬНАЯ ASCII схема в блоке ```ascii ... ``` - покажи главный экран ПРОДУКТА/ПРИЛОЖЕНИЯ
   ОБЯЗАТЕЛЬНО используй box-drawing символы (┌ ┐ └ ┘ ├ ┤ ┬ ┴ ┼ │ ─) для создания визуальных рамок
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

Сгенерируй wireframe, который визуально показывает как будет выглядеть интерфейс САМОГО ПРОДУКТА/ПРИЛОЖЕНИЯ, описанного в этой карте пользовательских историй.
ПОМНИ: wireframe - это ВИЗУАЛЬНАЯ схема ПРОДУКТА, а не JSON описание и не интерфейс управления картой историй!
"""

    request_params = {
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.5,  # Снижено для более предсказуемых и структурированных wireframes
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
    
    # Валидация промпта (сначала валидируем входные данные)
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

    # Проверяем наличие доступных провайдеров
    available_providers = provider_registry.get_available_providers()
    if not available_providers:
        raise HTTPException(
            status_code=503,
            detail="AI API key not configured. Set GROQ_API_KEY, PERPLEXITY_API_KEY, or OPENAI_API_KEY environment variable."
        )
    
    # Проверяем кеш
    cache_key = get_cache_key(f"improve:{story_data.get('title', '')}:{user_prompt}:{action}")
    if use_cache and redis_client:
        try:
            cached_result = redis_client.get(cache_key)
            if cached_result:
                logger.info(f"✅ Cache HIT for improvement: {cache_key[:50]}...")
                return json.loads(cached_result)
            else:
                logger.info(f"Cache MISS for improvement: {cache_key[:50]}...")
        except Exception as e:
            logger.warning(f"⚠️ Redis cache read failed for key {cache_key[:50]}...: {e}")
    elif use_cache and not redis_client:
        logger.warning(f"⚠️ Redis client not available, skipping cache check for improvement")
    
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
                result_json = json.dumps(result, ensure_ascii=False)
                redis_client.setex(
                    cache_key,
                    3600,  # 1 час
                    result_json
                )
                # Проверяем, что данные действительно записались
                verify = redis_client.get(cache_key)
                if verify:
                    logger.info(f"✅ Improvement result cached in Redis: {cache_key[:50]}... (TTL: 3600s, size: {len(result_json)} bytes)")
                else:
                    logger.warning(f"⚠️ Redis cache write verification failed for key: {cache_key[:50]}...")
            except Exception as e:
                logger.error(f"❌ Redis cache write failed for key {cache_key[:50]}...: {e}", exc_info=True)
        elif use_cache and not redis_client:
            logger.warning(f"⚠️ Redis client not available, skipping cache write for key: {cache_key[:50]}...")
        
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


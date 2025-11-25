"""
AI service - генерация User Story Map через AI API
"""
import json
import hashlib
import logging
from typing import Optional
from fastapi import HTTPException
from openai import OpenAI, RateLimitError, APIError, APITimeoutError, APIConnectionError

from config import settings

logger = logging.getLogger(__name__)

# Инициализация AI клиента
client: Optional[OpenAI] = None
if settings.get_api_key():
    if settings.API_PROVIDER == "perplexity":
        client = OpenAI(
            api_key=settings.get_api_key(),
            base_url="https://api.perplexity.ai"
        )
        logger.info("Initialized Perplexity API client")
    else:
        client = OpenAI(api_key=settings.get_api_key())
        logger.info("Initialized OpenAI API client")
else:
    logger.warning("AI API key not configured")


def get_cache_key(requirements_text: str) -> str:
    """Генерирует ключ для кеша на основе текста требований"""
    text_hash = hashlib.sha256(requirements_text.encode()).hexdigest()
    return f"ai_map:{text_hash}"


def generate_ai_map(requirements_text: str, redis_client=None, use_cache: bool = True) -> dict:
    """Отправляет запрос в AI API и получает структурированную User Story Map"""
    
    if not client:
        raise HTTPException(
            status_code=503,
            detail="AI API key not configured. Set OPENAI_API_KEY or PERPLEXITY_API_KEY environment variable."
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
        logger.info(f"Generating map for requirements (length: {len(requirements_text)} chars) using {settings.API_PROVIDER}")
        
        # Подготовка параметров запроса
        request_params = {
            "model": settings.API_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": settings.API_TEMPERATURE,
            "timeout": 60.0,  # 60 секунд таймаут
        }
        
        # Perplexity поддерживает JSON mode, но может требовать другой формат
        if settings.API_PROVIDER == "openai":
            request_params["response_format"] = {"type": "json_object"}
        else:
            # Для Perplexity добавляем инструкцию в промпт для JSON
            user_prompt = user_prompt + "\n\nIMPORTANT: Return ONLY valid JSON, no additional text or markdown formatting."
        
        completion = client.chat.completions.create(**request_params)
        
        response_text = completion.choices[0].message.content
        logger.info("Successfully received AI response")
        
        # Очистка ответа от возможных markdown форматирования (для Perplexity)
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]  # Убираем ```json
        if response_text.startswith("```"):
            response_text = response_text[3:]  # Убираем ```
        if response_text.endswith("```"):
            response_text = response_text[:-3]  # Убираем закрывающий ```
        response_text = response_text.strip()
        
        result = json.loads(response_text)
        
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
        
    except RateLimitError:
        logger.error(f"{settings.API_PROVIDER.upper()} rate limit exceeded")
        raise HTTPException(
            status_code=429,
            detail=f"{settings.API_PROVIDER.upper()} rate limit exceeded. Please try again later."
        )
    except APITimeoutError:
        logger.error(f"{settings.API_PROVIDER.upper()} request timeout")
        raise HTTPException(
            status_code=504,
            detail="Request to AI service timed out. Please try again."
        )
    except APIConnectionError as e:
        logger.error(f"{settings.API_PROVIDER.upper()} connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to AI service. Please check your internet connection."
        )
    except APIError as e:
        logger.error(f"{settings.API_PROVIDER.upper()} API error: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"AI service error: {str(e)}"
        )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from AI: {e}")
        raise HTTPException(
            status_code=502,
            detail="Invalid response format from AI service. Please try again."
        )
    except Exception as e:
        logger.error(f"Unexpected error in AI generation: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


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
    
    if not client:
        raise HTTPException(
            status_code=503,
            detail="AI API key not configured. Set OPENAI_API_KEY or PERPLEXITY_API_KEY environment variable."
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
        'details': 'Добавь больше деталей и конкретики в описание истории. Расширь контекст использования.',
        'criteria': 'Улучши и расширь acceptance criteria. Сделай их более конкретными, измеримыми и полными.',
        'split': 'Проанализируй историю и предложи, как её можно разделить на 2-3 более мелкие, независимые истории.',
        'edge_cases': 'Добавь edge cases (граничные случаи) в acceptance criteria. Подумай об ошибках, крайних ситуациях, offline режиме.'
    }
    
    action_instruction = action_prompts.get(action, '')
    
    system_prompt = """Ты — эксперт Product Manager и Business Analyst. 
Твоя задача — улучшать пользовательские истории (User Stories) на основе запросов пользователя.

ВАЖНО: 
- Все тексты должны быть на РУССКОМ языке
- Сохраняй структуру и формат истории
- Будь конкретным и практичным
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

Улучши эту историю согласно запросу пользователя.

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
  "title": "Улучшенное название",
  "description": "Улучшенное описание",
  "priority": "MVP/Release 1/Later",
  "acceptance_criteria": ["Критерий 1", "Критерий 2", ...],
  "suggestion": "Краткое пояснение изменений"
}}

Верни ТОЛЬКО валидный JSON, без markdown форматирования."""
    
    try:
        logger.info(f"Improving story with prompt length: {len(user_prompt)} chars, action: {action}")
        
        request_params = {
            "model": settings.API_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_full_prompt},
            ],
            "temperature": 0.7,
            "timeout": 30.0,
        }
        
        if settings.API_PROVIDER == "openai":
            request_params["response_format"] = {"type": "json_object"}
        
        completion = client.chat.completions.create(**request_params)
        response_text = completion.choices[0].message.content
        logger.info("Successfully received AI improvement response")
        
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
        
    except RateLimitError:
        logger.error(f"{settings.API_PROVIDER.upper()} rate limit exceeded")
        raise HTTPException(
            status_code=429,
            detail=f"{settings.API_PROVIDER.upper()} rate limit exceeded. Please try again later."
        )
    except APITimeoutError:
        logger.error(f"{settings.API_PROVIDER.upper()} request timeout")
        raise HTTPException(
            status_code=504,
            detail="Request to AI service timed out. Please try again."
        )
    except APIConnectionError as e:
        logger.error(f"{settings.API_PROVIDER.upper()} connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail="Unable to connect to AI service. Please check your internet connection."
        )
    except APIError as e:
        logger.error(f"{settings.API_PROVIDER.upper()} API error: {e}")
        raise HTTPException(
            status_code=502,
            detail=f"AI service error: {str(e)}"
        )
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from AI: {e}")
        raise HTTPException(
            status_code=502,
            detail="Invalid response format from AI service. Please try again."
        )
    except Exception as e:
        logger.error(f"Unexpected error in AI improvement: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Unexpected error: {str(e)}"
        )


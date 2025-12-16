"""
Epic service - AI группировка пользовательских историй в эпики
"""
import json
import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from models import UserStory, Epic, Project
from services.ai_service import _make_request_with_fallback, provider_registry

logger = logging.getLogger(__name__)


def _prepare_stories_for_prompt(stories: List[UserStory], project_description: Optional[str] = None) -> str:
    """
    Подготавливает текстовое представление историй для AI промпта
    
    Args:
        stories: Список историй для группировки
        project_description: Описание проекта (опционально)
    
    Returns:
        str: Форматированный текст для промпта
    """
    lines = []
    
    if project_description:
        lines.append(f"Описание проекта: {project_description}\n")
    
    lines.append(f"Всего историй для группировки: {len(stories)}\n")
    lines.append("Список историй:\n")
    
    for idx, story in enumerate(stories, 1):
        lines.append(f"{idx}. {story.title}")
        if story.description:
            lines.append(f"   Описание: {story.description}")
        if story.acceptance_criteria:
            ac_text = "; ".join(story.acceptance_criteria[:3])  # Первые 3 критерия
            if len(story.acceptance_criteria) > 3:
                ac_text += f" (и еще {len(story.acceptance_criteria) - 3})"
            lines.append(f"   Критерии приемки: {ac_text}")
        if story.priority:
            lines.append(f"   Приоритет: {story.priority}")
        lines.append("")  # Пустая строка между историями
    
    return "\n".join(lines)


def group_stories_into_epics(
    stories: List[UserStory],
    project: Project,
    min_epics: int = 3,
    max_epics: int = 7,
    redis_client=None,
    use_cache: bool = True
) -> List[Dict]:
    """
    AI группирует истории в 3-7 эпиков с confidence score.
    
    Args:
        stories: Список историй для группировки (будет отсортирован по ID)
        project: Проект (для получения описания)
        min_epics: Минимальное количество эпиков (по умолчанию 3)
        max_epics: Максимальное количество эпиков (по умолчанию 7)
        redis_client: Redis клиент для кеширования (опционально)
        use_cache: Использовать ли кеш (по умолчанию True)
    
    Returns:
        List[Dict]: Список эпиков с полями:
            - title: Название эпика
            - description: Описание эпика
            - story_ids: Список ID историй в этом эпике
            - confidence: Уверенность AI в группировке (0.0-1.0)
    
    Raises:
        HTTPException: Если группировка не удалась
    """
    if not stories:
        logger.warning("No stories provided for epic grouping")
        return []
    
    # Валидация min/max
    if min_epics > max_epics:
        raise ValueError("min_epics must be <= max_epics")
    
    if len(stories) < min_epics:
        logger.warning(f"Not enough stories ({len(stories)}) for {min_epics} epics, using fallback")
        return _fallback_grouping(stories)
    
    # Сортируем истории по ID для консистентности
    stories = sorted(stories, key=lambda s: s.id)
    """
    AI группирует истории в 3-7 эпиков с confidence score.
    
    Args:
        stories: Список историй для группировки
        project: Проект (для получения описания)
        min_epics: Минимальное количество эпиков (по умолчанию 3)
        max_epics: Максимальное количество эпиков (по умолчанию 7)
        redis_client: Redis клиент для кеширования (опционально)
        use_cache: Использовать ли кеш (по умолчанию True)
    
    Returns:
        List[Dict]: Список эпиков с полями:
            - title: Название эпика
            - description: Описание эпика
            - story_ids: Список ID историй в этом эпике
            - confidence: Уверенность AI в группировке (0.0-1.0)
    
    Raises:
        HTTPException: Если группировка не удалась
    """
    if not stories:
        logger.warning("No stories provided for epic grouping")
        return []
    
    if len(stories) < 3:
        # Если историй меньше 3, создаем один эпик
        logger.info(f"Only {len(stories)} stories, creating single epic")
        return [{
            "title": "Все истории",
            "description": f"Эпик содержит все {len(stories)} истории проекта",
            "story_ids": [story.id for story in stories],
            "confidence": 1.0
        }]
    
    # Проверяем наличие доступных провайдеров
    available_providers = provider_registry.get_available_providers()
    if not available_providers:
        logger.warning("No AI providers available, using fallback grouping")
        return _fallback_grouping(stories)
    
    # Подготавливаем данные для промпта
    project_description = project.raw_requirements or project.name or ""
    stories_text = _prepare_stories_for_prompt(stories, project_description)
    
    # Проверяем кеш (если включен)
    if use_cache and redis_client:
        try:
            import hashlib
            cache_key = f"epic_grouping:{hashlib.sha256(stories_text.encode()).hexdigest()}"
            cached_result = redis_client.get(cache_key)
            if cached_result:
                logger.info("Using cached epic grouping result")
                return json.loads(cached_result)
        except Exception as e:
            logger.warning(f"Redis cache read failed: {e}")
    
    # Создаем промпт для AI
    system_prompt = """Ты — эксперт Product Manager и Business Analyst, специализирующийся на группировке пользовательских историй в эпики (Epics).

Твоя задача — проанализировать список пользовательских историй и сгруппировать их в логические эпики.

ЭПИК (Epic) — это большая функциональная область или пользовательский сценарий, который объединяет несколько связанных историй.

ПРАВИЛА ГРУППИРОВКИ:
1. Группируй истории по функциональной близости (например, все истории про авторизацию)
2. Группируй по пользовательским сценариям (например, весь процесс оформления заказа)
3. Группируй по доменам/модулям продукта (например, все истории про админ-панель)
4. Каждый эпик должен содержать 2-10 историй (в среднем 3-5)
5. История может быть только в одном эпике
6. Все истории должны быть распределены по эпикам

ВАЖНО:
- Все тексты должны быть на РУССКОМ языке
- Названия эпиков должны быть понятными и отражать функциональность
- Описания эпиков должны объяснять, что объединяет истории в этом эпике
- Confidence score: 0.9-1.0 (четкая группировка), 0.7-0.9 (есть сомнения), 0.5-0.7 (неочевидная группировка)
- Возвращай ТОЛЬКО валидный JSON без дополнительного текста"""

    user_prompt = f"""Проанализируй следующие пользовательские истории и сгруппируй их в {min_epics}-{max_epics} логических эпиков.

{stories_text}

ТВОЯ ЗАДАЧА:
1. Проанализируй все истории
2. Определи логические группы (по функциональности, сценариям или доменам)
3. Создай {min_epics}-{max_epics} эпиков
4. Распредели все истории по эпикам (каждая история только в одном эпике)
5. Для каждого эпика укажи confidence score (0.0-1.0)

Верни ТОЛЬКО валидный JSON в формате:
{{
  "epics": [
    {{
      "title": "Название эпика (например, 'Авторизация и безопасность')",
      "description": "Краткое описание, что объединяет истории в этом эпике",
      "story_ids": [1, 2, 3],
      "confidence": 0.85
    }},
    {{
      "title": "Название второго эпика",
      "description": "Описание второго эпика",
      "story_ids": [4, 5, 6],
      "confidence": 0.90
    }}
  ]
}}

ВАЖНО:
- story_ids должны соответствовать порядковым номерам историй из списка (1, 2, 3...)
- Все истории должны быть распределены (не должно быть историй без эпика)
- Если история не подходит ни к одному эпику, создай эпик "Прочее" с confidence 0.5
- Confidence должен отражать уверенность в правильности группировки"""

    try:
        logger.info(f"Grouping {len(stories)} stories into {min_epics}-{max_epics} epics")
        
        request_params = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.5,  # Меньше креатива, больше точности
            "timeout": 60.0,
        }
        
        # Используем fallback механизм из ai_service
        completion, used_provider = _make_request_with_fallback(
            request_params,
            providers=available_providers,
            is_enhancement=False,
            task_type="generation"
        )
        
        response_text = completion.choices[0].message.content
        logger.info(f"Successfully received epic grouping response from {used_provider.upper()}")
        
        # Очистка ответа от markdown
        response_text = response_text.strip()
        if response_text.startswith("```json"):
            response_text = response_text[7:]
        if response_text.startswith("```"):
            response_text = response_text[3:]
        if response_text.endswith("```"):
            response_text = response_text[:-3]
        response_text = response_text.strip()
        
        # Парсим JSON
        result = json.loads(response_text)
        
        # Валидация структуры
        if not isinstance(result, dict) or "epics" not in result:
            logger.error(f"Invalid response structure: {result.keys() if isinstance(result, dict) else type(result)}")
            return _fallback_grouping(stories)
        
        epics = result.get("epics", [])
        if not isinstance(epics, list):
            logger.error(f"Epics is not a list: {type(epics)}")
            return _fallback_grouping(stories)
        
        # Валидация и преобразование story_ids (из порядковых номеров в реальные ID)
        validated_epics = []
        all_story_ids_used = set()
        
        for epic in epics:
            if not isinstance(epic, dict):
                continue
            
            story_indices = epic.get("story_ids", [])
            if not isinstance(story_indices, list):
                continue
            
            # Преобразуем порядковые номера (1-based) в реальные ID историй
            real_story_ids = []
            for idx in story_indices:
                if isinstance(idx, int) and 1 <= idx <= len(stories):
                    story = stories[idx - 1]  # Индекс в списке (0-based)
                    real_story_ids.append(story.id)
                    all_story_ids_used.add(story.id)
            
            if not real_story_ids:
                continue
            
            validated_epic = {
                "title": epic.get("title", "Без названия"),
                "description": epic.get("description", ""),
                "story_ids": real_story_ids,
                "confidence": float(epic.get("confidence", 0.5))
            }
            validated_epics.append(validated_epic)
        
        # Проверяем, что все истории распределены
        all_story_ids = {story.id for story in stories}
        ungrouped_story_ids = all_story_ids - all_story_ids_used
        
        if ungrouped_story_ids:
            logger.warning(f"Some stories were not grouped: {ungrouped_story_ids}")
            # Создаем эпик "Прочее" для нераспределенных историй
            validated_epics.append({
                "title": "Прочее",
                "description": "Истории, которые не были автоматически сгруппированы",
                "story_ids": list(ungrouped_story_ids),
                "confidence": 0.5
            })
        
        # Кешируем результат на 24 часа
        if use_cache and redis_client:
            try:
                import hashlib
                cache_key = f"epic_grouping:{hashlib.sha256(stories_text.encode()).hexdigest()}"
                redis_client.setex(
                    cache_key,
                    86400,  # 24 часа
                    json.dumps(validated_epics)
                )
                logger.info("Epic grouping result cached in Redis")
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")
        
        logger.info(f"Successfully grouped {len(stories)} stories into {len(validated_epics)} epics")
        return validated_epics
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from AI epic grouping: {e}")
        logger.info("Falling back to simple grouping")
        return _fallback_grouping(stories)
    except Exception as e:
        error_msg = str(e) if str(e) else repr(e)
        logger.error(f"Unexpected error in epic grouping: {error_msg}", exc_info=True)
        logger.info("Falling back to simple grouping")
        return _fallback_grouping(stories)


def _fallback_grouping(stories: List[UserStory]) -> List[Dict]:
    """
    Простая fallback группировка, если AI не может сгруппировать.
    Группирует по Activity (если доступно) или создает один эпик.
    
    Args:
        stories: Список историй
    
    Returns:
        List[Dict]: Список эпиков
    """
    logger.info("Using fallback grouping strategy")
    
    # Пытаемся сгруппировать по Activity
    activity_groups = {}
    for story in stories:
        if story.task and story.task.activity:
            activity_id = story.task.activity.id
            activity_title = story.task.activity.title or f"Activity {activity_id}"
            
            if activity_id not in activity_groups:
                activity_groups[activity_id] = {
                    "title": activity_title,
                    "description": f"Эпик на основе активности: {activity_title}",
                    "story_ids": [],
                    "confidence": 0.6
                }
            activity_groups[activity_id]["story_ids"].append(story.id)
    
    if activity_groups:
        return list(activity_groups.values())
    
    # Если группировка по Activity не удалась, создаем один эпик
    return [{
        "title": "Все истории",
        "description": f"Эпик содержит все {len(stories)} истории проекта",
        "story_ids": [story.id for story in stories],
        "confidence": 0.5
    }]


def create_epics_from_grouping(
    db: Session,
    project: Project,
    epics_data: List[Dict]
) -> List[Epic]:
    """
    Создает объекты Epic в БД на основе данных группировки.
    
    Args:
        db: Сессия БД
        project: Проект
        epics_data: Список данных эпиков из group_stories_into_epics()
    
    Returns:
        List[Epic]: Список созданных эпиков
    
    Raises:
        Exception: При ошибке транзакции (откатывает все изменения)
    """
    try:
        created_epics = []
        assigned_story_ids = set()  # Для отслеживания дубликатов
        
        for idx, epic_data in enumerate(epics_data):
            story_ids = epic_data.get("story_ids", [])
            
            # Пропускаем пустые эпики
            if not story_ids:
                logger.warning(f"Skipping epic '{epic_data.get('title', 'Unknown')}' - no stories")
                continue
            
            # Убираем дубликаты
            story_ids = list(set(story_ids))
            
            epic = Epic(
                project_id=project.id,
                title=epic_data["title"],
                description=epic_data.get("description", ""),
                confidence_score=epic_data.get("confidence", 0.5),
                position=idx
            )
            db.add(epic)
            db.flush()  # Получаем ID эпика
            
            # Присваиваем истории к эпику
            for story_id in story_ids:
                # Проверка на дубликаты
                if story_id in assigned_story_ids:
                    logger.warning(f"Story {story_id} already assigned to another epic, skipping")
                    continue
                
                story = db.query(UserStory).filter(UserStory.id == story_id).first()
                if story and story.task and story.task.activity:
                    if story.task.activity.project_id == project.id:
                        if story.epic_id is not None:
                            logger.warning(f"Story {story_id} already has epic_id {story.epic_id}, overwriting")
                        story.epic_id = epic.id
                        assigned_story_ids.add(story_id)
                    else:
                        logger.warning(f"Story {story_id} belongs to different project")
                else:
                    logger.warning(f"Story {story_id} not found or invalid")
            
            created_epics.append(epic)
        
        db.commit()
        logger.info(f"Created {len(created_epics)} epics in database")
        
        return created_epics
    except Exception as e:
        db.rollback()
        logger.error(f"Error creating epics, rolling back: {e}", exc_info=True)
        raise


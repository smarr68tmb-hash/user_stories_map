"""
AI Agent service - MVP версия агента для генерации User Story Map

Простой агентный подход:
1. Генерация (один запрос к AI)
2. Валидация структуры (интегрировано с validation_service и similarity_service)
3. Одно исправление если есть критические ошибки

Это MVP версия для тестирования концепции агента.
Фаза 1: Интеграция с существующими сервисами валидации и similarity.
"""
import json
import logging
import time
from typing import Dict, List, Optional, Any
from datetime import datetime

from services.ai_service import (
    _make_request_with_fallback,
    get_cache_key,
    rate_limiter
)
from services.validation_service import validate_project_map
from services.similarity_service import analyze_similarity
from models import Project, Activity, UserTask, UserStory, Release
from schemas.analysis import ValidationResult, IssueSeverity
from config import settings

logger = logging.getLogger(__name__)


class SimpleAgent:
    """
    Простой AI-агент для генерации User Story Map

    MVP Flow:
    1. Generate - генерирует карту одним запросом
    2. Validate - валидирует структуру
    3. Fix - одна попытка исправить критические ошибки
    """

    def __init__(
        self,
        model: Optional[str] = None,
        enable_validation: bool = True,
        enable_fix: bool = True,
        redis_client=None
    ):
        """
        Args:
            model: Название модели (если None, используется из настроек)
            enable_validation: Включить валидацию после генерации
            enable_fix: Включить исправление ошибок
            redis_client: Redis клиент для кеширования
        """
        self.model = model
        self.enable_validation = enable_validation
        self.enable_fix = enable_fix
        self.redis_client = redis_client

        # Метрики для отслеживания
        self.metrics = {
            "start_time": None,
            "end_time": None,
            "total_time": 0.0,
            "generation_time": 0.0,
            "validation_time": 0.0,
            "fix_time": 0.0,
            "provider_used": None,
            "fix_attempted": False,
            "fix_successful": False,
            "critical_issues_before_fix": 0,
            "critical_issues_after_fix": 0,
            "similarity_groups_found": 0,
            "duplicates_found": 0
        }

    def generate_map(
        self,
        requirements: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Генерирует User Story Map через агента

        Args:
            requirements: Текст требований пользователя
            use_cache: Использовать кеш для генерации

        Returns:
            dict: {
                "productName": str,
                "personas": List[str],
                "map": List[Dict],  # Activities с Tasks и Stories
                "metadata": {
                    "agent_version": "mvp",
                    "validation": {...},
                    "metrics": {...}
                }
            }
        """
        self.metrics["start_time"] = time.time()
        logger.info("🤖 SimpleAgent: Starting map generation")

        try:
            # Step 1: Генерация
            logger.info("📝 Step 1/3: Generating map structure")
            gen_start = time.time()
            result = self._generate(requirements, use_cache)
            self.metrics["generation_time"] = time.time() - gen_start
            self.metrics["provider_used"] = result.get("provider_used")

            # Step 2: Валидация
            validation_result = None
            if self.enable_validation:
                logger.info("✅ Step 2/3: Validating structure")
                val_start = time.time()
                validation_result = self._validate(result)
                self.metrics["validation_time"] = time.time() - val_start

                # Считаем критические ошибки
                # Поддерживаем как старый формат (dict), так и новый (ValidationIssue)
                issues = validation_result.get("issues", [])
                critical_issues = []
                for issue in issues:
                    # Если это ValidationIssue объект, конвертируем в dict
                    if hasattr(issue, 'severity'):
                        severity = issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity)
                        if severity == "error":  # ERROR = critical
                            critical_issues.append({
                                "type": issue.type.value if hasattr(issue.type, 'value') else str(issue.type),
                                "severity": severity,
                                "message": issue.message,
                                "location": issue.location
                            })
                    elif isinstance(issue, dict):
                        if issue.get("severity") in ["critical", "error"]:
                            critical_issues.append(issue)
                
                self.metrics["critical_issues_before_fix"] = len(critical_issues)
                
                # Обновляем метрики similarity
                similarity_result = validation_result.get("similarity", {})
                if similarity_result:
                    stats = similarity_result.get("stats", {})
                    self.metrics["similarity_groups_found"] = stats.get("similar_groups_found", 0)
                    self.metrics["duplicates_found"] = stats.get("duplicates_found", 0)

                # Step 3: Исправление (если есть критические ошибки или дубликаты)
                should_fix = False
                fix_reasons = []
                
                if critical_issues:
                    should_fix = True
                    fix_reasons.append(f"{len(critical_issues)} критических ошибок")
                
                # Также исправляем если найдены дубликаты
                duplicates_count = self.metrics.get("duplicates_found", 0)
                if duplicates_count > 0:
                    should_fix = True
                    fix_reasons.append(f"{duplicates_count} дубликатов")
                
                if self.enable_fix and should_fix:
                    logger.info(f"🔧 Step 3/3: Fixing ({', '.join(fix_reasons)})")
                    fix_start = time.time()
                    self.metrics["fix_attempted"] = True

                    # Передаем и critical issues, и similarity info
                    similarity_info = validation_result.get("similarity")
                    result = self._fix(result, critical_issues, similarity_info)
                    self.metrics["fix_time"] = time.time() - fix_start

                    # Повторная валидация после исправления
                    validation_result = self._validate(result)
                    issues_after = validation_result.get("issues", [])
                    critical_after = []
                    for issue in issues_after:
                        if hasattr(issue, 'severity'):
                            severity = issue.severity.value if hasattr(issue.severity, 'value') else str(issue.severity)
                            if severity == "error":
                                critical_after.append(issue)
                        elif isinstance(issue, dict) and issue.get("severity") in ["critical", "error"]:
                            critical_after.append(issue)
                    
                    # Обновляем метрики similarity после исправления
                    similarity_after = validation_result.get("similarity", {})
                    if similarity_after:
                        stats_after = similarity_after.get("stats", {})
                        self.metrics["similarity_groups_found"] = stats_after.get("similar_groups_found", 0)
                        self.metrics["duplicates_found"] = stats_after.get("duplicates_found", 0)
                    
                    self.metrics["critical_issues_after_fix"] = len(critical_after)
                    self.metrics["fix_successful"] = len(critical_after) < len(critical_issues)
                else:
                    logger.info("✨ Step 3/3: No fixes needed")

            # Финализация
            self.metrics["end_time"] = time.time()
            self.metrics["total_time"] = self.metrics["end_time"] - self.metrics["start_time"]

            # Добавляем метаданные
            result["metadata"] = {
                "agent_version": "mvp",
                "validation": validation_result,
                "metrics": self.metrics
            }

            logger.info(f"🎉 SimpleAgent: Generation completed in {self.metrics['total_time']:.2f}s")
            return result

        except Exception as e:
            logger.error(f"❌ SimpleAgent failed: {e}", exc_info=True)
            raise

    def _generate(
        self,
        requirements: str,
        use_cache: bool = True
    ) -> Dict[str, Any]:
        """
        Step 1: Генерирует карту одним запросом к AI

        Args:
            requirements: Текст требований
            use_cache: Использовать кеш

        Returns:
            dict: Сгенерированная структура карты
        """
        # Проверяем кеш
        cache_key = get_cache_key(requirements, prefix="agent:mvp")
        if use_cache and self.redis_client:
            try:
                cached = self.redis_client.get(cache_key)
                if cached:
                    logger.info("Using cached agent result")
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Redis cache read failed: {e}")

        # Промпт для агента (улучшенный)
        system_prompt = """Ты — эксперт Product Manager и Business Analyst, специализирующийся на User Story Mapping (USM).
Твоя задача — создавать качественные User Story Maps из требований к продукту.

КРИТИЧЕСКИ ВАЖНО:
1. Все тексты на РУССКОМ языке
2. Минимум 3-4 Activities (высокоуровневые цели)
3. 2-3 Tasks на каждую Activity
4. 2-4 Stories на каждую Task
5. Каждая Story должна иметь acceptance_criteria (2-4 критерия)
6. Приоритеты: "MVP" для базовых функций, "Release 1" для важных, "Later" для остальных

Возвращай ТОЛЬКО валидный JSON без дополнительного текста или markdown."""

        user_prompt = f"""Создай User Story Map для следующего продукта:

\"\"\"
{requirements}
\"\"\"

Верни JSON в точно такой структуре:
{{
  "productName": "Название продукта",
  "personas": ["Персона 1", "Персона 2"],
  "map": [
    {{
      "activity": "Название Activity",
      "tasks": [
        {{
          "taskTitle": "Название Task",
          "stories": [
            {{
              "title": "Название Story",
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
}}

ВАЖНО:
- Минимум 3 Activities
- Каждая Task должна иметь минимум 2 Stories
- Каждая Story должна иметь минимум 2 acceptance criteria
- Все тексты на РУССКОМ"""

        # Вызываем AI
        request_params = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": settings.API_TEMPERATURE,
            "timeout": 60.0
        }

        completion, provider = _make_request_with_fallback(
            request_params,
            providers=None,  # None означает использовать get_providers_for_task()
            is_enhancement=False,
            task_type="generation"
        )

        response_text = completion.choices[0].message.content

        # Парсим JSON
        parsed = self._parse_json_response(response_text)
        parsed["provider_used"] = provider

        # Кешируем результат
        if use_cache and self.redis_client:
            try:
                self.redis_client.setex(
                    cache_key,
                    86400,  # 24 часа
                    json.dumps(parsed)
                )
                logger.info("Agent result cached")
            except Exception as e:
                logger.warning(f"Redis cache write failed: {e}")

        return parsed

    def _structure_to_project(self, structure: Dict[str, Any]) -> Project:
        """
        Конвертирует структуру агента (dict) в модель Project для валидации
        
        Args:
            structure: Сгенерированная структура карты
            
        Returns:
            Project: Временный объект проекта для валидации
        """
        # Создаем временный проект
        project = Project(
            id=0,  # Временный ID
            user_id=0,
            name=structure.get("productName", "Temporary Project"),
            raw_requirements=""
        )
        
        # Создаем стандартные релизы
        mvp_release = Release(id=1, project_id=0, title="MVP", position=0)
        release1 = Release(id=2, project_id=0, title="Release 1", position=1)
        later_release = Release(id=3, project_id=0, title="Later", position=2)
        project.releases = [mvp_release, release1, later_release]
        
        # Конвертируем Activities
        activities = []
        for act_idx, activity_data in enumerate(structure.get("map", [])):
            if not isinstance(activity_data, dict):
                continue
                
            activity = Activity(
                id=act_idx + 1,
                project_id=0,
                title=activity_data.get("activity", f"Activity {act_idx + 1}"),
                position=act_idx
            )
            
            # Конвертируем Tasks
            tasks = []
            for task_idx, task_data in enumerate(activity_data.get("tasks", [])):
                if not isinstance(task_data, dict):
                    continue
                    
                task = UserTask(
                    id=(act_idx + 1) * 100 + task_idx + 1,
                    activity_id=act_idx + 1,
                    title=task_data.get("taskTitle", f"Task {task_idx + 1}"),
                    position=task_idx
                )
                
                # Конвертируем Stories
                stories = []
                for story_idx, story_data in enumerate(task_data.get("stories", [])):
                    if not isinstance(story_data, dict):
                        continue
                    
                    # Определяем релиз по приоритету
                    priority = story_data.get("priority", "Later").upper()
                    if "MVP" in priority:
                        target_release = mvp_release
                    elif "RELEASE" in priority or "1" in priority:
                        target_release = release1
                    else:
                        target_release = later_release
                    
                    story = UserStory(
                        id=(act_idx + 1) * 10000 + (task_idx + 1) * 100 + story_idx + 1,
                        task_id=(act_idx + 1) * 100 + task_idx + 1,
                        release_id=target_release.id,
                        title=story_data.get("title", f"Story {story_idx + 1}"),
                        description=story_data.get("description", ""),
                        priority=story_data.get("priority", "Later"),
                        acceptance_criteria=story_data.get("acceptanceCriteria", []),
                        position=story_idx
                    )
                    stories.append(story)
                
                task.stories = stories
                tasks.append(task)
            
            activity.tasks = tasks
            activities.append(activity)
        
        project.activities = activities
        return project

    def _validate(self, structure: Dict[str, Any]) -> Dict[str, Any]:
        """
        Step 2: Валидирует структуру карты
        
        ФАЗА 1: Интегрировано с validation_service и similarity_service
        
        Args:
            structure: Сгенерированная структура

        Returns:
            dict: {
                "is_valid": bool,
                "issues": List[ValidationIssue],
                "score": float,  # 0.0-1.0 (нормализованный из validation_service)
                "score_raw": int,  # 0-100 (оригинальный из validation_service)
                "similarity": Optional[Dict],  # SimilarityResult как dict
                "recommendations": List[str],
                "stats": Dict  # Статистика из validation_service
            }
        """
        # Быстрая проверка обязательных полей
        if not structure.get("map"):
            # Добавляем критическую проблему в issues для логической консистентности
            # Если is_valid=False, должен быть хотя бы один issue
            from schemas.analysis import ValidationIssue, IssueType, IssueSeverity
            return {
                "is_valid": False,
                "issues": [
                    ValidationIssue(
                        type=IssueType.EMPTY_ACTIVITY,  # Используем подходящий тип
                        severity=IssueSeverity.ERROR,
                        message="Отсутствует структура карты (map). Карта не может быть сгенерирована без структуры.",
                        location={"structure": "map"}
                    )
                ],
                "score": 0.0,  # float 0.0-1.0 для консистентности
                "score_raw": 0,  # int 0-100 для консистентности
                "similarity": None,
                "recommendations": ["Отсутствует структура карты (map)"],
                "stats": {}  # Пустой stats для консистентности
            }
        
        try:
            # Конвертируем структуру в модель Project
            temp_project = self._structure_to_project(structure)
            
            # Используем validation_service
            validation_result: ValidationResult = validate_project_map(temp_project, db=None)
            
            # Используем similarity_service для поиска дубликатов
            similarity_result = None
            try:
                # similarity_service требует минимум 2 истории
                total_stories = sum(
                    len(task.stories)
                    for activity in temp_project.activities
                    for task in activity.tasks
                )
                
                if total_stories >= 2:
                    similarity_result = analyze_similarity(
                        temp_project,
                        similarity_threshold=0.7,
                        duplicate_threshold=0.9
                    )
            except Exception as e:
                logger.warning(f"Similarity analysis failed: {e}")
                similarity_result = None
            
            # Конвертируем ValidationResult в dict для совместимости
            return {
                "is_valid": validation_result.is_valid,
                "issues": validation_result.issues,  # List[ValidationIssue]
                "score": validation_result.score / 100.0,  # Конвертируем 0-100 в 0.0-1.0
                "score_raw": validation_result.score,  # Оригинальный score 0-100
                "similarity": similarity_result.dict() if similarity_result else None,
                "recommendations": validation_result.recommendations,
                "stats": validation_result.stats
            }
            
        except Exception as e:
            logger.error(f"Validation failed: {e}", exc_info=True)
            # Fallback на простую валидацию если что-то пошло не так
            return {
                "is_valid": False,
                "issues": [{
                    "type": "validation_error",
                    "severity": "error",
                    "message": f"Ошибка валидации: {str(e)}"
                }],
                "score": 0.0,  # float 0.0-1.0 для консистентности
                "score_raw": 0,  # int 0-100 для консистентности
                "similarity": None,
                "recommendations": ["Ошибка при валидации структуры"],
                "stats": {}  # Пустой stats для консистентности
            }

    def _fix(
        self,
        structure: Dict[str, Any],
        issues: List,
        similarity_info: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Step 3: Исправляет критические ошибки
        
        ФАЗА 1: Работает с ValidationIssue объектами из validation_service
        и учитывает similarity issues

        Args:
            structure: Текущая структура
            issues: Список проблем (ValidationIssue объекты или dict)
            similarity_info: Результат similarity анализа (опционально)

        Returns:
            dict: Исправленная структура
        """
        logger.info(f"Attempting to fix {len(issues)} issues")

        # Конвертируем ValidationIssue в строки для промпта
        issues_messages = []
        for issue in issues:
            if hasattr(issue, 'message'):
                # ValidationIssue объект
                issues_messages.append(f"- {issue.message}")
            elif isinstance(issue, dict):
                # Старый формат dict
                issues_messages.append(f"- {issue.get('message', 'Неизвестная ошибка')}")
            else:
                issues_messages.append(f"- Неизвестная ошибка")

        # Добавляем информацию о дубликатах если есть
        similarity_warnings = []
        if similarity_info:
            similar_groups = similarity_info.get("similar_groups", [])
            duplicates = [g for g in similar_groups if g.get("group_type") == "duplicate"]
            if duplicates:
                similarity_warnings.append("\n⚠️ Найдены дубликаты историй:")
                for dup_group in duplicates:
                    stories_titles = [s.get("title", "Без названия") for s in dup_group.get("stories", [])]
                    similarity_warnings.append(f"  - Дубликаты: {', '.join(stories_titles[:3])}")
                    if len(stories_titles) > 3:
                        similarity_warnings.append(f"    ... и еще {len(stories_titles) - 3}")

        # Формируем промпт для исправления
        system_prompt = """Ты — эксперт по User Story Mapping.
Твоя задача — исправить ошибки в существующей User Story Map.

ВАЖНО:
1. Сохрани все существующие хорошие данные
2. Исправь только указанные проблемы
3. Не удаляй информацию, а дополняй/исправляй
4. Если есть дубликаты - объедини их или уточни различия
5. Все тексты на РУССКОМ языке
6. Возвращай ТОЛЬКО валидный JSON"""

        issues_description = "\n".join(issues_messages)
        if similarity_warnings:
            issues_description += "\n" + "\n".join(similarity_warnings)

        user_prompt = f"""Исходная User Story Map:
```json
{json.dumps(structure, ensure_ascii=False, indent=2)}
```

Найденные проблемы:
{issues_description}

Исправь эти проблемы и верни исправленную карту в том же JSON формате.

Требования:
- Минимум 3 Activities
- 2-3 Tasks на Activity
- 2-4 Stories на Task
- 2-4 acceptance criteria на Story
- Все на РУССКОМ языке

Верни ТОЛЬКО исправленный JSON, без дополнительного текста."""

        # Вызываем AI для исправления
        request_params = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.3,  # Меньше креативности при исправлении
            "timeout": 45.0
        }

        try:
                completion, provider = _make_request_with_fallback(
                    request_params,
                    providers=None,  # None означает использовать get_providers_for_task()
                    is_enhancement=False,
                    task_type="generation"
                )

            response_text = completion.choices[0].message.content
            fixed = self._parse_json_response(response_text)
            fixed["provider_used"] = provider

            logger.info(f"✅ Successfully fixed structure using {provider}")
            return fixed

        except Exception as e:
            logger.error(f"Failed to fix structure: {e}")
            # Возвращаем оригинал если исправление не удалось
            return structure

    def _parse_json_response(self, response_text: str) -> Dict:
        """
        Парсит JSON из ответа AI (убирает markdown если есть)

        Args:
            response_text: Текст ответа от AI

        Returns:
            dict: Распарсенный JSON

        Raises:
            json.JSONDecodeError: Если не удалось распарсить
        """
        # Убираем markdown форматирование
        text = response_text.strip()

        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]

        if text.endswith("```"):
            text = text[:-3]

        text = text.strip()

        # Парсим JSON
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON: {e}")
            logger.error(f"Response preview: {text[:500]}")
            raise


def generate_map_with_agent(
    requirements: str,
    redis_client=None,
    use_cache: bool = True,
    enable_validation: bool = True,
    enable_fix: bool = True
) -> Dict[str, Any]:
    """
    Удобная функция для генерации карты через агента

    Args:
        requirements: Текст требований
        redis_client: Redis клиент для кеширования
        use_cache: Использовать кеш
        enable_validation: Включить валидацию
        enable_fix: Включить исправление ошибок

    Returns:
        dict: Сгенерированная карта с метаданными
    """
    agent = SimpleAgent(
        redis_client=redis_client,
        enable_validation=enable_validation,
        enable_fix=enable_fix
    )

    return agent.generate_map(requirements, use_cache=use_cache)

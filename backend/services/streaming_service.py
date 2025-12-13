"""
Streaming Service для SSE (Server-Sent Events) генерации User Story Map.

Координирует:
1. Enhancement (опционально)
2. AI генерация карты
3. Валидация и анализ дубликатов
4. Сохранение в БД

Отправляет SSE события клиенту в реальном времени.
"""

import json
import logging
import asyncio
from typing import AsyncGenerator, Optional, Dict, Any
from sqlalchemy.orm import Session

from services.ai_service import enhance_requirements, generate_ai_map, generate_map_with_agent
from services.validation_service import validate_project_map
from services.similarity_service import analyze_similarity
from models import Project, Release, Activity, Task, Story
from config import get_redis_client

logger = logging.getLogger(__name__)


def sse_event(event_type: str, data: Dict[str, Any]) -> str:
    """
    Форматирует SSE event.

    Args:
        event_type: Тип события (enhancing, generating, analysis, etc.)
        data: Данные события

    Returns:
        Строка в формате SSE: "data: {...}\n\n"
    """
    payload = {"type": event_type, **data}
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


async def generate_map_streaming(
    requirements_text: str,
    use_enhancement: bool,
    use_agent: bool,
    user_id: int,
    db: Session
) -> AsyncGenerator[str, None]:
    """
    Async генератор для SSE streaming генерации карты.

    Args:
        requirements_text: Исходные требования
        use_enhancement: Использовать ли enhancement stage
        use_agent: Использовать ли AI Agent вместо простой генерации
        user_id: ID пользователя
        db: Database session

    Yields:
        SSE события в формате "data: {...}\n\n"

    Events:
        - {type: "enhancing", progress: 0-20}
        - {type: "enhanced", text: str, confidence: float}
        - {type: "generating", progress: 20-70}
        - {type: "validating", progress: 70-85}
        - {type: "analysis", duplicates: int, score: int, issues: list}
        - {type: "saving", progress: 85-95}
        - {type: "complete", project_id: int, project_name: str}
        - {type: "error", message: str}
    """

    redis_client = get_redis_client()
    generation_text = requirements_text
    enhancement_data = None

    try:
        # ============= STAGE 1: ENHANCEMENT =============
        if use_enhancement:
            logger.info(f"[SSE] Stage 1: Enhancing requirements for user {user_id}")
            yield sse_event("enhancing", {"progress": 10, "stage": "enhancement"})

            # Запускаем в executor т.к. enhance_requirements синхронная
            loop = asyncio.get_event_loop()
            enhancement_data = await loop.run_in_executor(
                None,
                lambda: enhance_requirements(requirements_text, redis_client=redis_client)
            )

            # Используем улучшенный текст если confidence достаточно высокий
            if (enhancement_data.get("confidence", 0) >= 0.7 and
                not enhancement_data.get("fallback", False)):
                generation_text = enhancement_data.get("enhanced_text", requirements_text)
                logger.info(f"[SSE] Using enhanced text. Confidence: {enhancement_data.get('confidence')}")
            else:
                generation_text = requirements_text
                logger.info(f"[SSE] Using original text. Low confidence: {enhancement_data.get('confidence', 0)}")

            yield sse_event("enhanced", {
                "text": generation_text,
                "confidence": enhancement_data.get("confidence", 0),
                "used_enhancement": generation_text != requirements_text,
                "progress": 20
            })

            # Небольшая задержка для UX (чтобы пользователь видел переход)
            await asyncio.sleep(0.5)
        else:
            logger.info(f"[SSE] Stage 1 skipped (use_enhancement=False)")
            yield sse_event("generating", {"progress": 20, "stage": "generation"})

        # ============= STAGE 2: AI GENERATION =============
        logger.info(f"[SSE] Stage 2: Generating map for user {user_id}")
        yield sse_event("generating", {"progress": 30, "stage": "generation"})

        # Запускаем генерацию в executor
        loop = asyncio.get_event_loop()

        if use_agent:
            logger.info("[SSE] Using AI Agent for generation")
            ai_result = await loop.run_in_executor(
                None,
                lambda: generate_map_with_agent(generation_text, redis_client=redis_client)
            )
        else:
            logger.info("[SSE] Using standard generation")
            ai_result = await loop.run_in_executor(
                None,
                lambda: generate_ai_map(generation_text, redis_client=redis_client)
            )

        yield sse_event("generating", {"progress": 60, "stage": "generation"})

        # Парсим результат
        product_name = ai_result.get("productName", "Untitled Project")
        map_data = ai_result.get("map", {})

        activities_count = len(map_data.get("activities", []))
        tasks_count = sum(len(act.get("tasks", [])) for act in map_data.get("activities", []))
        stories_count = sum(
            len(task.get("stories", []))
            for act in map_data.get("activities", [])
            for task in act.get("tasks", [])
        )

        logger.info(f"[SSE] Generated: {activities_count} activities, {tasks_count} tasks, {stories_count} stories")
        yield sse_event("generating", {
            "progress": 70,
            "activities": activities_count,
            "tasks": tasks_count,
            "stories": stories_count
        })

        await asyncio.sleep(0.3)

        # ============= STAGE 3: VALIDATION & ANALYSIS =============
        logger.info(f"[SSE] Stage 3: Validating and analyzing")
        yield sse_event("validating", {"progress": 75, "stage": "validation"})

        # Валидация (синхронная, запускаем в executor)
        validation_result = await loop.run_in_executor(
            None,
            lambda: validate_project_map(map_data)
        )

        yield sse_event("validating", {"progress": 80})

        # Анализ дубликатов (синхронная, запускаем в executor)
        similarity_result = await loop.run_in_executor(
            None,
            lambda: analyze_similarity(map_data)
        )

        duplicates_count = len(similarity_result.get("duplicate_groups", []))
        similar_count = len(similarity_result.get("similar_groups", []))
        overall_score = validation_result.get("overall_score", 0)
        issues = validation_result.get("issues", [])

        logger.info(f"[SSE] Analysis: score={overall_score}, duplicates={duplicates_count}, similar={similar_count}")

        # Отправляем результаты анализа (это триггерит auto-show на фронте!)
        yield sse_event("analysis", {
            "progress": 85,
            "duplicates": duplicates_count,
            "similar": similar_count,
            "score": overall_score,
            "issues": issues[:5],  # Первые 5 проблем
            "total_issues": len(issues)
        })

        await asyncio.sleep(0.5)

        # ============= STAGE 4: SAVE TO DATABASE =============
        logger.info(f"[SSE] Stage 4: Saving to database")
        yield sse_event("saving", {"progress": 90, "stage": "saving"})

        # Сохраняем в БД (синхронная операция)
        project_id = await loop.run_in_executor(
            None,
            lambda: _save_project_to_db(
                product_name=product_name,
                raw_requirements=requirements_text,
                map_data=map_data,
                user_id=user_id,
                enhancement_data=enhancement_data,
                db=db
            )
        )

        logger.info(f"[SSE] Project saved with ID: {project_id}")
        yield sse_event("saving", {"progress": 95})

        await asyncio.sleep(0.3)

        # ============= STAGE 5: COMPLETE =============
        logger.info(f"[SSE] Generation complete. Project ID: {project_id}")
        yield sse_event("complete", {
            "progress": 100,
            "project_id": project_id,
            "project_name": product_name,
            "stats": {
                "activities": activities_count,
                "tasks": tasks_count,
                "stories": stories_count,
                "score": overall_score,
                "duplicates": duplicates_count
            }
        })

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[SSE] Error during streaming generation: {error_msg}", exc_info=True)
        yield sse_event("error", {
            "message": error_msg,
            "stage": "unknown"
        })


def _save_project_to_db(
    product_name: str,
    raw_requirements: str,
    map_data: dict,
    user_id: int,
    enhancement_data: Optional[dict],
    db: Session
) -> int:
    """
    Сохраняет проект в базу данных.

    Args:
        product_name: Название продукта
        raw_requirements: Исходные требования
        map_data: Данные карты от AI
        user_id: ID пользователя
        enhancement_data: Данные улучшения (опционально)
        db: Database session

    Returns:
        ID созданного проекта
    """

    # Создаем проект
    new_project = Project(
        name=product_name,
        raw_requirements=raw_requirements,
        user_id=user_id
    )

    # Если было улучшение - сохраняем метаданные
    if enhancement_data:
        new_project.enhanced_requirements = enhancement_data.get("enhanced_text")
        new_project.enhancement_confidence = enhancement_data.get("confidence", 0)

    db.add(new_project)
    db.flush()  # Получаем project.id

    # Создаем дефолтные релизы
    default_releases = [
        Release(project_id=new_project.id, title="MVP", position=0),
        Release(project_id=new_project.id, title="Release 1", position=1),
        Release(project_id=new_project.id, title="Later", position=2)
    ]
    db.add_all(default_releases)
    db.flush()

    # Маппинг позиций релизов на ID
    release_map = {r.position: r.id for r in default_releases}

    # Создаем Activities → Tasks → Stories
    activities_data = map_data.get("activities", [])

    for act_idx, act_data in enumerate(activities_data):
        activity = Activity(
            project_id=new_project.id,
            title=act_data.get("title", f"Activity {act_idx + 1}"),
            position=act_idx
        )
        db.add(activity)
        db.flush()

        for task_idx, task_data in enumerate(act_data.get("tasks", [])):
            task = Task(
                activity_id=activity.id,
                title=task_data.get("title", f"Task {task_idx + 1}"),
                position=task_idx
            )
            db.add(task)
            db.flush()

            for story_idx, story_data in enumerate(task_data.get("stories", [])):
                # Определяем release_id по priority
                priority = story_data.get("priority", "MVP")
                if priority == "MVP":
                    release_id = release_map[0]
                elif priority == "Release 1":
                    release_id = release_map[1]
                else:
                    release_id = release_map[2]

                story = Story(
                    task_id=task.id,
                    title=story_data.get("title", f"Story {story_idx + 1}"),
                    description=story_data.get("description", ""),
                    acceptance_criteria=story_data.get("acceptanceCriteria", []),
                    priority=priority,
                    release_id=release_id,
                    position=story_idx,
                    status="todo"
                )
                db.add(story)

    db.commit()

    logger.info(f"Project {new_project.id} saved to database")
    return new_project.id

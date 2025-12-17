"""
Сервис применения actionable рекомендаций
"""
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from models import UserStory, Project
from schemas.analysis import (
    ActionType,
    ActionableRecommendation,
    ApplyRecommendationResponse
)
from services.ai_service import ai_improve_story_content

logger = logging.getLogger(__name__)


async def apply_recommendation(
    recommendation: ActionableRecommendation,
    project: Project,
    db: Session
) -> ApplyRecommendationResponse:
    """
    Применяет рекомендацию к проекту

    Args:
        recommendation: Рекомендация для применения
        project: Проект
        db: Сессия БД

    Returns:
        ApplyRecommendationResponse: Результат применения
    """
    logger.info(
        f"Applying recommendation {recommendation.id} "
        f"(type: {recommendation.action_type}) to project {project.id}"
    )

    try:
        if recommendation.action_type == ActionType.ADD_DESCRIPTION:
            return await apply_add_description(recommendation, project, db)

        elif recommendation.action_type == ActionType.ADD_CRITERIA:
            return await apply_add_criteria(recommendation, project, db)

        elif recommendation.action_type == ActionType.MERGE_STORIES:
            return await apply_merge_stories(recommendation, project, db)

        elif recommendation.action_type == ActionType.IMPROVE_STORY:
            return await apply_improve_stories(recommendation, project, db)

        elif recommendation.action_type == ActionType.MOVE_STORY:
            return apply_move_stories(recommendation, project, db)

        else:
            return ApplyRecommendationResponse(
                success=False,
                message=f"Тип действия {recommendation.action_type} пока не поддерживается",
                affected_story_ids=[],
                new_story_ids=[],
                deleted_story_ids=[]
            )

    except Exception as e:
        logger.error(f"Error applying recommendation: {e}", exc_info=True)
        return ApplyRecommendationResponse(
            success=False,
            message=f"Ошибка при применении: {str(e)}",
            affected_story_ids=[],
            new_story_ids=[],
            deleted_story_ids=[]
        )


async def apply_add_description(
    recommendation: ActionableRecommendation,
    project: Project,
    db: Session
) -> ApplyRecommendationResponse:
    """Добавляет описания к историям через AI"""

    story_ids = recommendation.story_ids
    if not story_ids:
        return ApplyRecommendationResponse(
            success=False,
            message="Не указаны ID историй",
            affected_story_ids=[],
            new_story_ids=[],
            deleted_story_ids=[]
        )

    # Получаем истории
    stories = db.query(UserStory).filter(
        UserStory.id.in_(story_ids),
        UserStory.task_id.in_(
            [task.id for activity in project.activities for task in activity.tasks]
        )
    ).all()

    if not stories:
        return ApplyRecommendationResponse(
            success=False,
            message="Истории не найдены",
            affected_story_ids=[],
            new_story_ids=[],
            deleted_story_ids=[]
        )

    affected_ids = []

    # Для каждой истории генерируем описание через AI
    for story in stories:
        if story.description and len(story.description.strip()) > 10:
            # Уже есть описание, пропускаем
            continue

        try:
            # Используем AI для генерации описания
            prompt = f"Добавь детальное описание для истории на основе названия. Используй формат User Story."

            result = await ai_improve_story_content(
                story_id=story.id,
                story_title=story.title,
                story_description=story.description or "",
                story_criteria=story.acceptance_criteria or [],
                prompt=prompt,
                action="details"
            )

            if result.get("success") and result.get("improved_story"):
                improved = result["improved_story"]
                story.description = improved.get("description", story.description)
                affected_ids.append(story.id)
                logger.info(f"Added description to story {story.id}")

        except Exception as e:
            logger.warning(f"Failed to add description to story {story.id}: {e}")
            continue

    db.commit()

    return ApplyRecommendationResponse(
        success=True,
        message=f"Добавлено описание к {len(affected_ids)} историям",
        affected_story_ids=affected_ids,
        new_story_ids=[],
        deleted_story_ids=[]
    )


async def apply_add_criteria(
    recommendation: ActionableRecommendation,
    project: Project,
    db: Session
) -> ApplyRecommendationResponse:
    """Добавляет acceptance criteria к историям через AI"""

    story_ids = recommendation.story_ids
    if not story_ids:
        return ApplyRecommendationResponse(
            success=False,
            message="Не указаны ID историй",
            affected_story_ids=[],
            new_story_ids=[],
            deleted_story_ids=[]
        )

    # Получаем истории
    stories = db.query(UserStory).filter(
        UserStory.id.in_(story_ids),
        UserStory.task_id.in_(
            [task.id for activity in project.activities for task in activity.tasks]
        )
    ).all()

    if not stories:
        return ApplyRecommendationResponse(
            success=False,
            message="Истории не найдены",
            affected_story_ids=[],
            new_story_ids=[],
            deleted_story_ids=[]
        )

    affected_ids = []

    # Для каждой истории генерируем AC через AI
    for story in stories:
        if story.acceptance_criteria and len(story.acceptance_criteria) > 0:
            # Уже есть AC, пропускаем
            continue

        try:
            # Используем AI для генерации AC
            prompt = f"Добавь детальные acceptance criteria для истории. Сделай их конкретными и измеримыми."

            result = await ai_improve_story_content(
                story_id=story.id,
                story_title=story.title,
                story_description=story.description or "",
                story_criteria=story.acceptance_criteria or [],
                prompt=prompt,
                action="criteria"
            )

            if result.get("success") and result.get("improved_story"):
                improved = result["improved_story"]
                story.acceptance_criteria = improved.get("acceptance_criteria", story.acceptance_criteria)
                affected_ids.append(story.id)
                logger.info(f"Added AC to story {story.id}")

        except Exception as e:
            logger.warning(f"Failed to add AC to story {story.id}: {e}")
            continue

    db.commit()

    return ApplyRecommendationResponse(
        success=True,
        message=f"Добавлены acceptance criteria к {len(affected_ids)} историям",
        affected_story_ids=affected_ids,
        new_story_ids=[],
        deleted_story_ids=[]
    )


async def apply_merge_stories(
    recommendation: ActionableRecommendation,
    project: Project,
    db: Session
) -> ApplyRecommendationResponse:
    """Объединяет дублирующиеся истории"""

    params = recommendation.action_params
    primary_story_id = params.get("primary_story_id")
    merge_story_ids = params.get("merge_story_ids", [])

    if not primary_story_id or not merge_story_ids:
        return ApplyRecommendationResponse(
            success=False,
            message="Не указаны ID историй для объединения",
            affected_story_ids=[],
            new_story_ids=[],
            deleted_story_ids=[]
        )

    # Получаем основную историю
    primary_story = db.query(UserStory).filter(UserStory.id == primary_story_id).first()
    if not primary_story:
        return ApplyRecommendationResponse(
            success=False,
            message="Основная история не найдена",
            affected_story_ids=[],
            new_story_ids=[],
            deleted_story_ids=[]
        )

    # Получаем истории для объединения
    stories_to_merge = db.query(UserStory).filter(
        UserStory.id.in_(merge_story_ids)
    ).all()

    if not stories_to_merge:
        return ApplyRecommendationResponse(
            success=False,
            message="Истории для объединения не найдены",
            affected_story_ids=[],
            new_story_ids=[],
            deleted_story_ids=[]
        )

    # Объединяем контент
    merged_descriptions = [primary_story.description or ""]
    merged_criteria = list(primary_story.acceptance_criteria or [])

    for story in stories_to_merge:
        if story.description and story.description not in merged_descriptions:
            merged_descriptions.append(story.description)

        if story.acceptance_criteria:
            for criterion in story.acceptance_criteria:
                if criterion not in merged_criteria:
                    merged_criteria.append(criterion)

    # Обновляем основную историю
    primary_story.description = "\n\n".join(filter(None, merged_descriptions))
    primary_story.acceptance_criteria = merged_criteria

    # Удаляем дубликаты
    deleted_ids = []
    for story in stories_to_merge:
        deleted_ids.append(story.id)
        db.delete(story)

    db.commit()

    return ApplyRecommendationResponse(
        success=True,
        message=f"Объединено {len(deleted_ids)} историй в '{primary_story.title}'",
        affected_story_ids=[primary_story_id],
        new_story_ids=[],
        deleted_story_ids=deleted_ids
    )


async def apply_improve_stories(
    recommendation: ActionableRecommendation,
    project: Project,
    db: Session
) -> ApplyRecommendationResponse:
    """Улучшает истории через AI"""

    params = recommendation.action_params
    improve_all = params.get("improve_all", False)

    if improve_all:
        # Улучшаем все истории проекта
        all_stories = []
        for activity in project.activities:
            for task in activity.tasks:
                all_stories.extend(task.stories)

        story_ids = [s.id for s in all_stories[:10]]  # Лимит 10 за раз
    else:
        story_ids = recommendation.story_ids

    if not story_ids:
        return ApplyRecommendationResponse(
            success=False,
            message="Нет историй для улучшения",
            affected_story_ids=[],
            new_story_ids=[],
            deleted_story_ids=[]
        )

    # Получаем истории
    stories = db.query(UserStory).filter(UserStory.id.in_(story_ids)).all()

    affected_ids = []

    for story in stories:
        try:
            # Улучшаем через AI
            result = await ai_improve_story_content(
                story_id=story.id,
                story_title=story.title,
                story_description=story.description or "",
                story_criteria=story.acceptance_criteria or [],
                prompt="Улучши описание и acceptance criteria по best практикам User Story",
                action="details"
            )

            if result.get("success") and result.get("improved_story"):
                improved = result["improved_story"]
                story.description = improved.get("description", story.description)
                story.acceptance_criteria = improved.get("acceptance_criteria", story.acceptance_criteria)
                affected_ids.append(story.id)

        except Exception as e:
            logger.warning(f"Failed to improve story {story.id}: {e}")
            continue

    db.commit()

    return ApplyRecommendationResponse(
        success=True,
        message=f"Улучшено {len(affected_ids)} историй",
        affected_story_ids=affected_ids,
        new_story_ids=[],
        deleted_story_ids=[]
    )


def apply_move_stories(
    recommendation: ActionableRecommendation,
    project: Project,
    db: Session
) -> ApplyRecommendationResponse:
    """Перемещает истории между релизами"""

    params = recommendation.action_params
    from_release_name = params.get("from_release")
    to_release_name = params.get("to_release")
    suggested_count = params.get("suggested_count", 0)

    if not from_release_name or not to_release_name:
        return ApplyRecommendationResponse(
            success=False,
            message="Не указаны релизы",
            affected_story_ids=[],
            new_story_ids=[],
            deleted_story_ids=[]
        )

    # Находим релизы
    from_release = next((r for r in project.releases if r.title == from_release_name), None)
    to_release = next((r for r in project.releases if r.title == to_release_name), None)

    if not from_release or not to_release:
        return ApplyRecommendationResponse(
            success=False,
            message="Релизы не найдены",
            affected_story_ids=[],
            new_story_ids=[],
            deleted_story_ids=[]
        )

    # Получаем истории из from_release
    stories_to_move = db.query(UserStory).filter(
        UserStory.release_id == from_release.id
    ).order_by(UserStory.position.desc()).limit(suggested_count).all()

    if not stories_to_move:
        return ApplyRecommendationResponse(
            success=False,
            message="Нет историй для перемещения",
            affected_story_ids=[],
            new_story_ids=[],
            deleted_story_ids=[]
        )

    # Перемещаем
    moved_ids = []
    for story in stories_to_move:
        story.release_id = to_release.id
        moved_ids.append(story.id)

    db.commit()

    return ApplyRecommendationResponse(
        success=True,
        message=f"Перемещено {len(moved_ids)} историй из {from_release_name} в {to_release_name}",
        affected_story_ids=moved_ids,
        new_story_ids=[],
        deleted_story_ids=[]
    )

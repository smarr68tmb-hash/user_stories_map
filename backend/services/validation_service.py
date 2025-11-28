"""
Сервис валидации структуры User Story Map
"""
import logging
from typing import List, Dict, Any
from sqlalchemy.orm import Session

from models import Project, Activity, UserTask, UserStory, Release
from schemas.analysis import (
    ValidationResult,
    ValidationIssue,
    IssueSeverity,
    IssueType
)

logger = logging.getLogger(__name__)


def validate_project_map(project: Project, db: Session) -> ValidationResult:
    """
    Валидирует структуру User Story Map проекта
    
    Проверяет:
    1. Наличие обязательных элементов (Activities, Tasks, Stories)
    2. Пустые ячейки (Task + Release без Stories)
    3. Качество описаний историй
    4. Баланс между релизами
    5. Дублирующиеся названия
    
    Args:
        project: Объект проекта с загруженными связями
        db: Сессия базы данных
    
    Returns:
        ValidationResult: Результат валидации
    """
    issues: List[ValidationIssue] = []
    recommendations: List[str] = []
    
    # Собираем статистику
    stats = {
        "total_activities": 0,
        "total_tasks": 0,
        "total_stories": 0,
        "stories_with_description": 0,
        "stories_with_criteria": 0,
        "empty_cells": 0,
        "stories_per_release": {}
    }
    
    # Получаем все релизы
    releases = project.releases
    release_ids = [r.id for r in releases]
    release_titles = {r.id: r.title for r in releases}
    
    # Инициализируем счетчики по релизам
    for release in releases:
        stats["stories_per_release"][release.title] = 0
    
    # Собираем все названия историй для проверки дубликатов
    all_story_titles: Dict[str, List[int]] = {}
    
    # === Проверка Activities ===
    if not project.activities:
        issues.append(ValidationIssue(
            type=IssueType.EMPTY_ACTIVITY,
            severity=IssueSeverity.ERROR,
            message="Проект не содержит ни одной Activity",
            location={"project_id": project.id}
        ))
    
    stats["total_activities"] = len(project.activities)
    
    for activity in project.activities:
        # Проверка пустых Activity
        if not activity.tasks:
            issues.append(ValidationIssue(
                type=IssueType.EMPTY_ACTIVITY,
                severity=IssueSeverity.WARNING,
                message=f"Activity '{activity.title}' не содержит задач (Tasks)",
                location={"activity_id": activity.id, "activity_title": activity.title}
            ))
            continue
        
        stats["total_tasks"] += len(activity.tasks)
        
        for task in activity.tasks:
            # Проверка пустых Task
            if not task.stories:
                issues.append(ValidationIssue(
                    type=IssueType.EMPTY_TASK,
                    severity=IssueSeverity.WARNING,
                    message=f"Task '{task.title}' в Activity '{activity.title}' не содержит историй",
                    location={
                        "task_id": task.id,
                        "task_title": task.title,
                        "activity_id": activity.id,
                        "activity_title": activity.title
                    }
                ))
                continue
            
            # Проверяем покрытие релизов для этого Task
            stories_by_release = {rid: [] for rid in release_ids}
            
            for story in task.stories:
                stats["total_stories"] += 1
                
                # Считаем по релизам
                if story.release_id:
                    stories_by_release[story.release_id].append(story)
                    release_title = release_titles.get(story.release_id, "Unknown")
                    if release_title in stats["stories_per_release"]:
                        stats["stories_per_release"][release_title] += 1
                
                # Проверка описания
                if story.description and len(story.description.strip()) > 10:
                    stats["stories_with_description"] += 1
                else:
                    issues.append(ValidationIssue(
                        type=IssueType.MISSING_DESCRIPTION,
                        severity=IssueSeverity.INFO,
                        message=f"История '{story.title}' не имеет описания",
                        location={
                            "story_id": story.id,
                            "story_title": story.title,
                            "task_title": task.title
                        }
                    ))
                
                # Проверка acceptance criteria
                if story.acceptance_criteria and len(story.acceptance_criteria) > 0:
                    stats["stories_with_criteria"] += 1
                else:
                    issues.append(ValidationIssue(
                        type=IssueType.MISSING_CRITERIA,
                        severity=IssueSeverity.WARNING,
                        message=f"История '{story.title}' не имеет acceptance criteria",
                        location={
                            "story_id": story.id,
                            "story_title": story.title,
                            "task_title": task.title
                        }
                    ))
                
                # Проверка длины названия
                if len(story.title.strip()) < 5:
                    issues.append(ValidationIssue(
                        type=IssueType.SHORT_TITLE,
                        severity=IssueSeverity.INFO,
                        message=f"Слишком короткое название истории: '{story.title}'",
                        location={"story_id": story.id}
                    ))
                
                # Собираем для проверки дубликатов
                title_lower = story.title.lower().strip()
                if title_lower not in all_story_titles:
                    all_story_titles[title_lower] = []
                all_story_titles[title_lower].append(story.id)
            
            # Проверяем пустые ячейки (Task + Release без Stories)
            for release_id, stories in stories_by_release.items():
                if not stories:
                    stats["empty_cells"] += 1
                    # Не добавляем как issue - пустые ячейки это нормально
    
    # === Проверка дубликатов названий ===
    for title, story_ids in all_story_titles.items():
        if len(story_ids) > 1:
            issues.append(ValidationIssue(
                type=IssueType.DUPLICATE_TITLE,
                severity=IssueSeverity.WARNING,
                message=f"Найдены истории с одинаковым названием: '{title}'",
                story_ids=story_ids
            ))
    
    # === Проверка баланса релизов ===
    if stats["total_stories"] > 0:
        release_counts = list(stats["stories_per_release"].values())
        if release_counts:
            max_count = max(release_counts)
            min_count = min(release_counts)
            
            # Если разница больше 3x - предупреждаем
            if max_count > 0 and min_count == 0:
                issues.append(ValidationIssue(
                    type=IssueType.UNBALANCED_RELEASES,
                    severity=IssueSeverity.INFO,
                    message="Некоторые релизы пустые. Проверьте распределение историй по релизам.",
                    location={"stats": stats["stories_per_release"]}
                ))
            elif max_count > min_count * 3 and min_count > 0:
                issues.append(ValidationIssue(
                    type=IssueType.UNBALANCED_RELEASES,
                    severity=IssueSeverity.INFO,
                    message="Истории неравномерно распределены по релизам",
                    location={"stats": stats["stories_per_release"]}
                ))
    
    # === Генерация рекомендаций ===
    if stats["total_stories"] == 0:
        recommendations.append("Добавьте пользовательские истории в карту")
    else:
        # Процент историй с описанием
        desc_percent = (stats["stories_with_description"] / stats["total_stories"]) * 100
        if desc_percent < 50:
            recommendations.append(
                f"Только {desc_percent:.0f}% историй имеют описание. "
                "Добавьте описания для лучшего понимания требований."
            )
        
        # Процент историй с AC
        criteria_percent = (stats["stories_with_criteria"] / stats["total_stories"]) * 100
        if criteria_percent < 70:
            recommendations.append(
                f"Только {criteria_percent:.0f}% историй имеют acceptance criteria. "
                "Добавьте критерии приемки для всех историй."
            )
    
    # Рекомендации по MVP
    mvp_count = stats["stories_per_release"].get("MVP", 0)
    if mvp_count == 0 and stats["total_stories"] > 0:
        recommendations.append("MVP релиз пуст. Определите минимальный набор функций для первого релиза.")
    elif mvp_count > 15:
        recommendations.append(
            f"В MVP слишком много историй ({mvp_count}). "
            "Рекомендуется сократить MVP до 10-15 историй."
        )
    
    # === Расчет оценки ===
    score = calculate_validation_score(issues, stats)
    
    # Определяем валидность (нет критических ошибок)
    has_errors = any(issue.severity == IssueSeverity.ERROR for issue in issues)
    
    logger.info(
        f"Validation completed for project {project.id}: "
        f"score={score}, issues={len(issues)}, valid={not has_errors}"
    )
    
    return ValidationResult(
        is_valid=not has_errors,
        score=score,
        issues=issues,
        recommendations=recommendations,
        stats=stats
    )


def calculate_validation_score(issues: List[ValidationIssue], stats: dict) -> int:
    """
    Рассчитывает оценку качества карты на основе найденных проблем
    
    Формула:
    - Базовый score: 100
    - ERROR: -20 баллов
    - WARNING: -5 баллов
    - INFO: -1 балл
    - Бонусы за полноту описаний
    """
    score = 100
    
    # Штрафы за проблемы
    for issue in issues:
        if issue.severity == IssueSeverity.ERROR:
            score -= 20
        elif issue.severity == IssueSeverity.WARNING:
            score -= 5
        elif issue.severity == IssueSeverity.INFO:
            score -= 1
    
    # Бонусы за полноту
    if stats.get("total_stories", 0) > 0:
        desc_ratio = stats.get("stories_with_description", 0) / stats["total_stories"]
        criteria_ratio = stats.get("stories_with_criteria", 0) / stats["total_stories"]
        
        # Добавляем до 10 бонусных баллов за полноту
        bonus = int((desc_ratio * 5) + (criteria_ratio * 5))
        score = min(100, score + bonus)
    
    # Минимальный score = 0
    return max(0, min(100, score))


def get_validation_summary(result: ValidationResult) -> str:
    """Генерирует текстовое резюме валидации"""
    
    if result.score >= 90:
        quality = "отличное"
    elif result.score >= 70:
        quality = "хорошее"
    elif result.score >= 50:
        quality = "удовлетворительное"
    else:
        quality = "требует улучшения"
    
    error_count = sum(1 for i in result.issues if i.severity == IssueSeverity.ERROR)
    warning_count = sum(1 for i in result.issues if i.severity == IssueSeverity.WARNING)
    
    summary = f"Качество карты: {quality} ({result.score}/100). "
    
    if error_count > 0:
        summary += f"Критических проблем: {error_count}. "
    if warning_count > 0:
        summary += f"Предупреждений: {warning_count}. "
    
    summary += f"Всего историй: {result.stats.get('total_stories', 0)}."
    
    return summary


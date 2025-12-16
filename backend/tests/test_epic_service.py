"""
Тесты для Epic Service - группировка историй в эпики

Покрытие:
1. ✅ AI группировка историй в эпики
2. ✅ Fallback группировка (по Activity или один эпик)
3. ✅ Валидация входных данных
4. ✅ Обработка ошибок AI
5. ✅ Создание эпиков в БД
6. ✅ Обработка дубликатов и пустых эпиков
"""
import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException

from models import UserStory, Project, Activity, UserTask, Release, Epic
from services.epic_service import (
    group_stories_into_epics,
    create_epics_from_grouping,
    _fallback_grouping,
    _prepare_stories_for_prompt
)


# ============================================================================
# Test _prepare_stories_for_prompt
# ============================================================================

class TestPrepareStoriesForPrompt:
    """Тесты для подготовки историй для промпта"""
    
    def test_prepare_stories_basic(self, db_session, test_project):
        """Проверка базовой подготовки историй"""
        # Получаем истории из проекта
        stories = db_session.query(UserStory).all()
        
        result = _prepare_stories_for_prompt(stories, "Test project")
        
        assert "Описание проекта: Test project" in result
        assert f"Всего историй для группировки: {len(stories)}" in result
        assert "Список историй:" in result
        assert stories[0].title in result if stories else True
    
    def test_prepare_stories_without_description(self, db_session, test_project):
        """Проверка подготовки без описания проекта"""
        stories = db_session.query(UserStory).all()
        
        result = _prepare_stories_for_prompt(stories, None)
        
        assert "Описание проекта" not in result
        assert f"Всего историй для группировки: {len(stories)}" in result


# ============================================================================
# Test _fallback_grouping
# ============================================================================

class TestFallbackGrouping:
    """Тесты для fallback группировки"""
    
    def test_fallback_empty_stories(self):
        """Проверка fallback для пустого списка"""
        result = _fallback_grouping([])
        # Fallback создает эпик "Все истории" даже для пустого списка
        assert len(result) == 1
        assert result[0]["title"] == "Все истории"
        assert len(result[0]["story_ids"]) == 0
    
    def test_fallback_group_by_activity(self, db_session, test_project):
        """Проверка группировки по Activity"""
        # Создаем еще одну Activity с историями
        activity2 = Activity(
            title="Activity 2",
            project_id=test_project.id,
            position=1
        )
        db_session.add(activity2)
        db_session.commit()
        
        task2 = UserTask(
            title="Task 2",
            activity_id=activity2.id,
            position=0
        )
        db_session.add(task2)
        db_session.commit()
        
        story2 = UserStory(
            title="Story 2",
            description="Story in activity 2",
            task_id=task2.id,
            position=0
        )
        db_session.add(story2)
        db_session.commit()
        
        # Получаем все истории
        stories = db_session.query(UserStory).all()
        
        result = _fallback_grouping(stories)
        
        assert len(result) >= 1
        assert all("story_ids" in epic for epic in result)
        assert all(epic["confidence"] == 0.6 for epic in result)  # Confidence для fallback
    
    def test_fallback_single_epic(self, db_session, test_project):
        """Проверка создания одного эпика если нет Activity"""
        stories = db_session.query(UserStory).all()
        
        # Удаляем связи с Activity для теста
        for story in stories:
            story.task = None
        
        result = _fallback_grouping(stories)
        
        assert len(result) == 1
        assert result[0]["title"] == "Все истории"
        assert len(result[0]["story_ids"]) == len(stories)
        assert result[0]["confidence"] == 0.5


# ============================================================================
# Test group_stories_into_epics
# ============================================================================

class TestGroupStoriesIntoEpics:
    """Тесты для AI группировки историй"""
    
    def test_empty_stories(self, test_project):
        """Проверка обработки пустого списка историй"""
        result = group_stories_into_epics([], test_project)
        assert result == []
    
    def test_too_few_stories(self, db_session, test_project):
        """Проверка обработки недостаточного количества историй"""
        stories = db_session.query(UserStory).limit(2).all()
        
        result = group_stories_into_epics(stories, test_project, min_epics=3)
        
        # Должен вернуть fallback группировку
        assert len(result) >= 1
    
    def test_invalid_min_max(self, db_session, test_project):
        """Проверка валидации min/max эпиков"""
        stories = db_session.query(UserStory).all()
        
        with pytest.raises(ValueError, match="min_epics must be <= max_epics"):
            group_stories_into_epics(stories, test_project, min_epics=5, max_epics=3)
    
    @patch('services.epic_service._make_request_with_fallback')
    def test_successful_grouping(self, mock_ai_request, db_session, test_project, mock_redis):
        """Проверка успешной группировки через AI"""
        # Создаем больше историй для группировки
        stories = []
        for i in range(10):
            activity = test_project.activities[0]
            task = activity.tasks[0]
            story = UserStory(
                title=f"Story {i}",
                description=f"Description {i}",
                task_id=task.id,
                position=i
            )
            db_session.add(story)
            stories.append(story)
        db_session.commit()
        
        # Mock AI ответ
        mock_response = {
            "epics": [
                {
                    "title": "Epic 1",
                    "description": "First epic",
                    "story_ids": [1, 2, 3],
                    "confidence": 0.9
                },
                {
                    "title": "Epic 2",
                    "description": "Second epic",
                    "story_ids": [4, 5, 6, 7],
                    "confidence": 0.85
                },
                {
                    "title": "Epic 3",
                    "description": "Third epic",
                    "story_ids": [8, 9, 10],
                    "confidence": 0.8
                }
            ]
        }
        
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message.content = json.dumps(mock_response)
        mock_ai_request.return_value = (mock_completion, "gemini")
        
        result = group_stories_into_epics(stories, test_project, redis_client=mock_redis)
        
        assert len(result) == 3
        assert all("title" in epic for epic in result)
        assert all("story_ids" in epic for epic in result)
        assert all("confidence" in epic for epic in result)
        mock_ai_request.assert_called_once()
    
    @patch('services.epic_service._make_request_with_fallback')
    def test_ai_json_error_fallback(self, mock_ai_request, db_session, test_project):
        """Проверка fallback при ошибке парсинга JSON"""
        stories = db_session.query(UserStory).all()
        
        # Mock невалидный JSON ответ
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message.content = "Invalid JSON {"
        mock_ai_request.return_value = (mock_completion, "gemini")
        
        result = group_stories_into_epics(stories, test_project)
        
        # Должен вернуть fallback группировку
        assert len(result) >= 1
    
    @patch('services.epic_service._make_request_with_fallback')
    def test_ungrouped_stories(self, mock_ai_request, db_session, test_project):
        """Проверка обработки нераспределенных историй"""
        stories = []
        for i in range(5):
            activity = test_project.activities[0]
            task = activity.tasks[0]
            story = UserStory(
                title=f"Story {i}",
                description=f"Description {i}",
                task_id=task.id,
                position=i
            )
            db_session.add(story)
            stories.append(story)
        db_session.commit()
        
        # Mock AI ответ, где не все истории распределены
        mock_response = {
            "epics": [
                {
                    "title": "Epic 1",
                    "description": "First epic",
                    "story_ids": [1, 2],  # Только 2 из 5
                    "confidence": 0.9
                }
            ]
        }
        
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message.content = json.dumps(mock_response)
        mock_ai_request.return_value = (mock_completion, "gemini")
        
        result = group_stories_into_epics(stories, test_project)
        
        # Должен быть эпик "Прочее" для нераспределенных историй
        assert len(result) >= 2
        other_epic = next((e for e in result if e["title"] == "Прочее"), None)
        assert other_epic is not None
        assert len(other_epic["story_ids"]) == 3  # Остальные 3 истории


# ============================================================================
# Test create_epics_from_grouping
# ============================================================================

class TestCreateEpicsFromGrouping:
    """Тесты для создания эпиков в БД"""
    
    def test_create_epics_basic(self, db_session, test_project):
        """Проверка базового создания эпиков"""
        # Получаем истории
        stories = db_session.query(UserStory).all()
        
        epics_data = [
            {
                "title": "Epic 1",
                "description": "First epic",
                "story_ids": [stories[0].id],
                "confidence": 0.9
            }
        ]
        
        created_epics = create_epics_from_grouping(
            db_session,
            test_project,
            epics_data
        )
        
        assert len(created_epics) == 1
        assert created_epics[0].title == "Epic 1"
        assert created_epics[0].project_id == test_project.id
        assert created_epics[0].confidence_score == 0.9
        
        # Проверяем, что история привязана к эпику
        db_session.refresh(stories[0])
        assert stories[0].epic_id == created_epics[0].id
    
    def test_create_epics_skip_empty(self, db_session, test_project):
        """Проверка пропуска пустых эпиков"""
        epics_data = [
            {
                "title": "Empty Epic",
                "description": "No stories",
                "story_ids": [],
                "confidence": 0.5
            },
            {
                "title": "Epic with Stories",
                "description": "Has stories",
                "story_ids": [db_session.query(UserStory).first().id],
                "confidence": 0.9
            }
        ]
        
        created_epics = create_epics_from_grouping(
            db_session,
            test_project,
            epics_data
        )
        
        # Пустой эпик должен быть пропущен
        assert len(created_epics) == 1
        assert created_epics[0].title == "Epic with Stories"
    
    def test_create_epics_duplicate_stories(self, db_session, test_project):
        """Проверка обработки дубликатов story_ids"""
        stories = db_session.query(UserStory).all()
        if len(stories) < 1:
            pytest.skip("Need at least 1 story")
        
        epics_data = [
            {
                "title": "Epic 1",
                "description": "Epic with duplicates",
                "story_ids": [stories[0].id, stories[0].id, stories[0].id],  # Дубликаты
                "confidence": 0.9
            }
        ]
        
        created_epics = create_epics_from_grouping(
            db_session,
            test_project,
            epics_data
        )
        
        assert len(created_epics) == 1
        # История должна быть привязана только один раз
        db_session.refresh(stories[0])
        assert stories[0].epic_id == created_epics[0].id
    
    def test_create_epics_rollback_on_error(self, db_session, test_project):
        """Проверка rollback при ошибке"""
        stories = db_session.query(UserStory).all()
        if len(stories) < 1:
            pytest.skip("Need at least 1 story")
        
        epics_data = [
            {
                "title": "Epic 1",
                "description": "Valid epic",
                "story_ids": [stories[0].id],
                "confidence": 0.9
            }
        ]
        
        # Симулируем ошибку при создании второго эпика
        with patch.object(db_session, 'flush', side_effect=Exception("DB Error")):
            with pytest.raises(Exception):
                create_epics_from_grouping(
                    db_session,
                    test_project,
                    epics_data
                )
        
        # Проверяем, что ничего не создано
        epics_count = db_session.query(Epic).filter(Epic.project_id == test_project.id).count()
        assert epics_count == 0


# ============================================================================
# Integration Tests
# ============================================================================

class TestEpicServiceIntegration:
    """Интеграционные тесты для epic service"""
    
    @patch('services.epic_service._make_request_with_fallback')
    def test_full_flow(self, mock_ai_request, db_session, test_project, mock_redis):
        """Проверка полного flow: группировка → создание в БД"""
        # Создаем больше историй
        stories = []
        for i in range(6):
            activity = test_project.activities[0]
            task = activity.tasks[0]
            story = UserStory(
                title=f"Story {i}",
                description=f"Description {i}",
                task_id=task.id,
                position=i
            )
            db_session.add(story)
            stories.append(story)
        db_session.commit()
        
        # Mock AI ответ
        mock_response = {
            "epics": [
                {
                    "title": "Epic 1",
                    "description": "First epic",
                    "story_ids": [1, 2, 3],
                    "confidence": 0.9
                },
                {
                    "title": "Epic 2",
                    "description": "Second epic",
                    "story_ids": [4, 5, 6],
                    "confidence": 0.85
                }
            ]
        }
        
        mock_completion = Mock()
        mock_completion.choices = [Mock()]
        mock_completion.choices[0].message.content = json.dumps(mock_response)
        mock_ai_request.return_value = (mock_completion, "gemini")
        
        # Группировка
        epics_data = group_stories_into_epics(stories, test_project, redis_client=mock_redis)
        
        # Создание в БД
        created_epics = create_epics_from_grouping(
            db_session,
            test_project,
            epics_data
        )
        
        assert len(created_epics) == 2
        
        # Проверяем, что истории привязаны
        for epic in created_epics:
            db_session.refresh(epic)
            assert len(epic.stories) > 0


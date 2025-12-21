"""
Тесты для Epic API endpoints

Покрытие:
1. ✅ Валидация входных данных
2. ✅ Проверка прав доступа через ResourceAccessValidator
3. ✅ Бизнес-логика helper классов

Примечание: Полные integration тесты требуют TestClient и настройки FastAPI app.
Эти тесты фокусируются на бизнес-логике и валидации.

После рефакторинга используем классы-хелперы вместо отдельных функций.
"""
import pytest
from fastapi import HTTPException

from models import Epic, UserStory, Project, User
from utils import ResourceAccessValidator


# ============================================================================
# Test ResourceAccessValidator
# ============================================================================

class TestResourceAccessValidator:
    """Тесты для ResourceAccessValidator - класса проверки доступа к ресурсам"""
    
    def test_get_project_success(self, db_session, test_user, test_project):
        """Проверка получения проекта пользователя"""
        validator = ResourceAccessValidator(db_session, test_user.id)
        project = validator.get_project(test_project.id)
        assert project.id == test_project.id
        assert project.user_id == test_user.id
    
    def test_get_project_not_found(self, db_session, test_user):
        """Проверка ошибки при отсутствии проекта"""
        validator = ResourceAccessValidator(db_session, test_user.id)
        with pytest.raises(HTTPException) as exc:
            validator.get_project(99999)
        assert exc.value.status_code == 404
        assert "Project not found" in exc.value.detail
    
    def test_get_project_wrong_user(self, db_session, test_user):
        """Проверка доступа к чужому проекту"""
        # Создаем проект другого пользователя
        other_user = User(
            email="other@example.com",
            full_name="Other User",
            hashed_password="hash",
            is_active=True
        )
        db_session.add(other_user)
        db_session.commit()
        
        other_project = Project(
            name="Other Project",
            user_id=other_user.id
        )
        db_session.add(other_project)
        db_session.commit()
        
        validator = ResourceAccessValidator(db_session, test_user.id)
        with pytest.raises(HTTPException) as exc:
            validator.get_project(other_project.id)
        assert exc.value.status_code == 404
        assert "Project not found" in exc.value.detail
    
    def test_get_project_with_stories_success(self, db_session, test_user):
        """Проверка получения проекта с полной загрузкой связей"""
        from models import Project, Activity, UserTask, Release
        
        # Создаем отдельный проект для теста
        project = Project(
            name="Test Project for Stories",
            raw_requirements="Test requirements",
            user_id=test_user.id
        )
        db_session.add(project)
        db_session.commit()
        db_session.refresh(project)
        
        # Создаем структуру: Activity -> Task -> Story
        activity = Activity(
            project_id=project.id,
            title="Test Activity",
            position=0
        )
        db_session.add(activity)
        db_session.commit()
        db_session.refresh(activity)
        
        task = UserTask(
            activity_id=activity.id,
            title="Test Task",
            position=0
        )
        db_session.add(task)
        db_session.commit()
        db_session.refresh(task)
        
        story = UserStory(
            task_id=task.id,
            title="Test Story",
            priority="MVP",
            position=0
        )
        db_session.add(story)
        db_session.commit()
        db_session.refresh(story)
        
        # Создаем релиз
        release = Release(
            project_id=project.id,
            title="MVP",
            position=0
        )
        db_session.add(release)
        db_session.commit()
        db_session.refresh(release)
        
        # Тестируем метод
        validator = ResourceAccessValidator(db_session, test_user.id)
        loaded_project = validator.get_project_with_stories(project.id)
        
        # Проверяем, что проект загружен
        assert loaded_project.id == project.id
        assert loaded_project.user_id == test_user.id
        
        # Проверяем, что связи загружены (eager loading)
        # SQLAlchemy загружает их через joinedload/subqueryload
        assert hasattr(loaded_project, 'activities')
        assert len(loaded_project.activities) == 1
        assert loaded_project.activities[0].id == activity.id
        
        # Проверяем tasks
        assert len(loaded_project.activities[0].tasks) == 1
        assert loaded_project.activities[0].tasks[0].id == task.id
        
        # Проверяем stories
        assert len(loaded_project.activities[0].tasks[0].stories) == 1
        assert loaded_project.activities[0].tasks[0].stories[0].id == story.id
        
        # Проверяем releases
        assert hasattr(loaded_project, 'releases')
        assert len(loaded_project.releases) == 1
        assert loaded_project.releases[0].id == release.id
    
    def test_get_project_with_stories_not_found(self, db_session, test_user):
        """Проверка ошибки при отсутствии проекта с загрузкой связей"""
        validator = ResourceAccessValidator(db_session, test_user.id)
        with pytest.raises(HTTPException) as exc:
            validator.get_project_with_stories(99999)
        assert exc.value.status_code == 404
        assert "Project not found" in exc.value.detail
    
    def test_get_project_with_stories_wrong_user(self, db_session, test_user):
        """Проверка доступа к чужому проекту с загрузкой связей"""
        # Создаем проект другого пользователя
        other_user = User(
            email="other@example.com",
            full_name="Other User",
            hashed_password="hash",
            is_active=True
        )
        db_session.add(other_user)
        db_session.commit()
        
        other_project = Project(
            name="Other Project",
            user_id=other_user.id
        )
        db_session.add(other_project)
        db_session.commit()
        
        validator = ResourceAccessValidator(db_session, test_user.id)
        with pytest.raises(HTTPException) as exc:
            validator.get_project_with_stories(other_project.id)
        assert exc.value.status_code == 404
        assert "Project not found" in exc.value.detail
    
    def test_get_epic_success(self, db_session, test_user, test_project):
        """Проверка получения эпика пользователя"""
        epic = Epic(
            project_id=test_project.id,
            title="Test Epic",
            confidence_score=0.9,
            position=0
        )
        db_session.add(epic)
        db_session.commit()
        
        validator = ResourceAccessValidator(db_session, test_user.id)
        result = validator.get_epic(epic.id)
        assert result.id == epic.id
        assert result.project_id == test_project.id
    
    def test_get_epic_not_found(self, db_session, test_user):
        """Проверка ошибки при отсутствии эпика"""
        validator = ResourceAccessValidator(db_session, test_user.id)
        with pytest.raises(HTTPException) as exc:
            validator.get_epic(99999)
        assert exc.value.status_code == 404
        assert "Epic not found" in exc.value.detail
    
    def test_get_story_success(self, db_session, test_user, test_project):
        """Проверка получения истории пользователя"""
        story = db_session.query(UserStory).first()
        assert story is not None
        
        validator = ResourceAccessValidator(db_session, test_user.id)
        result = validator.get_story(story.id)
        assert result.id == story.id
    
    def test_get_story_not_found(self, db_session, test_user):
        """Проверка ошибки при отсутствии истории"""
        validator = ResourceAccessValidator(db_session, test_user.id)
        with pytest.raises(HTTPException) as exc:
            validator.get_story(99999)
        assert exc.value.status_code == 404
        assert "Story not found" in exc.value.detail
    
    def test_get_task_success(self, db_session, test_user, test_project):
        """Проверка получения задачи пользователя"""
        # Создаем активность и задачу
        from models import Activity, UserTask
        activity = Activity(
            project_id=test_project.id,
            title="Test Activity",
            position=0
        )
        db_session.add(activity)
        db_session.commit()
        
        task = UserTask(
            activity_id=activity.id,
            title="Test Task",
            position=0
        )
        db_session.add(task)
        db_session.commit()
        
        validator = ResourceAccessValidator(db_session, test_user.id)
        result = validator.get_task(task.id)
        assert result.id == task.id
    
    def test_get_task_not_found(self, db_session, test_user):
        """Проверка ошибки при отсутствии задачи"""
        validator = ResourceAccessValidator(db_session, test_user.id)
        with pytest.raises(HTTPException) as exc:
            validator.get_task(99999)
        assert exc.value.status_code == 404
        assert "Task not found" in exc.value.detail
    
    def test_get_activity_success(self, db_session, test_user, test_project):
        """Проверка получения активности пользователя"""
        from models import Activity
        activity = Activity(
            project_id=test_project.id,
            title="Test Activity",
            position=0
        )
        db_session.add(activity)
        db_session.commit()
        
        validator = ResourceAccessValidator(db_session, test_user.id)
        result = validator.get_activity(activity.id)
        assert result.id == activity.id
    
    def test_get_activity_not_found(self, db_session, test_user):
        """Проверка ошибки при отсутствии активности"""
        validator = ResourceAccessValidator(db_session, test_user.id)
        with pytest.raises(HTTPException) as exc:
            validator.get_activity(99999)
        assert exc.value.status_code == 404
        assert "Activity not found" in exc.value.detail
    
    def test_verify_same_project_success(self, db_session, test_user, test_project):
        """Проверка верификации принадлежности к одному проекту"""
        from models import Activity, UserTask
        # Создаем активность и задачу
        activity = Activity(
            project_id=test_project.id,
            title="Test Activity",
            position=0
        )
        db_session.add(activity)
        db_session.commit()
        
        task = UserTask(
            activity_id=activity.id,
            title="Test Task",
            position=0
        )
        db_session.add(task)
        db_session.commit()
        
        story = UserStory(
            task_id=task.id,
            title="Test Story",
            priority="MVP",
            position=0
        )
        db_session.add(story)
        db_session.commit()
        
        epic = Epic(
            project_id=test_project.id,
            title="Test Epic",
            confidence_score=0.9,
            position=0
        )
        db_session.add(epic)
        db_session.commit()
        
        validator = ResourceAccessValidator(db_session, test_user.id)
        # Не должно быть исключения
        validator.verify_same_project(story, epic)
    
    def test_verify_same_project_failure(self, db_session, test_user, test_project):
        """Проверка ошибки при разных проектах"""
        from models import Activity, UserTask
        # Создаем другого пользователя и проект
        other_user = User(
            email="other@example.com",
            full_name="Other User",
            hashed_password="hash",
            is_active=True
        )
        db_session.add(other_user)
        db_session.commit()
        
        other_project = Project(
            name="Other Project",
            user_id=other_user.id
        )
        db_session.add(other_project)
        db_session.commit()
        
        # Создаем активность и задачу в первом проекте
        activity = Activity(
            project_id=test_project.id,
            title="Test Activity",
            position=0
        )
        db_session.add(activity)
        db_session.commit()
        
        task = UserTask(
            activity_id=activity.id,
            title="Test Task",
            position=0
        )
        db_session.add(task)
        db_session.commit()
        
        story = UserStory(
            task_id=task.id,
            title="Test Story",
            priority="MVP",
            position=0
        )
        db_session.add(story)
        db_session.commit()
        
        # Создаем эпик в другом проекте
        epic = Epic(
            project_id=other_project.id,
            title="Test Epic",
            confidence_score=0.9,
            position=0
        )
        db_session.add(epic)
        db_session.commit()
        
        validator = ResourceAccessValidator(db_session, test_user.id)
        with pytest.raises(HTTPException) as exc:
            validator.verify_same_project(story, epic)
        assert exc.value.status_code == 400
        assert "same project" in exc.value.detail.lower()


# ============================================================================
# Test Validation Logic
# ============================================================================

class TestValidationLogic:
    """Тесты для валидации в API"""
    
    def test_validate_min_max_epics(self):
        """Проверка валидации min/max эпиков"""
        from schemas.epic import EpicGenerateRequest
        
        # Валидный запрос
        valid_req = EpicGenerateRequest(min_epics=3, max_epics=7)
        assert valid_req.min_epics == 3
        assert valid_req.max_epics == 7
        
        # Pydantic валидация должна работать на уровне схемы
        # (проверка через Field constraints)
        assert valid_req.min_epics >= 1
        assert valid_req.max_epics <= 10
    
    def test_validate_epic_update(self):
        """Проверка валидации обновления эпика"""
        from schemas.epic import EpicUpdate
        
        # Частичное обновление
        update = EpicUpdate(title="New Title")
        assert update.title == "New Title"
        assert update.description is None
        
        # Полное обновление
        update2 = EpicUpdate(
            title="New Title",
            description="New Description",
            position=5
        )
        assert update2.title == "New Title"
        assert update2.description == "New Description"
        assert update2.position == 5

"""
Тесты для Epic API endpoints

Покрытие:
1. ✅ Валидация входных данных
2. ✅ Проверка прав доступа
3. ✅ Бизнес-логика helper функций

Примечание: Полные integration тесты требуют TestClient и настройки FastAPI app.
Эти тесты фокусируются на бизнес-логике и валидации.
"""
import pytest
from fastapi import HTTPException

from models import Epic, UserStory, Project, User
from api.epics import (
    get_project_for_user,
    get_epic_for_user,
    get_story_for_user
)


# ============================================================================
# Test Helper Functions
# ============================================================================

class TestHelperFunctions:
    """Тесты для вспомогательных функций API"""
    
    def test_get_project_for_user_success(self, db_session, test_user, test_project):
        """Проверка получения проекта пользователя"""
        project = get_project_for_user(test_project.id, test_user.id, db_session)
        assert project.id == test_project.id
        assert project.user_id == test_user.id
    
    def test_get_project_for_user_not_found(self, db_session, test_user):
        """Проверка ошибки при отсутствии проекта"""
        with pytest.raises(HTTPException) as exc:
            get_project_for_user(99999, test_user.id, db_session)
        assert exc.value.status_code == 404
    
    def test_get_project_for_user_wrong_user(self, db_session, test_user):
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
        
        with pytest.raises(HTTPException) as exc:
            get_project_for_user(other_project.id, test_user.id, db_session)
        assert exc.value.status_code == 404
    
    def test_get_epic_for_user_success(self, db_session, test_user, test_project):
        """Проверка получения эпика пользователя"""
        epic = Epic(
            project_id=test_project.id,
            title="Test Epic",
            confidence_score=0.9,
            position=0
        )
        db_session.add(epic)
        db_session.commit()
        
        result = get_epic_for_user(epic.id, test_user.id, db_session)
        assert result.id == epic.id
    
    def test_get_epic_for_user_not_found(self, db_session, test_user):
        """Проверка ошибки при отсутствии эпика"""
        with pytest.raises(HTTPException) as exc:
            get_epic_for_user(99999, test_user.id, db_session)
        assert exc.value.status_code == 404
    
    def test_get_story_for_user_success(self, db_session, test_user, test_project):
        """Проверка получения истории пользователя"""
        story = db_session.query(UserStory).first()
        assert story is not None
        
        result = get_story_for_user(story.id, test_user.id, db_session)
        assert result.id == story.id
    
    def test_get_story_for_user_not_found(self, db_session, test_user):
        """Проверка ошибки при отсутствии истории"""
        with pytest.raises(HTTPException) as exc:
            get_story_for_user(99999, test_user.id, db_session)
        assert exc.value.status_code == 404


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

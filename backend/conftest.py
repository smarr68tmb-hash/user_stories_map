"""
Pytest configuration and fixtures for backend tests

Provides:
- Database fixtures (in-memory SQLite for tests)
- Mock Redis client
- Common test data fixtures
"""
import pytest
from unittest.mock import Mock, MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

# Import только models - без main.py (избегаем циклических зависимостей)
from models import Base, User, RefreshToken, Project, Activity, UserTask, Release, UserStory, Epic
from services.auth_service import get_password_hash


# ============================================================================
# Database Fixtures
# ============================================================================

# Тестовая БД в памяти (SQLite)
SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(autouse=True)
def reset_db():
    """
    Автоматически создает чистую схему БД перед каждым тестом.
    Это гарантирует изоляцию тестов друг от друга.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    # Cleanup после теста
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session() -> Session:
    """
    Создает тестовую сессию БД.

    Usage:
        def test_something(db_session):
            user = User(email="test@example.com", ...)
            db_session.add(user)
            db_session.commit()
    """
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def mock_db():
    """
    Mock database session для unit-тестов без реальной БД.

    Usage:
        def test_service(mock_db):
            mock_db.query.return_value.filter.return_value.first.return_value = user
    """
    mock = Mock(spec=Session)
    return mock


# ============================================================================
# Redis Fixtures
# ============================================================================

@pytest.fixture
def mock_redis():
    """
    Mock Redis client для тестирования кеширования.

    Usage:
        def test_caching(mock_redis):
            mock_redis.get.return_value = cached_data
            result = my_function(redis_client=mock_redis)
    """
    mock = Mock()
    mock.get.return_value = None  # По умолчанию cache miss
    mock.set.return_value = True
    mock.setex.return_value = True
    mock.delete.return_value = True
    return mock


# ============================================================================
# User Fixtures
# ============================================================================

@pytest.fixture
def test_user_data():
    """
    Данные тестового пользователя.
    Пароль соответствует требованиям безопасности.
    """
    return {
        "email": "test@example.com",
        "password": "TestPassword123!",
        "full_name": "Test User"
    }


@pytest.fixture
def test_user(db_session, test_user_data):
    """
    Создает тестового пользователя в БД.

    Usage:
        def test_auth(test_user):
            # test_user уже существует в БД
            assert test_user.email == "test@example.com"
    """
    user = User(
        email=test_user_data["email"],
        full_name=test_user_data["full_name"],
        hashed_password=get_password_hash(test_user_data["password"]),
        is_active=True
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # Добавляем plain password для тестов аутентификации
    user.plain_password = test_user_data["password"]

    return user


@pytest.fixture
def inactive_user(db_session):
    """Неактивный пользователь для тестов доступа"""
    user = User(
        email="inactive@example.com",
        full_name="Inactive User",
        hashed_password=get_password_hash("Password123!"),
        is_active=False
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user


# ============================================================================
# Project Fixtures
# ============================================================================

@pytest.fixture
def test_project(db_session, test_user):
    """
    Создает тестовый проект с базовой структурой.

    Returns:
        Project с 1 activity, 1 task, 1 story, 3 releases
    """
    project = Project(
        name="Test Project",
        raw_requirements="Test requirements",
        user_id=test_user.id
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    # Создаем релизы
    releases = []
    for i, title in enumerate(["MVP", "Release 1", "Later"]):
        release = Release(
            title=title,
            position=i,
            project_id=project.id
        )
        db_session.add(release)
        releases.append(release)

    db_session.commit()

    # Создаем Activity → Task → Story
    activity = Activity(
        title="Test Activity",
        project_id=project.id,
        position=0
    )
    db_session.add(activity)
    db_session.commit()
    db_session.refresh(activity)

    task = UserTask(
        title="Test Task",
        activity_id=activity.id,
        position=0
    )
    db_session.add(task)
    db_session.commit()
    db_session.refresh(task)

    story = UserStory(
        title="Test Story",
        description="As a user, I want to test",
        task_id=task.id,
        release_id=releases[0].id,
        priority="MVP",
        position=0,
        acceptance_criteria=["Test criterion 1", "Test criterion 2"]
    )
    db_session.add(story)
    db_session.commit()

    # Refresh для загрузки связей
    db_session.refresh(project)

    return project


@pytest.fixture
def complex_project(db_session, test_user):
    """
    Создает сложный проект для тестов валидации и similarity.

    Returns:
        Project с 2 activities, несколькими tasks и stories
    """
    project = Project(
        name="Complex Project",
        requirements="Complex requirements",
        user_id=test_user.id
    )
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)

    # Релизы
    releases = []
    for i, title in enumerate(["MVP", "Release 1", "Later"]):
        release = Release(title=title, order=i, project_id=project.id)
        db_session.add(release)
        releases.append(release)
    db_session.commit()

    # Activity 1
    activity1 = Activity(title="User Management", project_id=project.id, position=0)
    db_session.add(activity1)
    db_session.commit()

    task1 = UserTask(title="Registration", activity_id=activity1.id, position=0)
    db_session.add(task1)
    db_session.commit()

    # Stories для task1
    stories_data = [
        {"title": "Email Registration", "desc": "Register with email", "priority": "MVP"},
        {"title": "Social Login", "desc": "Login with social", "priority": "Release 1"},
    ]

    for i, data in enumerate(stories_data):
        story = UserStory(
            title=data["title"],
            description=data["desc"],
            task_id=task1.id,
            release_id=releases[0].id if data["priority"] == "MVP" else releases[1].id,
            priority=data["priority"],
            position=i,
            acceptance_criteria=["Criterion 1", "Criterion 2"]
        )
        db_session.add(story)

    db_session.commit()
    db_session.refresh(project)

    return project


# ============================================================================
# Mock AI Service
# ============================================================================

@pytest.fixture
def mock_ai_response():
    """
    Mock ответ от AI сервиса для generate_ai_map
    """
    return {
        "productName": "Test Product",
        "personas": ["User", "Admin"],
        "map": [
            {
                "activity": "Test Activity",
                "tasks": [
                    {
                        "taskTitle": "Test Task",
                        "stories": [
                            {
                                "title": "Test Story",
                                "description": "As a user, I want to test",
                                "priority": "MVP",
                                "acceptanceCriteria": ["Criterion 1"]
                            }
                        ]
                    }
                ]
            }
        ]
    }


@pytest.fixture
def mock_enhancement_response():
    """
    Mock ответ от AI сервиса для enhance_requirements
    """
    return {
        "enhanced_text": "Enhanced requirements with details",
        "original_text": "Original requirements",
        "added_aspects": ["Added role: User"],
        "missing_info": ["Payment method not specified"],
        "detected_product_type": "web",
        "detected_roles": ["User", "Admin"],
        "confidence": 0.85
    }


# ============================================================================
# Utility Fixtures
# ============================================================================

@pytest.fixture
def mock_logger():
    """Mock logger для тестов без реального логирования"""
    return Mock()


@pytest.fixture(autouse=True)
def disable_rate_limiting(monkeypatch):
    """
    Автоматически отключает rate limiting для всех тестов.
    Это ускоряет тесты и избегает проблем с лимитами.
    """
    # Можно добавить патчи для rate limiter если нужно
    pass

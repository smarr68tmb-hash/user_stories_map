"""
Тесты для ResponseFormatter - форматирование ответов API

Покрытие:
1. ✅ Форматирование историй (StoryResponse)
2. ✅ Форматирование задач (TaskResponse)
3. ✅ Форматирование активностей (ActivityResponse)
4. ✅ Форматирование релизов (ReleaseResponse)
5. ✅ Форматирование проектов (ProjectResponse)
6. ✅ Обработка пустых списков
7. ✅ Обработка None значений
"""
import pytest

from models import UserStory, UserTask, Activity, Project, Release
from utils import ResponseFormatter
from schemas import StoryResponse, TaskResponse, ActivityResponse, ReleaseResponse, ProjectResponse


# ============================================================================
# Test Story Formatting
# ============================================================================

class TestStoryFormatting:
    """Тесты для форматирования историй"""
    
    def test_format_story_basic(self, db_session, test_project):
        """Проверка базового форматирования истории"""
        from models import Activity, UserTask
        
        activity = Activity(project_id=test_project.id, title="Test Activity", position=0)
        db_session.add(activity)
        db_session.commit()
        
        task = UserTask(activity_id=activity.id, title="Test Task", position=0)
        db_session.add(task)
        db_session.commit()
        
        story = UserStory(
            task_id=task.id,
            title="Test Story",
            description="Test Description",
            priority="MVP",
            acceptance_criteria=["Criterion 1", "Criterion 2"],
            position=0,
            status="todo"
        )
        db_session.add(story)
        db_session.commit()
        
        formatter = ResponseFormatter()
        result = formatter.format_story(story)
        
        assert isinstance(result, StoryResponse)
        assert result.id == story.id
        assert result.title == "Test Story"
        assert result.description == "Test Description"
        assert result.priority == "MVP"
        assert result.acceptance_criteria == ["Criterion 1", "Criterion 2"]
        assert result.position == 0
        assert result.status == "todo"
    
    def test_format_story_with_none_values(self, db_session, test_project):
        """Проверка форматирования истории с None значениями"""
        from models import Activity, UserTask
        
        activity = Activity(project_id=test_project.id, title="Test Activity", position=0)
        db_session.add(activity)
        db_session.commit()
        
        task = UserTask(activity_id=activity.id, title="Test Task", position=0)
        db_session.add(task)
        db_session.commit()
        
        story = UserStory(
            task_id=task.id,
            title="Test Story",
            description=None,
            priority=None,
            acceptance_criteria=None,
            position=0,
            status=None
        )
        db_session.add(story)
        db_session.commit()
        
        formatter = ResponseFormatter()
        result = formatter.format_story(story)
        
        assert result.description is None
        assert result.priority is None
        assert result.acceptance_criteria == []  # Должно быть пустым списком
        assert result.status == "todo"  # Дефолтное значение
    
    def test_format_stories_list(self, db_session, test_project):
        """Проверка форматирования списка историй"""
        from models import Activity, UserTask
        
        activity = Activity(project_id=test_project.id, title="Test Activity", position=0)
        db_session.add(activity)
        db_session.commit()
        
        task = UserTask(activity_id=activity.id, title="Test Task", position=0)
        db_session.add(task)
        db_session.commit()
        
        stories = []
        for i in range(3):
            story = UserStory(
                task_id=task.id,
                title=f"Story {i}",
                position=i
            )
            db_session.add(story)
            stories.append(story)
        db_session.commit()
        
        formatter = ResponseFormatter()
        result = formatter.format_stories(stories)
        
        assert len(result) == 3
        assert all(isinstance(r, StoryResponse) for r in result)
        assert result[0].title == "Story 0"
        assert result[1].title == "Story 1"
        assert result[2].title == "Story 2"
    
    def test_format_stories_empty_list(self):
        """Проверка форматирования пустого списка историй"""
        formatter = ResponseFormatter()
        result = formatter.format_stories([])
        
        assert result == []
        assert isinstance(result, list)


# ============================================================================
# Test Task Formatting
# ============================================================================

class TestTaskFormatting:
    """Тесты для форматирования задач"""
    
    def test_format_task_with_stories(self, db_session, test_project):
        """Проверка форматирования задачи с историями"""
        from models import Activity
        
        activity = Activity(project_id=test_project.id, title="Test Activity", position=0)
        db_session.add(activity)
        db_session.commit()
        
        task = UserTask(activity_id=activity.id, title="Test Task", position=0)
        db_session.add(task)
        db_session.commit()
        
        # Добавляем истории
        for i in range(2):
            story = UserStory(
                task_id=task.id,
                title=f"Story {i}",
                position=i
            )
            db_session.add(story)
        db_session.commit()
        
        formatter = ResponseFormatter()
        result = formatter.format_task(task, include_stories=True)
        
        assert isinstance(result, TaskResponse)
        assert result.id == task.id
        assert result.title == "Test Task"
        assert len(result.stories) == 2
        assert all(isinstance(s, StoryResponse) for s in result.stories)
    
    def test_format_task_without_stories(self, db_session, test_project):
        """Проверка форматирования задачи без историй"""
        from models import Activity
        
        activity = Activity(project_id=test_project.id, title="Test Activity", position=0)
        db_session.add(activity)
        db_session.commit()
        
        task = UserTask(activity_id=activity.id, title="Test Task", position=0)
        db_session.add(task)
        db_session.commit()
        
        formatter = ResponseFormatter()
        result = formatter.format_task(task, include_stories=False)
        
        assert isinstance(result, TaskResponse)
        assert result.id == task.id
        assert result.stories == []


# ============================================================================
# Test Activity Formatting
# ============================================================================

class TestActivityFormatting:
    """Тесты для форматирования активностей"""
    
    def test_format_activity_with_tasks(self, db_session, test_project):
        """Проверка форматирования активности с задачами"""
        activity = Activity(project_id=test_project.id, title="Test Activity", position=0)
        db_session.add(activity)
        db_session.commit()
        
        # Добавляем задачи
        for i in range(2):
            task = UserTask(activity_id=activity.id, title=f"Task {i}", position=i)
            db_session.add(task)
        db_session.commit()
        
        formatter = ResponseFormatter()
        result = formatter.format_activity(activity, include_tasks=True)
        
        assert isinstance(result, ActivityResponse)
        assert result.id == activity.id
        assert result.title == "Test Activity"
        assert len(result.tasks) == 2
        assert all(isinstance(t, TaskResponse) for t in result.tasks)


# ============================================================================
# Test Release Formatting
# ============================================================================

class TestReleaseFormatting:
    """Тесты для форматирования релизов"""
    
    def test_format_release(self, db_session, test_project):
        """Проверка форматирования релиза"""
        release = Release(project_id=test_project.id, title="MVP", position=0)
        db_session.add(release)
        db_session.commit()
        
        formatter = ResponseFormatter()
        result = formatter.format_release(release)
        
        assert isinstance(result, ReleaseResponse)
        assert result.id == release.id
        assert result.title == "MVP"
        assert result.position == 0
    
    def test_format_releases_list(self, db_session, test_project):
        """Проверка форматирования списка релизов"""
        releases = []
        for i, title in enumerate(["MVP", "Release 1", "Later"]):
            release = Release(project_id=test_project.id, title=title, position=i)
            db_session.add(release)
            releases.append(release)
        db_session.commit()
        
        formatter = ResponseFormatter()
        result = formatter.format_releases(releases)
        
        assert len(result) == 3
        assert all(isinstance(r, ReleaseResponse) for r in result)
        assert result[0].title == "MVP"
        assert result[1].title == "Release 1"
        assert result[2].title == "Later"


# ============================================================================
# Test Project Formatting
# ============================================================================

class TestProjectFormatting:
    """Тесты для форматирования проектов"""
    
    def test_format_project_full(self, db_session, test_project):
        """Проверка полного форматирования проекта"""
        from models import Activity, UserTask
        
        # Добавляем активности
        activity = Activity(project_id=test_project.id, title="Test Activity", position=0)
        db_session.add(activity)
        db_session.commit()
        
        # Добавляем задачи
        task = UserTask(activity_id=activity.id, title="Test Task", position=0)
        db_session.add(task)
        db_session.commit()
        
        # Добавляем релизы
        release = Release(project_id=test_project.id, title="MVP", position=0)
        db_session.add(release)
        db_session.commit()
        
        # Обновляем проект с отношениями
        db_session.refresh(test_project)
        
        formatter = ResponseFormatter()
        result = formatter.format_project(test_project)
        
        assert isinstance(result, ProjectResponse)
        assert result.id == test_project.id
        assert result.name == test_project.name
        assert len(result.activities) == 1
        assert len(result.releases) == 1
        assert result.activities[0].title == "Test Activity"
        assert result.releases[0].title == "MVP"


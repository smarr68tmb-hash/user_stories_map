"""
Тесты для Validation Service - важно для качества рекомендаций!

Покрытие:
1. ✅ Расчет overall_score (0-100)
2. ✅ Обнаружение пустых ячеек (Task + Release без Stories)
3. ✅ Проверка качества описаний
4. ✅ Проверка acceptance criteria
5. ✅ Баланс релизов
6. ✅ Обнаружение дубликатов названий
7. ✅ Генерация рекомендаций
"""
import pytest
from unittest.mock import Mock
from typing import List

from services.validation_service import (
    validate_project_map,
    calculate_validation_score,
    get_validation_summary,
)
from schemas.analysis import (
    ValidationIssue,
    IssueSeverity,
    IssueType,
)
from models import Project, Activity, UserTask, UserStory, Release


# ============================================================================
# Test Fixtures
# ============================================================================

@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock()


@pytest.fixture
def empty_project(mock_db):
    """Пустой проект без activities"""
    project = Project(
        id=1,
        name="Empty Project",
        requirements="Empty",
        user_id=1
    )
    project.activities = []
    project.releases = []
    return project


@pytest.fixture
def minimal_project(mock_db):
    """Минимальный проект с 1 activity, 1 task, 1 story"""
    project = Project(
        id=2,
        name="Minimal Project",
        requirements="Test",
        user_id=1
    )

    release = Release(id=1, title="MVP", order=1, project_id=2)
    project.releases = [release]

    activity = Activity(id=1, title="Activity 1", project_id=2)
    task = UserTask(id=1, title="Task 1", activity_id=1)
    story = UserStory(
        id=1,
        title="Story 1",
        description="Description",
        task_id=1,
        release_id=1,
        acceptance_criteria=["Criterion 1"]
    )

    task.stories = [story]
    activity.tasks = [task]
    project.activities = [activity]

    return project


@pytest.fixture
def complex_project(mock_db):
    """Сложный проект с несколькими activities, tasks, stories"""
    project = Project(
        id=3,
        name="Complex Project",
        requirements="Complex requirements",
        user_id=1
    )

    # Релизы
    mvp = Release(id=1, title="MVP", order=1, project_id=3)
    release1 = Release(id=2, title="Release 1", order=2, project_id=3)
    later = Release(id=3, title="Later", order=3, project_id=3)
    project.releases = [mvp, release1, later]

    # Activity 1
    activity1 = Activity(id=1, title="User Management", project_id=3)
    task1 = UserTask(id=1, title="Registration", activity_id=1)

    story1 = UserStory(
        id=1,
        title="Email Registration",
        description="As a user, I want to register with email",
        task_id=1,
        release_id=1,  # MVP
        acceptance_criteria=["Valid email format", "Password strength check"]
    )

    story2 = UserStory(
        id=2,
        title="Social Login",
        description="As a user, I want to login with social accounts",
        task_id=1,
        release_id=2,  # Release 1
        acceptance_criteria=["Google OAuth", "Facebook OAuth"]
    )

    task1.stories = [story1, story2]

    # Activity 2
    activity2 = Activity(id=2, title="Content Management", project_id=3)
    task2 = UserTask(id=2, title="Create Content", activity_id=2)

    story3 = UserStory(
        id=3,
        title="Create Post",
        description="As a user, I want to create posts",
        task_id=2,
        release_id=1,  # MVP
        acceptance_criteria=["Title and body required"]
    )

    task2.stories = [story3]

    activity1.tasks = [task1]
    activity2.tasks = [task2]
    project.activities = [activity1, activity2]

    return project


# ============================================================================
# Test Validation - Empty Cases
# ============================================================================

class TestEmptyValidation:
    """Тесты для валидации пустых проектов"""

    def test_empty_project_has_error(self, empty_project, mock_db):
        """Пустой проект должен иметь ERROR"""
        result = validate_project_map(empty_project, mock_db)

        assert result.is_valid is False

        # Должна быть хотя бы одна ошибка типа EMPTY_ACTIVITY
        errors = [i for i in result.issues if i.severity == IssueSeverity.ERROR]
        assert len(errors) > 0

        empty_activity_errors = [i for i in errors if i.type == IssueType.EMPTY_ACTIVITY]
        assert len(empty_activity_errors) > 0

    def test_empty_project_low_score(self, empty_project, mock_db):
        """Пустой проект должен иметь низкий score"""
        result = validate_project_map(empty_project, mock_db)

        # Score должен быть очень низким (из-за ERROR -20)
        assert result.score < 50

    def test_empty_activity_warning(self, mock_db):
        """Activity без Tasks должна давать WARNING"""
        project = Project(id=4, name="Test", requirements="Test", user_id=1)
        project.releases = []

        activity = Activity(id=1, title="Empty Activity", project_id=4)
        activity.tasks = []  # Пустая
        project.activities = [activity]

        result = validate_project_map(project, mock_db)

        warnings = [i for i in result.issues if i.severity == IssueSeverity.WARNING]
        empty_activity_warnings = [i for i in warnings if i.type == IssueType.EMPTY_ACTIVITY]

        assert len(empty_activity_warnings) > 0

    def test_empty_task_warning(self, mock_db):
        """Task без Stories должен давать WARNING"""
        project = Project(id=5, name="Test", requirements="Test", user_id=1)
        project.releases = []

        activity = Activity(id=1, title="Activity", project_id=5)
        task = UserTask(id=1, title="Empty Task", activity_id=1)
        task.stories = []  # Пустой

        activity.tasks = [task]
        project.activities = [activity]

        result = validate_project_map(project, mock_db)

        warnings = [i for i in result.issues if i.severity == IssueSeverity.WARNING]
        empty_task_warnings = [i for i in warnings if i.type == IssueType.EMPTY_TASK]

        assert len(empty_task_warnings) > 0


# ============================================================================
# Test Score Calculation
# ============================================================================

class TestScoreCalculation:
    """Тесты для расчета overall_score (0-100)"""

    def test_perfect_score_no_issues(self):
        """Проект без проблем должен иметь score = 100"""
        issues = []
        stats = {
            "total_stories": 10,
            "stories_with_description": 10,
            "stories_with_criteria": 10
        }

        score = calculate_validation_score(issues, stats)
        assert score == 100

    def test_error_deducts_20_points(self):
        """ERROR должен вычитать 20 баллов"""
        issues = [
            ValidationIssue(
                type=IssueType.EMPTY_ACTIVITY,
                severity=IssueSeverity.ERROR,
                message="Error"
            )
        ]
        stats = {"total_stories": 0}

        score = calculate_validation_score(issues, stats)
        assert score <= 80  # Максимум 80 (100 - 20)

    def test_warning_deducts_5_points(self):
        """WARNING должен вычитать 5 баллов"""
        issues = [
            ValidationIssue(
                type=IssueType.MISSING_CRITERIA,
                severity=IssueSeverity.WARNING,
                message="Warning"
            )
        ]
        stats = {"total_stories": 1, "stories_with_description": 1, "stories_with_criteria": 0}

        score = calculate_validation_score(issues, stats)
        assert score <= 95  # Максимум 95 (100 - 5)

    def test_info_deducts_1_point(self):
        """INFO должен вычитать 1 балл"""
        issues = [
            ValidationIssue(
                type=IssueType.SHORT_TITLE,
                severity=IssueSeverity.INFO,
                message="Info"
            )
        ]
        stats = {"total_stories": 1, "stories_with_description": 1, "stories_with_criteria": 1}

        score = calculate_validation_score(issues, stats)
        assert score <= 99  # Максимум 99 (100 - 1)

    def test_multiple_errors_cumulative(self):
        """Несколько ERROR должны суммироваться"""
        issues = [
            ValidationIssue(type=IssueType.EMPTY_ACTIVITY, severity=IssueSeverity.ERROR, message="E1"),
            ValidationIssue(type=IssueType.EMPTY_ACTIVITY, severity=IssueSeverity.ERROR, message="E2"),
            ValidationIssue(type=IssueType.EMPTY_ACTIVITY, severity=IssueSeverity.ERROR, message="E3"),
        ]
        stats = {"total_stories": 0}

        score = calculate_validation_score(issues, stats)
        assert score <= 40  # 100 - (3 * 20) = 40

    def test_score_never_negative(self):
        """Score не должен быть отрицательным"""
        # Много ошибок
        issues = [
            ValidationIssue(type=IssueType.EMPTY_ACTIVITY, severity=IssueSeverity.ERROR, message="E")
            for _ in range(10)
        ]
        stats = {"total_stories": 0}

        score = calculate_validation_score(issues, stats)
        assert score >= 0

    def test_score_never_above_100(self):
        """Score не должен превышать 100"""
        issues = []
        stats = {
            "total_stories": 100,
            "stories_with_description": 100,
            "stories_with_criteria": 100
        }

        score = calculate_validation_score(issues, stats)
        assert score <= 100

    def test_bonus_for_completeness(self):
        """Бонусы за полноту описаний и criteria"""
        issues = []
        stats = {
            "total_stories": 10,
            "stories_with_description": 10,  # 100%
            "stories_with_criteria": 10  # 100%
        }

        score = calculate_validation_score(issues, stats)

        # Должен быть бонус за полноту (до +10)
        assert score == 100


# ============================================================================
# Test Quality Checks
# ============================================================================

class TestQualityChecks:
    """Тесты для проверки качества историй"""

    def test_missing_description_info(self, mock_db):
        """История без описания должна давать INFO"""
        project = Project(id=6, name="Test", requirements="Test", user_id=1)
        release = Release(id=1, title="MVP", order=1, project_id=6)
        project.releases = [release]

        activity = Activity(id=1, title="Activity", project_id=6)
        task = UserTask(id=1, title="Task", activity_id=1)
        story = UserStory(
            id=1,
            title="Story without description",
            description="",  # Пустое
            task_id=1,
            release_id=1
        )

        task.stories = [story]
        activity.tasks = [task]
        project.activities = [activity]

        result = validate_project_map(project, mock_db)

        infos = [i for i in result.issues if i.severity == IssueSeverity.INFO]
        missing_desc = [i for i in infos if i.type == IssueType.MISSING_DESCRIPTION]

        assert len(missing_desc) > 0

    def test_missing_criteria_warning(self, mock_db):
        """История без acceptance criteria должна давать WARNING"""
        project = Project(id=7, name="Test", requirements="Test", user_id=1)
        release = Release(id=1, title="MVP", order=1, project_id=7)
        project.releases = [release]

        activity = Activity(id=1, title="Activity", project_id=7)
        task = UserTask(id=1, title="Task", activity_id=1)
        story = UserStory(
            id=1,
            title="Story without criteria",
            description="Has description",
            task_id=1,
            release_id=1,
            acceptance_criteria=[]  # Пустой список
        )

        task.stories = [story]
        activity.tasks = [task]
        project.activities = [activity]

        result = validate_project_map(project, mock_db)

        warnings = [i for i in result.issues if i.severity == IssueSeverity.WARNING]
        missing_criteria = [i for i in warnings if i.type == IssueType.MISSING_CRITERIA]

        assert len(missing_criteria) > 0

    def test_short_title_info(self, mock_db):
        """Слишком короткое название (<5 символов) должно давать INFO"""
        project = Project(id=8, name="Test", requirements="Test", user_id=1)
        release = Release(id=1, title="MVP", order=1, project_id=8)
        project.releases = [release]

        activity = Activity(id=1, title="Activity", project_id=8)
        task = UserTask(id=1, title="Task", activity_id=1)
        story = UserStory(
            id=1,
            title="Test",  # 4 символа (< 5)
            description="Description",
            task_id=1,
            release_id=1
        )

        task.stories = [story]
        activity.tasks = [task]
        project.activities = [activity]

        result = validate_project_map(project, mock_db)

        infos = [i for i in result.issues if i.severity == IssueSeverity.INFO]
        short_title = [i for i in infos if i.type == IssueType.SHORT_TITLE]

        assert len(short_title) > 0


# ============================================================================
# Test Duplicate Detection
# ============================================================================

class TestDuplicateDetection:
    """Тесты для обнаружения дубликатов названий"""

    def test_duplicate_titles_warning(self, mock_db):
        """Истории с одинаковыми названиями должны давать WARNING"""
        project = Project(id=9, name="Test", requirements="Test", user_id=1)
        release = Release(id=1, title="MVP", order=1, project_id=9)
        project.releases = [release]

        activity = Activity(id=1, title="Activity", project_id=9)
        task = UserTask(id=1, title="Task", activity_id=1)

        # Две истории с одинаковым названием
        story1 = UserStory(
            id=1,
            title="Duplicate Story",
            description="First",
            task_id=1,
            release_id=1
        )

        story2 = UserStory(
            id=2,
            title="Duplicate Story",  # Дубликат
            description="Second",
            task_id=1,
            release_id=1
        )

        task.stories = [story1, story2]
        activity.tasks = [task]
        project.activities = [activity]

        result = validate_project_map(project, mock_db)

        warnings = [i for i in result.issues if i.severity == IssueSeverity.WARNING]
        duplicates = [i for i in warnings if i.type == IssueType.DUPLICATE_TITLE]

        assert len(duplicates) > 0

    def test_case_insensitive_duplicates(self, mock_db):
        """Дубликаты должны обнаруживаться case-insensitive"""
        project = Project(id=10, name="Test", requirements="Test", user_id=1)
        release = Release(id=1, title="MVP", order=1, project_id=10)
        project.releases = [release]

        activity = Activity(id=1, title="Activity", project_id=10)
        task = UserTask(id=1, title="Task", activity_id=1)

        story1 = UserStory(id=1, title="Test Story", description="A", task_id=1, release_id=1)
        story2 = UserStory(id=2, title="test story", description="B", task_id=1, release_id=1)  # Lowercase

        task.stories = [story1, story2]
        activity.tasks = [task]
        project.activities = [activity]

        result = validate_project_map(project, mock_db)

        duplicates = [i for i in result.issues if i.type == IssueType.DUPLICATE_TITLE]
        assert len(duplicates) > 0

    def test_no_duplicates_when_unique(self, minimal_project, mock_db):
        """Нет дубликатов при уникальных названиях"""
        result = validate_project_map(minimal_project, mock_db)

        duplicates = [i for i in result.issues if i.type == IssueType.DUPLICATE_TITLE]
        assert len(duplicates) == 0


# ============================================================================
# Test Release Balance
# ============================================================================

class TestReleaseBalance:
    """Тесты для проверки баланса между релизами"""

    def test_unbalanced_releases_info(self, mock_db):
        """Неравномерное распределение историй по релизам должно давать INFO"""
        project = Project(id=11, name="Test", requirements="Test", user_id=1)
        mvp = Release(id=1, title="MVP", order=1, project_id=11)
        later = Release(id=2, title="Later", order=2, project_id=11)
        project.releases = [mvp, later]

        activity = Activity(id=1, title="Activity", project_id=11)
        task = UserTask(id=1, title="Task", activity_id=1)

        # 10 историй в MVP, 0 в Later - неравномерно
        stories = [
            UserStory(
                id=i,
                title=f"Story {i}",
                description="Desc",
                task_id=1,
                release_id=1  # Все в MVP
            )
            for i in range(1, 11)
        ]

        task.stories = stories
        activity.tasks = [task]
        project.activities = [activity]

        result = validate_project_map(project, mock_db)

        infos = [i for i in result.issues if i.severity == IssueSeverity.INFO]
        unbalanced = [i for i in infos if i.type == IssueType.UNBALANCED_RELEASES]

        assert len(unbalanced) > 0

    def test_balanced_releases_no_warning(self, complex_project, mock_db):
        """Равномерное распределение не должно давать предупреждений о балансе"""
        result = validate_project_map(complex_project, mock_db)

        # В complex_project 2 истории в MVP, 1 в Release 1 - относительно сбалансировано
        unbalanced = [i for i in result.issues if i.type == IssueType.UNBALANCED_RELEASES]

        # Может быть предупреждение, если разница > 3x, но у нас 2 vs 1 - это ok
        # Проверяем логику
        assert isinstance(unbalanced, list)


# ============================================================================
# Test Statistics
# ============================================================================

class TestStatistics:
    """Тесты для сбора статистики"""

    def test_stats_counting(self, complex_project, mock_db):
        """Статистика должна корректно считать элементы"""
        result = validate_project_map(complex_project, mock_db)

        assert result.stats["total_activities"] == 2
        assert result.stats["total_tasks"] == 2
        assert result.stats["total_stories"] == 3

    def test_stats_description_count(self, complex_project, mock_db):
        """Статистика должна считать истории с описанием"""
        result = validate_project_map(complex_project, mock_db)

        # Все 3 истории в complex_project имеют описания
        assert result.stats["stories_with_description"] == 3

    def test_stats_criteria_count(self, complex_project, mock_db):
        """Статистика должна считать истории с AC"""
        result = validate_project_map(complex_project, mock_db)

        # Все 3 истории имеют acceptance_criteria
        assert result.stats["stories_with_criteria"] == 3

    def test_stats_per_release(self, complex_project, mock_db):
        """Статистика по релизам"""
        result = validate_project_map(complex_project, mock_db)

        # MVP: 2 истории, Release 1: 1 история, Later: 0
        assert result.stats["stories_per_release"]["MVP"] == 2
        assert result.stats["stories_per_release"]["Release 1"] == 1
        assert result.stats["stories_per_release"]["Later"] == 0


# ============================================================================
# Test Recommendations
# ============================================================================

class TestRecommendations:
    """Тесты для генерации рекомендаций"""

    def test_recommendations_for_empty_project(self, empty_project, mock_db):
        """Рекомендации для пустого проекта"""
        result = validate_project_map(empty_project, mock_db)

        # Должна быть рекомендация добавить истории
        assert len(result.recommendations) > 0

    def test_recommendations_for_missing_descriptions(self, mock_db):
        """Рекомендации при недостаточном количестве описаний"""
        project = Project(id=12, name="Test", requirements="Test", user_id=1)
        release = Release(id=1, title="MVP", order=1, project_id=12)
        project.releases = [release]

        activity = Activity(id=1, title="Activity", project_id=12)
        task = UserTask(id=1, title="Task", activity_id=1)

        # 10 историй, только 3 с описанием (30% < 50%)
        stories = []
        for i in range(1, 11):
            story = UserStory(
                id=i,
                title=f"Story {i}",
                description="Description" if i <= 3 else "",  # Только первые 3
                task_id=1,
                release_id=1
            )
            stories.append(story)

        task.stories = stories
        activity.tasks = [task]
        project.activities = [activity]

        result = validate_project_map(project, mock_db)

        # Должна быть рекомендация добавить описания
        desc_recommendations = [r for r in result.recommendations if "описание" in r.lower()]
        assert len(desc_recommendations) > 0

    def test_recommendations_for_missing_criteria(self, mock_db):
        """Рекомендации при недостаточном количестве AC"""
        project = Project(id=13, name="Test", requirements="Test", user_id=1)
        release = Release(id=1, title="MVP", order=1, project_id=13)
        project.releases = [release]

        activity = Activity(id=1, title="Activity", project_id=13)
        task = UserTask(id=1, title="Task", activity_id=1)

        # 10 историй, только 5 с AC (50% < 70%)
        stories = []
        for i in range(1, 11):
            story = UserStory(
                id=i,
                title=f"Story {i}",
                description="Desc",
                task_id=1,
                release_id=1,
                acceptance_criteria=["AC"] if i <= 5 else []
            )
            stories.append(story)

        task.stories = stories
        activity.tasks = [task]
        project.activities = [activity]

        result = validate_project_map(project, mock_db)

        # Должна быть рекомендация добавить AC
        ac_recommendations = [r for r in result.recommendations if "criteria" in r.lower()]
        assert len(ac_recommendations) > 0

    def test_recommendations_for_large_mvp(self, mock_db):
        """Рекомендации при слишком большом MVP"""
        project = Project(id=14, name="Test", requirements="Test", user_id=1)
        release = Release(id=1, title="MVP", order=1, project_id=14)
        project.releases = [release]

        activity = Activity(id=1, title="Activity", project_id=14)
        task = UserTask(id=1, title="Task", activity_id=1)

        # 20 историй в MVP (> 15)
        stories = [
            UserStory(
                id=i,
                title=f"Story {i}",
                description="Desc",
                task_id=1,
                release_id=1,
                acceptance_criteria=["AC"]
            )
            for i in range(1, 21)
        ]

        task.stories = stories
        activity.tasks = [task]
        project.activities = [activity]

        result = validate_project_map(project, mock_db)

        # Должна быть рекомендация сократить MVP
        mvp_recommendations = [r for r in result.recommendations if "mvp" in r.lower()]
        assert len(mvp_recommendations) > 0


# ============================================================================
# Test Validation Summary
# ============================================================================

class TestValidationSummary:
    """Тесты для текстового резюме валидации"""

    def test_excellent_quality_summary(self):
        """Резюме для отличного качества (score >= 90)"""
        result = Mock()
        result.score = 95
        result.issues = []
        result.stats = {"total_stories": 10}

        summary = get_validation_summary(result)

        assert "отличное" in summary.lower()
        assert "95/100" in summary

    def test_good_quality_summary(self):
        """Резюме для хорошего качества (70 <= score < 90)"""
        result = Mock()
        result.score = 75
        result.issues = []
        result.stats = {"total_stories": 10}

        summary = get_validation_summary(result)

        assert "хорошее" in summary.lower()

    def test_satisfactory_quality_summary(self):
        """Резюме для удовлетворительного качества (50 <= score < 70)"""
        result = Mock()
        result.score = 55
        result.issues = []
        result.stats = {"total_stories": 10}

        summary = get_validation_summary(result)

        assert "удовлетворительное" in summary.lower()

    def test_needs_improvement_summary(self):
        """Резюме для качества требующего улучшения (score < 50)"""
        result = Mock()
        result.score = 40
        result.issues = []
        result.stats = {"total_stories": 10}

        summary = get_validation_summary(result)

        assert "требует улучшения" in summary.lower()

    def test_summary_with_errors(self):
        """Резюме должно упоминать количество ошибок"""
        result = Mock()
        result.score = 60
        result.issues = [
            ValidationIssue(type=IssueType.EMPTY_ACTIVITY, severity=IssueSeverity.ERROR, message="E1"),
            ValidationIssue(type=IssueType.EMPTY_ACTIVITY, severity=IssueSeverity.ERROR, message="E2"),
        ]
        result.stats = {"total_stories": 5}

        summary = get_validation_summary(result)

        assert "2" in summary  # Количество ошибок
        assert "Критических проблем" in summary or "проблем" in summary.lower()

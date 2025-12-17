"""
Pytest tests for recommendation_service.py
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch
from sqlalchemy.orm import Session

from services.recommendation_service import (
    apply_recommendation,
    apply_add_description,
    apply_add_criteria,
    apply_merge_stories,
    apply_improve_stories,
    apply_move_stories
)
from schemas.analysis import (
    ActionableRecommendation,
    ActionType,
    IssueSeverity,
    ApplyRecommendationResponse
)
from models import UserStory, Project, Release, Activity, UserTask


@pytest.fixture
def mock_db():
    """Mock database session"""
    return Mock(spec=Session)


@pytest.fixture
def mock_project():
    """Mock project with activities, tasks, releases"""
    project = Mock(spec=Project)
    project.id = 1

    # Create mock releases
    mvp_release = Mock(spec=Release)
    mvp_release.id = 1
    mvp_release.title = "MVP"

    release1 = Mock(spec=Release)
    release1.id = 2
    release1.title = "Release 1"

    project.releases = [mvp_release, release1]

    # Create mock activities and tasks
    activity = Mock(spec=Activity)
    task = Mock(spec=UserTask)
    task.id = 1
    task.stories = []
    activity.tasks = [task]
    project.activities = [activity]

    return project


@pytest.fixture
def mock_stories():
    """Create mock user stories"""
    stories = []
    for i in range(1, 6):
        story = Mock(spec=UserStory)
        story.id = i
        story.title = f"Story {i}"
        story.description = "" if i <= 3 else f"Description for story {i}"
        story.acceptance_criteria = [] if i <= 3 else [f"AC {i}.1", f"AC {i}.2"]
        story.task_id = 1
        story.release_id = 1
        story.position = i
        stories.append(story)
    return stories


class TestApplyAddDescription:
    """Tests for apply_add_description function"""

    @pytest.mark.asyncio
    async def test_add_description_success(self, mock_db, mock_project, mock_stories):
        """Test successful description addition"""
        recommendation = ActionableRecommendation(
            id="rec_1",
            title="Add descriptions",
            description="Add descriptions to 3 stories",
            action_type=ActionType.ADD_DESCRIPTION,
            severity=IssueSeverity.INFO,
            story_ids=[1, 2, 3],
            action_params={},
            auto_applicable=False,
            impact="Improves clarity"
        )

        # Setup mock database query
        stories_to_update = mock_stories[:3]
        mock_db.query.return_value.filter.return_value.all.return_value = stories_to_update

        # Mock AI service response
        with patch('services.recommendation_service.ai_improve_story_content', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = {
                "success": True,
                "improved_story": {
                    "description": "Generated description by AI"
                }
            }

            result = await apply_add_description(recommendation, mock_project, mock_db)

        assert result.success is True
        assert len(result.affected_story_ids) == 3
        assert result.message == "Добавлено описание к 3 историям"
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_add_description_no_story_ids(self, mock_db, mock_project):
        """Test with empty story_ids"""
        recommendation = ActionableRecommendation(
            id="rec_1",
            title="Add descriptions",
            description="Test",
            action_type=ActionType.ADD_DESCRIPTION,
            severity=IssueSeverity.INFO,
            story_ids=[],
            action_params={},
            auto_applicable=False,
            impact="Test"
        )

        result = await apply_add_description(recommendation, mock_project, mock_db)

        assert result.success is False
        assert "Не указаны ID историй" in result.message

    @pytest.mark.asyncio
    async def test_add_description_stories_not_found(self, mock_db, mock_project):
        """Test when stories don't exist"""
        recommendation = ActionableRecommendation(
            id="rec_1",
            title="Add descriptions",
            description="Test",
            action_type=ActionType.ADD_DESCRIPTION,
            severity=IssueSeverity.INFO,
            story_ids=[999],
            action_params={},
            auto_applicable=False,
            impact="Test"
        )

        mock_db.query.return_value.filter.return_value.all.return_value = []

        result = await apply_add_description(recommendation, mock_project, mock_db)

        assert result.success is False
        assert "Истории не найдены" in result.message


class TestApplyAddCriteria:
    """Tests for apply_add_criteria function"""

    @pytest.mark.asyncio
    async def test_add_criteria_success(self, mock_db, mock_project, mock_stories):
        """Test successful AC addition"""
        recommendation = ActionableRecommendation(
            id="rec_2",
            title="Add AC",
            description="Add acceptance criteria",
            action_type=ActionType.ADD_CRITERIA,
            severity=IssueSeverity.WARNING,
            story_ids=[1, 2, 3],
            action_params={},
            auto_applicable=False,
            impact="Adds clear criteria"
        )

        stories_to_update = mock_stories[:3]
        mock_db.query.return_value.filter.return_value.all.return_value = stories_to_update

        with patch('services.recommendation_service.ai_improve_story_content', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = {
                "success": True,
                "improved_story": {
                    "acceptance_criteria": ["AC 1", "AC 2", "AC 3"]
                }
            }

            result = await apply_add_criteria(recommendation, mock_project, mock_db)

        assert result.success is True
        assert len(result.affected_story_ids) == 3
        assert "acceptance criteria" in result.message.lower()
        assert mock_db.commit.called


class TestApplyMergeStories:
    """Tests for apply_merge_stories function"""

    @pytest.mark.asyncio
    async def test_merge_stories_success(self, mock_db, mock_project, mock_stories):
        """Test successful story merge"""
        primary_story = mock_stories[0]
        merge_stories = mock_stories[1:3]

        recommendation = ActionableRecommendation(
            id="rec_3",
            title="Merge duplicates",
            description="Merge 2 duplicate stories",
            action_type=ActionType.MERGE_STORIES,
            severity=IssueSeverity.WARNING,
            story_ids=[1, 2, 3],
            action_params={
                "primary_story_id": 1,
                "merge_story_ids": [2, 3]
            },
            auto_applicable=False,
            impact="Removes duplicates"
        )

        # Mock database queries
        mock_db.query.return_value.filter.return_value.first.return_value = primary_story
        mock_db.query.return_value.filter.return_value.all.return_value = merge_stories

        result = await apply_merge_stories(recommendation, mock_project, mock_db)

        assert result.success is True
        assert len(result.deleted_story_ids) == 2
        assert 1 in result.affected_story_ids
        assert "Объединено" in result.message
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_merge_stories_missing_params(self, mock_db, mock_project):
        """Test merge with missing parameters"""
        recommendation = ActionableRecommendation(
            id="rec_3",
            title="Merge duplicates",
            description="Test",
            action_type=ActionType.MERGE_STORIES,
            severity=IssueSeverity.WARNING,
            story_ids=[1, 2],
            action_params={},
            auto_applicable=False,
            impact="Test"
        )

        result = await apply_merge_stories(recommendation, mock_project, mock_db)

        assert result.success is False
        assert "Не указаны ID историй" in result.message

    @pytest.mark.asyncio
    async def test_merge_stories_primary_not_found(self, mock_db, mock_project):
        """Test merge when primary story doesn't exist"""
        recommendation = ActionableRecommendation(
            id="rec_3",
            title="Merge duplicates",
            description="Test",
            action_type=ActionType.MERGE_STORIES,
            severity=IssueSeverity.WARNING,
            story_ids=[1, 2],
            action_params={
                "primary_story_id": 999,
                "merge_story_ids": [2]
            },
            auto_applicable=False,
            impact="Test"
        )

        mock_db.query.return_value.filter.return_value.first.return_value = None

        result = await apply_merge_stories(recommendation, mock_project, mock_db)

        assert result.success is False
        assert "Основная история не найдена" in result.message


class TestApplyImproveStories:
    """Tests for apply_improve_stories function"""

    @pytest.mark.asyncio
    async def test_improve_stories_success(self, mock_db, mock_project, mock_stories):
        """Test successful story improvement"""
        recommendation = ActionableRecommendation(
            id="rec_4",
            title="Improve stories",
            description="Improve 3 stories",
            action_type=ActionType.IMPROVE_STORY,
            severity=IssueSeverity.INFO,
            story_ids=[1, 2, 3],
            action_params={},
            auto_applicable=False,
            impact="Better quality"
        )

        stories_to_improve = mock_stories[:3]
        mock_db.query.return_value.filter.return_value.all.return_value = stories_to_improve

        with patch('services.recommendation_service.ai_improve_story_content', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = {
                "success": True,
                "improved_story": {
                    "description": "Improved description",
                    "acceptance_criteria": ["Improved AC 1", "Improved AC 2"]
                }
            }

            result = await apply_improve_stories(recommendation, mock_project, mock_db)

        assert result.success is True
        assert len(result.affected_story_ids) == 3
        assert "Улучшено" in result.message
        assert mock_db.commit.called

    @pytest.mark.asyncio
    async def test_improve_all_stories(self, mock_db, mock_project, mock_stories):
        """Test improving all stories in project"""
        recommendation = ActionableRecommendation(
            id="rec_4",
            title="Improve all",
            description="Improve all stories",
            action_type=ActionType.IMPROVE_STORY,
            severity=IssueSeverity.INFO,
            story_ids=[],
            action_params={"improve_all": True},
            auto_applicable=False,
            impact="Better quality"
        )

        # Setup project with stories
        task = mock_project.activities[0].tasks[0]
        task.stories = mock_stories[:10]

        mock_db.query.return_value.filter.return_value.all.return_value = mock_stories[:10]

        with patch('services.recommendation_service.ai_improve_story_content', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = {
                "success": True,
                "improved_story": {
                    "description": "Improved",
                    "acceptance_criteria": ["AC"]
                }
            }

            result = await apply_improve_stories(recommendation, mock_project, mock_db)

        assert result.success is True
        assert len(result.affected_story_ids) <= 10  # Limited to 10


class TestApplyMoveStories:
    """Tests for apply_move_stories function"""

    def test_move_stories_success(self, mock_db, mock_project, mock_stories):
        """Test successful story move between releases"""
        recommendation = ActionableRecommendation(
            id="rec_5",
            title="Move stories",
            description="Move stories from MVP to Release 1",
            action_type=ActionType.MOVE_STORY,
            severity=IssueSeverity.WARNING,
            story_ids=[],
            action_params={
                "from_release": "MVP",
                "to_release": "Release 1",
                "suggested_count": 5
            },
            auto_applicable=False,
            impact="Optimizes MVP"
        )

        # Setup stories in MVP release
        stories_in_mvp = mock_stories
        mock_db.query.return_value.filter.return_value.order_by.return_value.limit.return_value.all.return_value = stories_in_mvp

        result = apply_move_stories(recommendation, mock_project, mock_db)

        assert result.success is True
        assert len(result.affected_story_ids) == len(stories_in_mvp)
        assert "Перемещено" in result.message
        assert mock_db.commit.called

    def test_move_stories_missing_params(self, mock_db, mock_project):
        """Test move with missing parameters"""
        recommendation = ActionableRecommendation(
            id="rec_5",
            title="Move stories",
            description="Test",
            action_type=ActionType.MOVE_STORY,
            severity=IssueSeverity.WARNING,
            story_ids=[],
            action_params={},
            auto_applicable=False,
            impact="Test"
        )

        result = apply_move_stories(recommendation, mock_project, mock_db)

        assert result.success is False
        assert "Не указаны релизы" in result.message

    def test_move_stories_release_not_found(self, mock_db, mock_project):
        """Test move when release doesn't exist"""
        recommendation = ActionableRecommendation(
            id="rec_5",
            title="Move stories",
            description="Test",
            action_type=ActionType.MOVE_STORY,
            severity=IssueSeverity.WARNING,
            story_ids=[],
            action_params={
                "from_release": "NonExistent",
                "to_release": "Release 1",
                "suggested_count": 5
            },
            auto_applicable=False,
            impact="Test"
        )

        result = apply_move_stories(recommendation, mock_project, mock_db)

        assert result.success is False
        assert "Релизы не найдены" in result.message


class TestApplyRecommendation:
    """Tests for main apply_recommendation dispatcher"""

    @pytest.mark.asyncio
    async def test_dispatch_add_description(self, mock_db, mock_project, mock_stories):
        """Test dispatching to ADD_DESCRIPTION handler"""
        recommendation = ActionableRecommendation(
            id="rec_1",
            title="Test",
            description="Test",
            action_type=ActionType.ADD_DESCRIPTION,
            severity=IssueSeverity.INFO,
            story_ids=[1],
            action_params={},
            auto_applicable=False,
            impact="Test"
        )

        mock_db.query.return_value.filter.return_value.all.return_value = [mock_stories[0]]

        with patch('services.recommendation_service.ai_improve_story_content', new_callable=AsyncMock) as mock_ai:
            mock_ai.return_value = {
                "success": True,
                "improved_story": {"description": "Test"}
            }

            result = await apply_recommendation(recommendation, mock_project, mock_db)

        assert result.success is True

    @pytest.mark.asyncio
    async def test_unsupported_action_type(self, mock_db, mock_project):
        """Test unsupported action type"""
        recommendation = ActionableRecommendation(
            id="rec_x",
            title="Test",
            description="Test",
            action_type=ActionType.SPLIT_STORY,  # Not implemented
            severity=IssueSeverity.INFO,
            story_ids=[],
            action_params={},
            auto_applicable=False,
            impact="Test"
        )

        result = await apply_recommendation(recommendation, mock_project, mock_db)

        assert result.success is False
        assert "пока не поддерживается" in result.message

    @pytest.mark.asyncio
    async def test_exception_handling(self, mock_db, mock_project):
        """Test exception handling in dispatcher"""
        recommendation = ActionableRecommendation(
            id="rec_1",
            title="Test",
            description="Test",
            action_type=ActionType.ADD_DESCRIPTION,
            severity=IssueSeverity.INFO,
            story_ids=[1],
            action_params={},
            auto_applicable=False,
            impact="Test"
        )

        # Make query raise exception
        mock_db.query.side_effect = Exception("Database error")

        result = await apply_recommendation(recommendation, mock_project, mock_db)

        assert result.success is False
        assert "Ошибка при применении" in result.message

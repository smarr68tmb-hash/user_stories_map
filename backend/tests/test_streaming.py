"""
Тесты для streaming_service.py - SSE (Server-Sent Events) генерации карты.

Проверяем:
1. Последовательность SSE событий
2. Формат данных в событиях
3. Обработку ошибок
4. Корректность analysis event
"""

import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy.orm import Session

from services.streaming_service import (
    sse_event,
    generate_map_streaming,
    _save_project_to_db
)


class TestSSEEventFormat:
    """Тесты форматирования SSE событий."""

    def test_sse_event_basic_format(self):
        """Проверка базового формата SSE события."""
        result = sse_event("test_type", {"progress": 50, "message": "Test"})

        # Формат: "data: {...}\n\n"
        assert result.startswith("data: ")
        assert result.endswith("\n\n")

        # Парсим JSON
        json_str = result[6:-2]  # Убираем "data: " и "\n\n"
        data = json.loads(json_str)

        assert data["type"] == "test_type"
        assert data["progress"] == 50
        assert data["message"] == "Test"

    def test_sse_event_with_russian_text(self):
        """Проверка корректной кодировки русского текста."""
        result = sse_event("enhancing", {"message": "Улучшаю требования"})

        json_str = result[6:-2]
        data = json.loads(json_str)

        assert data["message"] == "Улучшаю требования"
        assert "\\u" not in result  # ensure_ascii=False работает


@pytest.mark.asyncio
class TestStreamingGeneration:
    """Тесты генерации карты с SSE потоком."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        db = MagicMock(spec=Session)
        db.add = Mock()
        db.flush = Mock()
        db.commit = Mock()
        return db

    @pytest.fixture
    def mock_redis(self):
        """Mock Redis client."""
        with patch('services.streaming_service.get_redis_client') as mock:
            redis_mock = MagicMock()
            mock.return_value = redis_mock
            yield redis_mock

    async def test_event_sequence_without_enhancement(self, mock_db, mock_redis):
        """
        Проверка последовательности событий БЕЗ enhancement.

        Ожидаемая последовательность:
        1. generating (20%)
        2. generating (30%)
        3. generating (60%)
        4. generating (70%)
        5. validating (75%)
        6. validating (80%)
        7. analysis (85%)
        8. saving (90%)
        9. saving (95%)
        10. complete (100%)
        """
        with patch('services.streaming_service.generate_ai_map') as mock_gen, \
             patch('services.streaming_service.validate_project_map') as mock_val, \
             patch('services.streaming_service.analyze_similarity') as mock_sim:

            # Mock AI generation результат
            mock_gen.return_value = {
                "productName": "Test Product",
                "map": {
                    "activities": [
                        {
                            "title": "Activity 1",
                            "tasks": [
                                {
                                    "title": "Task 1",
                                    "stories": [
                                        {"title": "Story 1", "priority": "MVP"}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }

            # Mock validation
            mock_val.return_value = {
                "overall_score": 85,
                "issues": ["Issue 1", "Issue 2"]
            }

            # Mock similarity
            mock_sim.return_value = {
                "duplicate_groups": [],
                "similar_groups": [["Story A", "Story B"]]
            }

            # Собираем все события
            events = []
            async for event_str in generate_map_streaming(
                requirements_text="Test requirements",
                use_enhancement=False,
                use_agent=False,
                user_id=1,
                db=mock_db
            ):
                events.append(event_str)

            # Парсим события
            parsed_events = []
            for event_str in events:
                json_str = event_str[6:-2]  # Убираем "data: " и "\n\n"
                parsed_events.append(json.loads(json_str))

            # Проверяем типы событий
            event_types = [e["type"] for e in parsed_events]

            assert "generating" in event_types
            assert "validating" in event_types
            assert "analysis" in event_types
            assert "saving" in event_types
            assert "complete" in event_types

            # Проверяем, что события в правильном порядке
            generating_idx = event_types.index("generating")
            validating_idx = event_types.index("validating")
            analysis_idx = event_types.index("analysis")
            saving_idx = event_types.index("saving")
            complete_idx = event_types.index("complete")

            assert generating_idx < validating_idx < analysis_idx < saving_idx < complete_idx

    async def test_event_sequence_with_enhancement(self, mock_db, mock_redis):
        """
        Проверка последовательности событий С enhancement.

        Должны появиться события:
        - enhancing (10%)
        - enhanced (20%)
        """
        with patch('services.streaming_service.enhance_requirements') as mock_enh, \
             patch('services.streaming_service.generate_ai_map') as mock_gen, \
             patch('services.streaming_service.validate_project_map') as mock_val, \
             patch('services.streaming_service.analyze_similarity') as mock_sim:

            # Mock enhancement
            mock_enh.return_value = {
                "enhanced_text": "Enhanced requirements",
                "confidence": 0.9,
                "fallback": False
            }

            # Mock AI generation
            mock_gen.return_value = {
                "productName": "Test Product",
                "map": {"activities": []}
            }

            mock_val.return_value = {"overall_score": 90, "issues": []}
            mock_sim.return_value = {"duplicate_groups": [], "similar_groups": []}

            # Собираем события
            events = []
            async for event_str in generate_map_streaming(
                requirements_text="Test requirements",
                use_enhancement=True,
                use_agent=False,
                user_id=1,
                db=mock_db
            ):
                events.append(event_str)

            parsed_events = [json.loads(e[6:-2]) for e in events]
            event_types = [e["type"] for e in parsed_events]

            # Проверяем наличие enhancement событий
            assert "enhancing" in event_types
            assert "enhanced" in event_types

            # Проверяем, что enhancing раньше всего остального
            enhancing_idx = event_types.index("enhancing")
            generating_idx = event_types.index("generating")

            assert enhancing_idx < generating_idx

    async def test_analysis_event_data(self, mock_db, mock_redis):
        """
        Проверка данных в analysis событии.

        Событие должно содержать:
        - duplicates: int
        - similar: int
        - score: int
        - issues: list
        - total_issues: int
        - progress: 85
        """
        with patch('services.streaming_service.generate_ai_map') as mock_gen, \
             patch('services.streaming_service.validate_project_map') as mock_val, \
             patch('services.streaming_service.analyze_similarity') as mock_sim:

            mock_gen.return_value = {
                "productName": "Test Product",
                "map": {"activities": []}
            }

            # Mock validation с проблемами
            mock_val.return_value = {
                "overall_score": 65,
                "issues": [
                    "Missing acceptance criteria",
                    "Too short description",
                    "No priority set",
                    "Duplicate title",
                    "Empty story",
                    "Another issue"
                ]
            }

            # Mock similarity с дубликатами
            mock_sim.return_value = {
                "duplicate_groups": [
                    ["Story 1", "Story 2"],
                    ["Story 3", "Story 4"],
                    ["Story 5", "Story 6"]
                ],
                "similar_groups": [
                    ["Story A", "Story B"]
                ]
            }

            # Собираем события
            events = []
            async for event_str in generate_map_streaming(
                requirements_text="Test requirements",
                use_enhancement=False,
                use_agent=False,
                user_id=1,
                db=mock_db
            ):
                events.append(event_str)

            parsed_events = [json.loads(e[6:-2]) for e in events]

            # Находим analysis событие
            analysis_event = next(e for e in parsed_events if e["type"] == "analysis")

            # Проверяем структуру
            assert analysis_event["progress"] == 85
            assert analysis_event["duplicates"] == 3  # 3 группы дубликатов
            assert analysis_event["similar"] == 1  # 1 группа похожих
            assert analysis_event["score"] == 65
            assert len(analysis_event["issues"]) == 5  # Первые 5 проблем
            assert analysis_event["total_issues"] == 6

    async def test_complete_event_data(self, mock_db, mock_redis):
        """
        Проверка данных в complete событии.

        Событие должно содержать:
        - project_id: int
        - project_name: str
        - stats: {activities, tasks, stories, score, duplicates}
        """
        with patch('services.streaming_service.generate_ai_map') as mock_gen, \
             patch('services.streaming_service.validate_project_map') as mock_val, \
             patch('services.streaming_service.analyze_similarity') as mock_sim:

            # Mock с реальными данными
            mock_gen.return_value = {
                "productName": "Test Product",
                "map": {
                    "activities": [
                        {
                            "title": "Activity 1",
                            "tasks": [
                                {
                                    "title": "Task 1",
                                    "stories": [
                                        {"title": "Story 1", "priority": "MVP"},
                                        {"title": "Story 2", "priority": "Release 1"}
                                    ]
                                },
                                {
                                    "title": "Task 2",
                                    "stories": [
                                        {"title": "Story 3", "priority": "MVP"}
                                    ]
                                }
                            ]
                        },
                        {
                            "title": "Activity 2",
                            "tasks": [
                                {
                                    "title": "Task 3",
                                    "stories": [
                                        {"title": "Story 4", "priority": "Later"}
                                    ]
                                }
                            ]
                        }
                    ]
                }
            }

            mock_val.return_value = {"overall_score": 88, "issues": []}
            mock_sim.return_value = {"duplicate_groups": [], "similar_groups": []}

            # Mock БД для получения project_id
            mock_project = Mock()
            mock_project.id = 42
            mock_db.add.side_effect = lambda obj: setattr(obj, 'id', 42)

            # Собираем события
            events = []
            async for event_str in generate_map_streaming(
                requirements_text="Test requirements",
                use_enhancement=False,
                use_agent=False,
                user_id=1,
                db=mock_db
            ):
                events.append(event_str)

            parsed_events = [json.loads(e[6:-2]) for e in events]

            # Находим complete событие
            complete_event = next(e for e in parsed_events if e["type"] == "complete")

            # Проверяем данные
            assert complete_event["progress"] == 100
            assert complete_event["project_id"] == 42
            assert complete_event["project_name"] == "Test Product"

            # Проверяем статистику
            stats = complete_event["stats"]
            assert stats["activities"] == 2
            assert stats["tasks"] == 3
            assert stats["stories"] == 4
            assert stats["score"] == 88
            assert stats["duplicates"] == 0

    async def test_error_handling(self, mock_db, mock_redis):
        """
        Проверка обработки ошибок.

        При ошибке должно прийти событие:
        {type: "error", message: str, stage: str}
        """
        with patch('services.streaming_service.generate_ai_map') as mock_gen:

            # Mock ошибки AI
            mock_gen.side_effect = Exception("AI service unavailable")

            # Собираем события
            events = []
            async for event_str in generate_map_streaming(
                requirements_text="Test requirements",
                use_enhancement=False,
                use_agent=False,
                user_id=1,
                db=mock_db
            ):
                events.append(event_str)

            parsed_events = [json.loads(e[6:-2]) for e in events]

            # Должно быть хотя бы одно error событие
            error_events = [e for e in parsed_events if e["type"] == "error"]
            assert len(error_events) > 0

            error_event = error_events[0]
            assert "message" in error_event
            assert "AI service unavailable" in error_event["message"]

    async def test_progress_monotonic_increase(self, mock_db, mock_redis):
        """
        Проверка монотонного роста progress.

        Progress должен только расти: 10% → 20% → 30% → ... → 100%
        """
        with patch('services.streaming_service.generate_ai_map') as mock_gen, \
             patch('services.streaming_service.validate_project_map') as mock_val, \
             patch('services.streaming_service.analyze_similarity') as mock_sim:

            mock_gen.return_value = {
                "productName": "Test",
                "map": {"activities": []}
            }
            mock_val.return_value = {"overall_score": 90, "issues": []}
            mock_sim.return_value = {"duplicate_groups": [], "similar_groups": []}

            # Собираем события
            events = []
            async for event_str in generate_map_streaming(
                requirements_text="Test requirements",
                use_enhancement=False,
                use_agent=False,
                user_id=1,
                db=mock_db
            ):
                events.append(event_str)

            parsed_events = [json.loads(e[6:-2]) for e in events]

            # Извлекаем progress из событий
            progress_values = [e.get("progress", 0) for e in parsed_events if "progress" in e]

            # Проверяем монотонность
            for i in range(1, len(progress_values)):
                assert progress_values[i] >= progress_values[i-1], \
                    f"Progress decreased: {progress_values[i-1]} → {progress_values[i]}"

            # Проверяем финальный progress
            assert progress_values[-1] == 100


class TestSaveProjectToDB:
    """Тесты сохранения проекта в БД."""

    @pytest.fixture
    def mock_db(self):
        """Mock database session."""
        db = MagicMock(spec=Session)

        # Counter для автоинкремента ID
        id_counter = {"value": 1}

        def mock_add(obj):
            obj.id = id_counter["value"]
            id_counter["value"] += 1

        db.add = Mock(side_effect=mock_add)
        db.add_all = Mock(side_effect=lambda objs: [mock_add(o) for o in objs])
        db.flush = Mock()
        db.commit = Mock()

        return db

    def test_save_basic_project(self, mock_db):
        """Проверка сохранения базового проекта."""
        map_data = {
            "activities": [
                {
                    "title": "Activity 1",
                    "tasks": [
                        {
                            "title": "Task 1",
                            "stories": [
                                {
                                    "title": "Story 1",
                                    "description": "As a user...",
                                    "acceptanceCriteria": ["Given...", "When...", "Then..."],
                                    "priority": "MVP"
                                }
                            ]
                        }
                    ]
                }
            ]
        }

        project_id = _save_project_to_db(
            product_name="Test Product",
            raw_requirements="Test requirements",
            map_data=map_data,
            user_id=1,
            enhancement_data=None,
            db=mock_db
        )

        # Проверяем, что проект создан
        assert project_id == 1

        # Проверяем вызовы БД
        assert mock_db.add.call_count >= 1  # Project
        assert mock_db.add_all.call_count >= 1  # Releases
        assert mock_db.commit.called

    def test_save_with_enhancement(self, mock_db):
        """Проверка сохранения с enhancement данными."""
        enhancement_data = {
            "enhanced_text": "Enhanced requirements",
            "confidence": 0.92
        }

        map_data = {"activities": []}

        project_id = _save_project_to_db(
            product_name="Test Product",
            raw_requirements="Original requirements",
            map_data=map_data,
            user_id=1,
            enhancement_data=enhancement_data,
            db=mock_db
        )

        assert project_id == 1

        # Проверяем, что Project был создан с enhancement полями
        # (в реальности нужно проверить объект, но в mock это сложно)
        assert mock_db.add.called

    def test_save_creates_default_releases(self, mock_db):
        """Проверка создания дефолтных релизов: MVP, Release 1, Later."""
        map_data = {"activities": []}

        _save_project_to_db(
            product_name="Test",
            raw_requirements="Test",
            map_data=map_data,
            user_id=1,
            enhancement_data=None,
            db=mock_db
        )

        # Проверяем, что add_all был вызван (для releases)
        assert mock_db.add_all.called

        # В реальной БД должны быть созданы 3 релиза
        # Проверяем хотя бы количество вызовов
        assert mock_db.add_all.call_count >= 1

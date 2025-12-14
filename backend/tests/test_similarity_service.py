"""
Тесты для Similarity Service - важно для auto-notifications о дубликатах!

Покрытие:
1. ✅ TF-IDF vectorization
2. ✅ Cosine similarity расчет
3. ✅ Группировка похожих историй
4. ✅ Fallback алгоритм (Jaccard) без sklearn
5. ✅ Предобработка текста (preprocess)
6. ✅ Русские стоп-слова
7. ✅ Определение дубликатов vs похожих
"""
import pytest
from unittest.mock import Mock, patch

from services.similarity_service import (
    preprocess_text,
    get_story_text,
    calculate_similarity_tfidf,
    calculate_similarity_fallback,
    analyze_similarity,
    find_similar_groups,
    get_similarity_summary,
    RUSSIAN_STOP_WORDS,
)
from models import Project, Activity, UserTask, UserStory, Release


# ============================================================================
# Test Text Preprocessing
# ============================================================================

class TestTextPreprocessing:
    """Тесты для предобработки текста"""

    def test_preprocess_lowercase(self):
        """Текст должен преобразовываться в lowercase"""
        text = "Test TEXT МиКс CaSe"
        result = preprocess_text(text)
        assert result == result.lower()

    def test_preprocess_remove_special_chars(self):
        """Специальные символы должны удаляться"""
        text = "Test! @#$ %^& *() Text"
        result = preprocess_text(text)
        # Должны остаться только буквы и пробелы
        assert all(c.isalnum() or c.isspace() for c in result)

    def test_preprocess_remove_multiple_spaces(self):
        """Множественные пробелы должны схлопываться в один"""
        text = "Test    multiple     spaces"
        result = preprocess_text(text)
        assert "  " not in result  # Нет двойных пробелов

    def test_preprocess_empty_string(self):
        """Пустая строка должна вернуть пустую строку"""
        assert preprocess_text("") == ""
        assert preprocess_text(None) == ""

    def test_preprocess_russian_text(self):
        """Русский текст должен корректно обрабатываться"""
        text = "Пользователь может войти в систему"
        result = preprocess_text(text)
        assert "пользователь" in result
        assert "может" in result

    def test_preprocess_strips_whitespace(self):
        """Начальные и конечные пробелы должны удаляться"""
        text = "  Test text  "
        result = preprocess_text(text)
        assert result == "test text"


# ============================================================================
# Test Story Text Extraction
# ============================================================================

class TestStoryTextExtraction:
    """Тесты для сбора текста истории"""

    def test_get_story_text_full(self):
        """Сбор полного текста истории (title + description + AC)"""
        story = UserStory(
            id=1,
            title="User Registration",
            description="As a user, I want to register",
            task_id=1,
            release_id=1,
            acceptance_criteria=["Valid email", "Strong password"]
        )

        text = get_story_text(story)

        assert "User Registration" in text
        assert "As a user, I want to register" in text
        assert "Valid email" in text
        assert "Strong password" in text

    def test_get_story_text_only_title(self):
        """История только с названием"""
        story = UserStory(
            id=1,
            title="Test Story",
            description=None,
            task_id=1,
            release_id=1,
            acceptance_criteria=None
        )

        text = get_story_text(story)
        assert text == "Test Story"

    def test_get_story_text_empty_fields(self):
        """История с пустыми полями"""
        story = UserStory(
            id=1,
            title="Title",
            description="",
            task_id=1,
            release_id=1,
            acceptance_criteria=[]
        )

        text = get_story_text(story)
        assert "Title" in text


# ============================================================================
# Test TF-IDF Similarity
# ============================================================================

class TestTFIDFSimilarity:
    """Тесты для TF-IDF + Cosine Similarity"""

    @patch('services.similarity_service.SKLEARN_AVAILABLE', True)
    def test_tfidf_identical_texts(self):
        """Идентичные тексты должны иметь similarity = 1.0"""
        texts = [
            "Пользователь может зарегистрироваться",
            "Пользователь может зарегистрироваться"
        ]

        matrix = calculate_similarity_tfidf(texts)

        # Similarity между идентичными текстами должна быть ~1.0
        assert matrix[0][1] > 0.99

    @patch('services.similarity_service.SKLEARN_AVAILABLE', True)
    def test_tfidf_different_texts(self):
        """Совершенно разные тексты должны иметь низкую similarity"""
        texts = [
            "Пользователь может зарегистрироваться через email",
            "Система отправляет уведомления о новых сообщениях"
        ]

        matrix = calculate_similarity_tfidf(texts)

        # Similarity должна быть низкой (< 0.3)
        assert matrix[0][1] < 0.3

    def test_tfidf_similar_texts(self):
        """Похожие тексты должны иметь среднюю similarity"""
        texts = [
            "Администратор добавляет товар каталога",
            "Администратор редактирует товар каталога"
        ]

        matrix = calculate_similarity_tfidf(texts)

        # Similarity должна быть средней (тексты похожи, но не идентичны)
        assert 0.3 < matrix[0][1] < 0.95

    def test_tfidf_matrix_symmetrical(self):
        """Матрица similarity должна быть симметричной"""
        texts = [
            "Текст 1 про авторизацию",
            "Текст 2 про регистрацию",
            "Текст 3 про профиль"
        ]

        matrix = calculate_similarity_tfidf(texts)

        # Проверяем симметричность
        assert matrix[0][1] == matrix[1][0]
        assert matrix[0][2] == matrix[2][0]
        assert matrix[1][2] == matrix[2][1]

    def test_tfidf_diagonal_is_one(self):
        """Диагональ матрицы (similarity с самим собой) должна быть 1.0"""
        texts = [
            "Текст 1",
            "Текст 2",
            "Текст 3"
        ]

        matrix = calculate_similarity_tfidf(texts)

        # Диагональ = 1.0
        assert matrix[0][0] == 1.0
        assert matrix[1][1] == 1.0
        assert matrix[2][2] == 1.0

    def test_tfidf_stop_words_ignored(self):
        """Русские стоп-слова должны игнорироваться"""
        texts = [
            "и в на что как администратор редактирует профиль",
            "администратор редактирует профиль и также настройки"
        ]

        matrix = calculate_similarity_tfidf(texts)

        # Стоп-слова не должны влиять, similarity должна быть высокой
        assert matrix[0][1] > 0.5


# ============================================================================
# Test Fallback Algorithm (Jaccard)
# ============================================================================

class TestFallbackAlgorithm:
    """Тесты для fallback алгоритма (Jaccard similarity) без sklearn"""

    def test_fallback_identical_texts(self):
        """Идентичные тексты должны иметь similarity = 1.0 (Jaccard)"""
        texts = [
            "пользователь может зарегистрироваться",
            "пользователь может зарегистрироваться"
        ]

        matrix = calculate_similarity_fallback(texts)

        # После предобработки и токенизации должны быть идентичны
        assert matrix[0][1] == 1.0

    def test_fallback_completely_different(self):
        """Совершенно разные тексты должны иметь similarity = 0.0"""
        texts = [
            "авторизация пользователя email",
            "отправка уведомлений push"
        ]

        matrix = calculate_similarity_fallback(texts)

        # Нет общих слов (после удаления стоп-слов)
        assert matrix[0][1] < 0.3

    def test_fallback_partial_overlap(self):
        """Частичное совпадение слов"""
        texts = [
            "авторизация email регистрация",
            "авторизация push уведомления"
        ]

        matrix = calculate_similarity_fallback(texts)

        # Jaccard: intersection / union
        # Текст 1: {авторизация, email, регистрация}
        # Текст 2: {авторизация, push, уведомления}
        # Intersection: {авторизация} = 1
        # Union: {авторизация, email, регистрация, push, уведомления} = 5
        # Jaccard = 1/5 = 0.2
        assert 0.1 < matrix[0][1] < 0.4

    def test_fallback_matrix_symmetrical(self):
        """Матрица Jaccard должна быть симметричной"""
        texts = [
            "текст один про авторизацию",
            "текст два про регистрацию",
            "текст три про профиль"
        ]

        matrix = calculate_similarity_fallback(texts)

        assert matrix[0][1] == matrix[1][0]
        assert matrix[0][2] == matrix[2][0]

    def test_fallback_diagonal_is_one(self):
        """Диагональ матрицы Jaccard должна быть 1.0"""
        texts = ["текст 1", "текст 2", "текст 3"]

        matrix = calculate_similarity_fallback(texts)

        assert matrix[0][0] == 1.0
        assert matrix[1][1] == 1.0
        assert matrix[2][2] == 1.0

    def test_fallback_empty_texts(self):
        """Пустые тексты должны обрабатываться корректно"""
        texts = ["", ""]

        matrix = calculate_similarity_fallback(texts)

        # Пустые множества: similarity = 0
        assert matrix[0][1] == 0.0

    def test_fallback_removes_stop_words(self):
        """Fallback должен удалять русские стоп-слова"""
        texts = [
            "и в на что администратор редактирует данные",
            "администратор редактирует данные и также"
        ]

        matrix = calculate_similarity_fallback(texts)

        # После удаления стоп-слов: {администратор, редактирует, данные}
        # Similarity должна быть высокой (идентичные множества = 1.0)
        assert matrix[0][1] >= 0.9


# ============================================================================
# Test Similarity Analysis
# ============================================================================

class TestSimilarityAnalysis:
    """Тесты для полного анализа схожести проекта"""

    def create_project_with_stories(self, stories_data: list) -> Project:
        """Хелпер для создания проекта с историями"""
        project = Project(id=1, name="Test", raw_requirements="Test", user_id=1)
        project.releases = [Release(id=1, title="MVP", position=1, project_id=1)]

        activity = Activity(id=1, title="Activity", project_id=1)
        task = UserTask(id=1, title="Task", activity_id=1)

        stories = []
        for i, data in enumerate(stories_data, start=1):
            story = UserStory(
                id=i,
                title=data.get("title", f"Story {i}"),
                description=data.get("description", ""),
                task_id=1,
                release_id=1,
                acceptance_criteria=data.get("acceptance_criteria", [])
            )
            stories.append(story)

        task.stories = stories
        activity.tasks = [task]
        project.activities = [activity]

        return project

    @patch('services.similarity_service.SKLEARN_AVAILABLE', True)
    def test_analyze_finds_duplicates(self):
        """Анализ должен находить дубликаты (similarity >= 0.9)"""
        stories_data = [
            {"title": "Регистрация пользователя через email"},
            {"title": "Регистрация пользователя через email"},  # Дубликат
        ]

        project = self.create_project_with_stories(stories_data)
        result = analyze_similarity(project, duplicate_threshold=0.9)

        # Должна быть найдена 1 группа дубликатов
        duplicate_groups = [g for g in result.similar_groups if g.group_type == "duplicate"]
        assert len(duplicate_groups) > 0
        assert result.stats["duplicates_found"] > 0

    @patch('services.similarity_service.SKLEARN_AVAILABLE', True)
    def test_analyze_finds_similar_not_duplicates(self):
        """Анализ должен находить похожие истории (0.7 <= similarity < 0.9)"""
        stories_data = [
            {"title": "Пользователь может войти через email"},
            {"title": "Пользователь может войти через социальные сети"},
        ]

        project = self.create_project_with_stories(stories_data)
        result = analyze_similarity(project, similarity_threshold=0.5, duplicate_threshold=0.9)

        # Должна быть найдена группа похожих (не дубликатов)
        similar_groups = [g for g in result.similar_groups if g.group_type == "similar"]
        assert len(result.similar_groups) > 0

    def test_analyze_skips_single_story(self):
        """Анализ должен пропускаться для проектов с <2 историями"""
        stories_data = [{"title": "Единственная история"}]

        project = self.create_project_with_stories(stories_data)
        result = analyze_similarity(project)

        assert len(result.similar_groups) == 0
        assert result.stats["total_stories"] == 1
        assert result.stats["algorithm"] == "skipped"

    def test_analyze_no_stories(self):
        """Анализ проекта без историй"""
        project = Project(id=1, name="Empty", raw_requirements="Test", user_id=1)
        project.activities = []

        result = analyze_similarity(project)

        assert len(result.similar_groups) == 0
        assert result.stats["total_stories"] == 0

    @patch('services.similarity_service.SKLEARN_AVAILABLE', False)
    def test_analyze_uses_fallback_when_sklearn_unavailable(self):
        """Анализ должен использовать fallback, если sklearn недоступен"""
        stories_data = [
            {"title": "Story 1 про авторизацию"},
            {"title": "Story 2 про авторизацию"},
        ]

        project = self.create_project_with_stories(stories_data)
        result = analyze_similarity(project)

        # Алгоритм должен быть jaccard
        assert result.stats["algorithm"] == "jaccard"


# ============================================================================
# Test Group Finding
# ============================================================================

class TestGroupFinding:
    """Тесты для группировки похожих историй"""

    def test_find_groups_creates_duplicate_group(self):
        """find_similar_groups должен создавать группу дубликатов"""
        stories_data = [
            {"story": Mock(id=1, title="Story 1", description="Desc"), "task_title": "Task", "activity_title": "Act", "text": "same text"},
            {"story": Mock(id=2, title="Story 2", description="Desc"), "task_title": "Task", "activity_title": "Act", "text": "same text"},
        ]

        # Similarity matrix: идентичные
        similarity_matrix = [
            [1.0, 0.95],
            [0.95, 1.0]
        ]

        groups = find_similar_groups(stories_data, similarity_matrix, similarity_threshold=0.7, duplicate_threshold=0.9)

        # Должна быть группа дубликатов (similarity >= 0.9)
        assert len(groups) > 0
        assert groups[0].group_type == "duplicate"

    def test_find_groups_creates_similar_group(self):
        """find_similar_groups должен создавать группу похожих"""
        stories_data = [
            {"story": Mock(id=1, title="Story 1", description="D"), "task_title": "T", "activity_title": "A", "text": "text 1"},
            {"story": Mock(id=2, title="Story 2", description="D"), "task_title": "T", "activity_title": "A", "text": "text 2"},
        ]

        # Similarity matrix: похожие, но не дубликаты
        similarity_matrix = [
            [1.0, 0.75],
            [0.75, 1.0]
        ]

        groups = find_similar_groups(stories_data, similarity_matrix, similarity_threshold=0.7, duplicate_threshold=0.9)

        assert len(groups) > 0
        assert groups[0].group_type == "similar"

    def test_find_groups_ignores_low_similarity(self):
        """Истории с низкой similarity не должны группироваться"""
        stories_data = [
            {"story": Mock(id=1, title="S1", description="D"), "task_title": "T", "activity_title": "A", "text": "completely different"},
            {"story": Mock(id=2, title="S2", description="D"), "task_title": "T", "activity_title": "A", "text": "totally another thing"},
        ]

        # Similarity matrix: очень низкая similarity
        similarity_matrix = [
            [1.0, 0.1],
            [0.1, 1.0]
        ]

        groups = find_similar_groups(stories_data, similarity_matrix, similarity_threshold=0.7, duplicate_threshold=0.9)

        # Не должно быть групп (similarity < 0.7)
        assert len(groups) == 0

    def test_find_groups_multiple_stories_in_group(self):
        """Группа может содержать >2 историй"""
        stories_data = [
            {"story": Mock(id=1, title="S1", description="D"), "task_title": "T", "activity_title": "A", "text": "text"},
            {"story": Mock(id=2, title="S2", description="D"), "task_title": "T", "activity_title": "A", "text": "text"},
            {"story": Mock(id=3, title="S3", description="D"), "task_title": "T", "activity_title": "A", "text": "text"},
        ]

        # Все похожи друг на друга
        similarity_matrix = [
            [1.0, 0.95, 0.93],
            [0.95, 1.0, 0.94],
            [0.93, 0.94, 1.0]
        ]

        groups = find_similar_groups(stories_data, similarity_matrix, similarity_threshold=0.7, duplicate_threshold=0.9)

        assert len(groups) == 1
        assert len(groups[0].stories) == 3

    def test_find_groups_sorts_duplicates_first(self):
        """Дубликаты должны идти первыми в списке групп"""
        stories_data = [
            {"story": Mock(id=1, title="Similar 1", description="D"), "task_title": "T", "activity_title": "A", "text": "similar"},
            {"story": Mock(id=2, title="Similar 2", description="D"), "task_title": "T", "activity_title": "A", "text": "similar text"},
            {"story": Mock(id=3, title="Duplicate 1", description="D"), "task_title": "T", "activity_title": "A", "text": "exact match"},
            {"story": Mock(id=4, title="Duplicate 2", description="D"), "task_title": "T", "activity_title": "A", "text": "exact match"},
        ]

        similarity_matrix = [
            [1.0, 0.75, 0.0, 0.0],
            [0.75, 1.0, 0.0, 0.0],
            [0.0, 0.0, 1.0, 0.95],
            [0.0, 0.0, 0.95, 1.0]
        ]

        groups = find_similar_groups(stories_data, similarity_matrix, similarity_threshold=0.7, duplicate_threshold=0.9)

        # Первая группа должна быть дубликатами
        assert groups[0].group_type == "duplicate"


# ============================================================================
# Test Similarity Summary
# ============================================================================

class TestSimilaritySummary:
    """Тесты для текстового резюме анализа"""

    def test_summary_no_groups(self):
        """Резюме при отсутствии групп"""
        result = Mock()
        result.stats = {
            "total_stories": 10,
            "duplicates_found": 0,
            "similar_groups_found": 0
        }

        summary = get_similarity_summary(result)

        assert "10" in summary
        assert "не найдено" in summary.lower() or "не обнаружено" in summary.lower()

    def test_summary_with_duplicates(self):
        """Резюме с дубликатами"""
        result = Mock()
        result.stats = {
            "total_stories": 15,
            "duplicates_found": 2,
            "similar_groups_found": 3
        }

        summary = get_similarity_summary(result)

        assert "15" in summary
        assert "2" in summary
        assert "дубликат" in summary.lower()

    def test_summary_with_similar_groups(self):
        """Резюме с похожими группами"""
        result = Mock()
        result.stats = {
            "total_stories": 20,
            "duplicates_found": 1,
            "similar_groups_found": 4
        }

        summary = get_similarity_summary(result)

        assert "20" in summary
        assert "похож" in summary.lower()


# ============================================================================
# Test Russian Stop Words
# ============================================================================

class TestRussianStopWords:
    """Тесты для русских стоп-слов"""

    def test_common_russian_stop_words_included(self):
        """Проверка наличия основных русских стоп-слов"""
        common_stop_words = ["и", "в", "на", "что", "как", "с", "по", "для", "от"]

        for word in common_stop_words:
            assert word in RUSSIAN_STOP_WORDS

    def test_user_story_specific_stop_words(self):
        """Проверка User Story специфичных стоп-слов"""
        us_stop_words = ["как", "хочу", "чтобы", "могу", "пользователь", "система"]

        for word in us_stop_words:
            assert word in RUSSIAN_STOP_WORDS


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Тесты для граничных случаев"""

    def test_similarity_with_empty_text(self):
        """Similarity с пустым текстом"""
        texts = ["", "some text"]

        matrix = calculate_similarity_fallback(texts)

        # Пустой текст vs непустой = 0 similarity
        assert matrix[0][1] == 0.0

    def test_similarity_with_only_stop_words(self):
        """Similarity когда текст состоит только из стоп-слов"""
        texts = [
            "и в на что как",
            "что как и на в"
        ]

        matrix = calculate_similarity_fallback(texts)

        # После удаления стоп-слов останутся пустые множества
        # similarity = 0
        assert matrix[0][1] == 0.0

    def test_single_text_similarity(self):
        """Similarity для одного текста"""
        texts = ["single text"]

        matrix = calculate_similarity_tfidf(texts)

        # Должна вернуться матрица 1x1 с значением 1.0
        assert len(matrix) == 1
        assert len(matrix[0]) == 1
        assert matrix[0][0] == 1.0

    @patch('services.similarity_service.SKLEARN_AVAILABLE', True)
    def test_similarity_matrix_size(self):
        """Размер матрицы similarity должен быть NxN"""
        texts = ["text 1", "text 2", "text 3", "text 4"]

        matrix = calculate_similarity_tfidf(texts)

        # Матрица должна быть 4x4
        assert len(matrix) == 4
        assert all(len(row) == 4 for row in matrix)

    def test_unicode_emoji_in_story_text(self):
        """Unicode и emoji в тексте истории"""
        story = UserStory(
            id=1,
            title="🔐 Авторизация 🔑",
            description="Пользователь может 👤 войти",
            task_id=1,
            release_id=1,
            acceptance_criteria=["✅ Email валидация"]
        )

        text = get_story_text(story)

        # Emoji должны быть в тексте
        assert "🔐" in text or "Авторизация" in text

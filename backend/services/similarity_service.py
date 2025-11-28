"""
Сервис анализа схожести User Stories через TF-IDF
"""
import logging
import re
from typing import List, Dict, Tuple, Optional
from collections import defaultdict

from models import Project, UserStory
from schemas.analysis import (
    SimilarityResult,
    SimilarityGroup,
    SimilarStory,
    StoryConflict,
    ConflictType
)

logger = logging.getLogger(__name__)

# Попытка импорта sklearn - может быть не установлен
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    logger.warning("scikit-learn not installed. Using fallback similarity algorithm.")


# Русские стоп-слова для TF-IDF
RUSSIAN_STOP_WORDS = [
    'и', 'в', 'во', 'не', 'что', 'он', 'на', 'я', 'с', 'со', 'как', 'а', 'то', 'все',
    'она', 'так', 'его', 'но', 'да', 'ты', 'к', 'у', 'же', 'вы', 'за', 'бы', 'по',
    'только', 'её', 'мне', 'было', 'вот', 'от', 'меня', 'еще', 'нет', 'о', 'из',
    'ему', 'теперь', 'когда', 'уже', 'вам', 'ни', 'быть', 'был', 'него', 'до',
    'вас', 'нибудь', 'опять', 'уж', 'вам', 'ведь', 'там', 'потом', 'себя', 'ничего',
    'ей', 'может', 'они', 'тут', 'где', 'есть', 'надо', 'ней', 'для', 'мы', 'тебя',
    'их', 'чем', 'была', 'сам', 'чтоб', 'без', 'будто', 'чего', 'раз', 'тоже', 'себе',
    'под', 'будет', 'ж', 'тогда', 'кто', 'этот', 'того', 'потому', 'этого', 'какой',
    'совсем', 'ним', 'здесь', 'этом', 'один', 'почти', 'мой', 'тем', 'чтобы', 'нее',
    'сейчас', 'были', 'куда', 'зачем', 'всех', 'никогда', 'можно', 'при', 'наконец',
    'два', 'об', 'другой', 'хоть', 'после', 'над', 'больше', 'тот', 'через', 'эти',
    'нас', 'про', 'всего', 'них', 'какая', 'много', 'разве', 'три', 'эту', 'моя',
    'впрочем', 'хорошо', 'свою', 'этой', 'перед', 'иногда', 'лучше', 'чуть', 'том',
    'нельзя', 'такой', 'им', 'более', 'всегда', 'конечно', 'всю', 'между',
    # User Story специфичные
    'как', 'хочу', 'чтобы', 'могу', 'пользователь', 'система', 'должен', 'должна'
]


def preprocess_text(text: str) -> str:
    """Предобработка текста для анализа"""
    if not text:
        return ""
    
    # Приводим к нижнему регистру
    text = text.lower()
    
    # Убираем специальные символы, оставляем только буквы и пробелы
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Убираем множественные пробелы
    text = re.sub(r'\s+', ' ', text)
    
    return text.strip()


def get_story_text(story: UserStory) -> str:
    """Собирает полный текст истории для анализа"""
    parts = [story.title or ""]
    
    if story.description:
        parts.append(story.description)
    
    if story.acceptance_criteria:
        parts.extend(story.acceptance_criteria)
    
    return " ".join(parts)


def calculate_similarity_tfidf(texts: List[str]) -> List[List[float]]:
    """
    Рассчитывает матрицу схожести через TF-IDF + Cosine Similarity
    
    Returns:
        Матрица схожести NxN
    """
    if not SKLEARN_AVAILABLE:
        return calculate_similarity_fallback(texts)
    
    if len(texts) < 2:
        return [[1.0]]
    
    # Создаем TF-IDF векторизатор
    vectorizer = TfidfVectorizer(
        stop_words=RUSSIAN_STOP_WORDS,
        ngram_range=(1, 2),  # Униграммы и биграммы
        min_df=1,
        max_df=0.95
    )
    
    try:
        # Векторизуем тексты
        tfidf_matrix = vectorizer.fit_transform(texts)
        
        # Рассчитываем косинусное сходство
        similarity_matrix = cosine_similarity(tfidf_matrix)
        
        return similarity_matrix.tolist()
    except Exception as e:
        logger.warning(f"TF-IDF calculation failed: {e}. Using fallback.")
        return calculate_similarity_fallback(texts)


def calculate_similarity_fallback(texts: List[str]) -> List[List[float]]:
    """
    Fallback алгоритм схожести на основе Jaccard similarity
    Используется если sklearn не установлен
    """
    n = len(texts)
    if n == 0:
        return []
    
    # Токенизируем тексты
    tokenized = []
    for text in texts:
        words = set(preprocess_text(text).split())
        # Убираем стоп-слова
        words = words - set(RUSSIAN_STOP_WORDS)
        tokenized.append(words)
    
    # Рассчитываем Jaccard similarity
    matrix = [[0.0] * n for _ in range(n)]
    
    for i in range(n):
        for j in range(n):
            if i == j:
                matrix[i][j] = 1.0
            elif i < j:
                set1, set2 = tokenized[i], tokenized[j]
                if not set1 or not set2:
                    similarity = 0.0
                else:
                    intersection = len(set1 & set2)
                    union = len(set1 | set2)
                    similarity = intersection / union if union > 0 else 0.0
                
                matrix[i][j] = similarity
                matrix[j][i] = similarity
    
    return matrix


def analyze_similarity(
    project: Project,
    similarity_threshold: float = 0.7,
    duplicate_threshold: float = 0.9
) -> SimilarityResult:
    """
    Анализирует схожесть историй в проекте
    
    Args:
        project: Объект проекта с загруженными связями
        similarity_threshold: Порог для группировки похожих (0.5-1.0)
        duplicate_threshold: Порог для определения дубликатов (0.8-1.0)
    
    Returns:
        SimilarityResult: Результат анализа схожести
    """
    # Собираем все истории
    stories_data: List[Dict] = []
    
    for activity in project.activities:
        for task in activity.tasks:
            for story in task.stories:
                stories_data.append({
                    "story": story,
                    "task_title": task.title,
                    "activity_title": activity.title,
                    "text": get_story_text(story)
                })
    
    if len(stories_data) < 2:
        logger.info(f"Project {project.id} has less than 2 stories, skipping similarity analysis")
        return SimilarityResult(
            similar_groups=[],
            potential_conflicts=[],
            stats={
                "total_stories": len(stories_data),
                "duplicates_found": 0,
                "similar_groups_found": 0,
                "algorithm": "skipped"
            }
        )
    
    # Подготавливаем тексты
    texts = [preprocess_text(sd["text"]) for sd in stories_data]
    
    # Рассчитываем матрицу схожести
    similarity_matrix = calculate_similarity_tfidf(texts)
    
    # Находим группы похожих историй
    similar_groups = find_similar_groups(
        stories_data,
        similarity_matrix,
        similarity_threshold,
        duplicate_threshold
    )
    
    # Статистика
    duplicates_count = sum(1 for g in similar_groups if g.group_type == "duplicate")
    
    stats = {
        "total_stories": len(stories_data),
        "duplicates_found": duplicates_count,
        "similar_groups_found": len(similar_groups),
        "algorithm": "tfidf" if SKLEARN_AVAILABLE else "jaccard"
    }
    
    logger.info(
        f"Similarity analysis for project {project.id}: "
        f"{len(similar_groups)} groups found, {duplicates_count} potential duplicates"
    )
    
    return SimilarityResult(
        similar_groups=similar_groups,
        potential_conflicts=[],  # Конфликты определяются через AI отдельно
        stats=stats
    )


def find_similar_groups(
    stories_data: List[Dict],
    similarity_matrix: List[List[float]],
    similarity_threshold: float,
    duplicate_threshold: float
) -> List[SimilarityGroup]:
    """
    Находит группы похожих историй на основе матрицы схожести
    
    Использует алгоритм:
    1. Находим все пары с similarity >= threshold
    2. Группируем связанные истории (union-find)
    3. Классифицируем группы как duplicates или similar
    """
    n = len(stories_data)
    groups: List[SimilarityGroup] = []
    
    # Union-Find для группировки
    parent = list(range(n))
    
    def find(x):
        if parent[x] != x:
            parent[x] = find(parent[x])
        return parent[x]
    
    def union(x, y):
        px, py = find(x), find(y)
        if px != py:
            parent[px] = py
    
    # Находим пары с высокой схожестью
    pairs_with_similarity: List[Tuple[int, int, float]] = []
    
    for i in range(n):
        for j in range(i + 1, n):
            sim = similarity_matrix[i][j]
            if sim >= similarity_threshold:
                union(i, j)
                pairs_with_similarity.append((i, j, sim))
    
    # Группируем по компонентам
    components: Dict[int, List[int]] = defaultdict(list)
    for i in range(n):
        components[find(i)].append(i)
    
    # Формируем группы
    for component_id, indices in components.items():
        if len(indices) < 2:
            continue
        
        # Определяем тип группы (duplicate или similar)
        max_similarity = 0.0
        for i, idx1 in enumerate(indices):
            for idx2 in indices[i + 1:]:
                sim = similarity_matrix[idx1][idx2]
                max_similarity = max(max_similarity, sim)
        
        is_duplicate = max_similarity >= duplicate_threshold
        group_type = "duplicate" if is_duplicate else "similar"
        
        # Формируем список историй в группе
        similar_stories = []
        for idx in indices:
            sd = stories_data[idx]
            story = sd["story"]
            
            # Находим среднюю схожесть с остальными в группе
            avg_sim = 0.0
            count = 0
            for other_idx in indices:
                if other_idx != idx:
                    avg_sim += similarity_matrix[idx][other_idx]
                    count += 1
            avg_sim = avg_sim / count if count > 0 else 1.0
            
            similar_stories.append(SimilarStory(
                id=story.id,
                title=story.title,
                description=story.description,
                similarity=round(avg_sim, 2),
                task_title=sd["task_title"],
                activity_title=sd["activity_title"]
            ))
        
        # Сортируем по схожести (от большей к меньшей)
        similar_stories.sort(key=lambda x: x.similarity, reverse=True)
        
        # Генерируем рекомендацию
        if is_duplicate:
            recommendation = (
                "Возможные дубликаты. Рекомендуется объединить истории или "
                "уточнить их различия."
            )
        else:
            recommendation = (
                "Похожие истории. Проверьте, не пересекается ли функциональность. "
                "Возможно, стоит разграничить scope каждой истории."
            )
        
        groups.append(SimilarityGroup(
            stories=similar_stories,
            group_type=group_type,
            recommendation=recommendation
        ))
    
    # Сортируем группы: дубликаты первыми, затем по размеру
    groups.sort(key=lambda g: (0 if g.group_type == "duplicate" else 1, -len(g.stories)))
    
    return groups


def get_similarity_summary(result: SimilarityResult) -> str:
    """Генерирует текстовое резюме анализа схожести"""
    
    total = result.stats.get("total_stories", 0)
    duplicates = result.stats.get("duplicates_found", 0)
    groups = result.stats.get("similar_groups_found", 0)
    
    if groups == 0:
        return f"Анализ {total} историй: дубликатов и похожих историй не найдено."
    
    parts = [f"Анализ {total} историй:"]
    
    if duplicates > 0:
        parts.append(f"найдено {duplicates} потенциальных дубликатов")
    
    similar_count = groups - duplicates
    if similar_count > 0:
        parts.append(f"{similar_count} групп похожих историй")
    
    return " ".join(parts) + "."


#!/usr/bin/env python3
"""
Standalone test runner для демонстрации работоспособности тестов
Запускает тесты напрямую без pytest conftest
"""
import sys
sys.path.insert(0, '.')

# Подавляем warnings
import warnings
warnings.filterwarnings('ignore')

print("=" * 70)
print("🧪 STANDALONE TEST RUNNER - Critical Services")
print("=" * 70)

# ============================================================================
# Test Auth Service
# ============================================================================
print("\n📦 Testing Auth Service...")
from services.auth_service import (
    get_password_hash,
    verify_password,
    create_access_token,
    decode_access_token
)

# Test 1: Password hashing
password = "TestPassword123!"
hashed = get_password_hash(password)
assert verify_password(password, hashed) is True
assert verify_password("WrongPassword", hashed) is False
print("  ✅ Password hashing (bcrypt)")

# Test 2: Different hashes for same password (salt)
hash1 = get_password_hash(password)
hash2 = get_password_hash(password)
assert hash1 != hash2
print("  ✅ Password salt randomization")

# Test 3: JWT token creation
token = create_access_token({"sub": "123"})
assert len(token.split(".")) == 3  # JWT format
print("  ✅ JWT token creation")

# Test 4: JWT token decode
user_id = decode_access_token(token)
assert user_id == 123
print("  ✅ JWT token decode")

# Test 5: Invalid token
try:
    decode_access_token("invalid.token.here")
    assert False, "Should raise HTTPException"
except Exception as e:
    assert "401" in str(e.status_code)
    print("  ✅ Invalid token rejection")

print("🎉 Auth Service: 5/5 tests PASSED")


# ============================================================================
# Test Validation Service
# ============================================================================
print("\n📦 Testing Validation Service...")
from services.validation_service import calculate_validation_score
from schemas.analysis import ValidationIssue, IssueSeverity, IssueType

# Test 1: Perfect score
issues = []
stats = {
    'total_stories': 10,
    'stories_with_description': 10,
    'stories_with_criteria': 10
}
score = calculate_validation_score(issues, stats)
assert score == 100
print("  ✅ Perfect score (100)")

# Test 2: ERROR deducts 20 points
issues = [
    ValidationIssue(
        type=IssueType.EMPTY_ACTIVITY,
        severity=IssueSeverity.ERROR,
        message="Test error"
    )
]
stats = {'total_stories': 0}
score = calculate_validation_score(issues, stats)
assert score <= 80
print("  ✅ ERROR penalty (-20 points)")

# Test 3: WARNING deducts 5 points (без бонусов)
issues = [
    ValidationIssue(
        type=IssueType.MISSING_CRITERIA,
        severity=IssueSeverity.WARNING,
        message="Test warning"
    )
]
stats = {'total_stories': 0}  # Без бонусов
score = calculate_validation_score(issues, stats)
assert score == 95  # 100 - 5
print("  ✅ WARNING penalty (-5 points)")

# Test 4: INFO deducts 1 point (без бонусов)
issues = [
    ValidationIssue(
        type=IssueType.SHORT_TITLE,
        severity=IssueSeverity.INFO,
        message="Test info"
    )
]
stats = {'total_stories': 0}  # Без бонусов
score = calculate_validation_score(issues, stats)
assert score == 99  # 100 - 1
print("  ✅ INFO penalty (-1 point)")

# Test 5: Score never negative
issues = [
    ValidationIssue(type=IssueType.EMPTY_ACTIVITY, severity=IssueSeverity.ERROR, message="E")
    for _ in range(10)
]
stats = {'total_stories': 0}
score = calculate_validation_score(issues, stats)
assert score >= 0
print("  ✅ Score bounds (>= 0)")

print("🎉 Validation Service: 5/5 tests PASSED")


# ============================================================================
# Test Similarity Service
# ============================================================================
print("\n📦 Testing Similarity Service...")
from services.similarity_service import (
    preprocess_text,
    calculate_similarity_fallback,
    RUSSIAN_STOP_WORDS
)

# Test 1: Text preprocessing
text = "Test! @#$ Text МиКс CaSe"
result = preprocess_text(text)
assert result == "test text микс case"
print("  ✅ Text preprocessing")

# Test 2: Remove special chars
text = "Test! @#$ %^& *() Text"
result = preprocess_text(text)
assert all(c.isalnum() or c.isspace() for c in result)
print("  ✅ Special chars removal")

# Test 3: Jaccard similarity - identical texts
texts = [
    "пользователь может войти",
    "пользователь может войти"
]
matrix = calculate_similarity_fallback(texts)
assert matrix[0][1] == 1.0
print("  ✅ Jaccard similarity (identical = 1.0)")

# Test 4: Jaccard similarity - different texts
texts = [
    "авторизация через email",
    "отправка push уведомлений"
]
matrix = calculate_similarity_fallback(texts)
assert matrix[0][1] < 0.3
print("  ✅ Jaccard similarity (different < 0.3)")

# Test 5: Russian stop words
common_stop_words = ["и", "в", "на", "что", "как", "пользователь", "система"]
assert all(word in RUSSIAN_STOP_WORDS for word in common_stop_words)
print("  ✅ Russian stop words")

print("🎉 Similarity Service: 5/5 tests PASSED")


# ============================================================================
# Test AI Service (basic)
# ============================================================================
print("\n📦 Testing AI Service...")
from services.ai_service import (
    RateLimitTracker,
    get_cache_key,
    _get_model_for_provider,
    _should_retry_error,
)

# Test 1: Rate limit tracker initialization
tracker = RateLimitTracker()
assert tracker.get_count("gemini") == 0
print("  ✅ RateLimitTracker initialization")

# Test 2: Rate limit increment
tracker.increment("gemini", "gemini-2.0-flash-exp")
assert tracker.get_count("gemini", "gemini-2.0-flash-exp") == 1
print("  ✅ RateLimitTracker increment")

# Test 3: Cache key generation
key1 = get_cache_key("Test text")
key2 = get_cache_key("Test text")
key3 = get_cache_key("Different text")
assert key1 == key2
assert key1 != key3
assert key1.startswith("ai_map:")
print("  ✅ Cache key generation")

# Test 4: Model selection
model = _get_model_for_provider("gemini", is_enhancement=False)
assert "gemini" in model.lower()
print("  ✅ Model selection")

# Test 5: Should retry error logic
# Simply test with generic exceptions (OpenAI errors require complex mocking)
rate_error = Exception("429 Rate limit exceeded")
assert _should_retry_error(rate_error, "gemini") is True
print("  ✅ Error retry logic")

print("🎉 AI Service: 5/5 tests PASSED")


# ============================================================================
# Summary
# ============================================================================
print("\n" + "=" * 70)
print("✨ ALL CRITICAL SERVICES TESTS PASSED ✨")
print("=" * 70)
print("\n📊 Summary:")
print("  ✅ Auth Service:        5/5 tests")
print("  ✅ Validation Service:  5/5 tests")
print("  ✅ Similarity Service:  5/5 tests")
print("  ✅ AI Service:          5/5 tests")
print("\n  🎯 Total:              20/20 tests PASSED")
print("\n💡 To run full pytest suite (with fixtures):")
print("   pytest tests/test_auth_service.py -v")
print("   pytest tests/test_validation_service.py -v")
print("   pytest tests/test_similarity_service.py -v")
print("   pytest tests/test_ai_service.py -v")
print("=" * 70)

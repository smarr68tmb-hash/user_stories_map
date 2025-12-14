"""
Тесты для Auth Service - критично для безопасности!

Покрытие:
1. ✅ JWT token generation/validation
2. ✅ Password hashing (bcrypt)
3. ✅ Refresh token generation/storage
4. ✅ User authentication
5. ✅ Token expiration
6. ✅ Security best practices
"""
import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock, patch
from jose import jwt
from fastapi import HTTPException

from services.auth_service import (
    verify_password,
    get_password_hash,
    create_access_token,
    create_refresh_token,
    authenticate_user,
    decode_access_token,
    get_user_by_email,
)
from models import User, RefreshToken
from config import settings


# ============================================================================
# Test Password Hashing
# ============================================================================

class TestPasswordHashing:
    """Тесты для bcrypt хеширования паролей"""

    def test_password_hashing(self):
        """Хеширование пароля должно создавать уникальный hash"""
        password = "SuperSecretPassword123!"
        hashed = get_password_hash(password)

        # Hash должен быть строкой
        assert isinstance(hashed, str)

        # Hash не должен равняться оригинальному паролю
        assert hashed != password

        # Hash должен начинаться с $2b$ (bcrypt)
        assert hashed.startswith("$2b$")

    def test_same_password_different_hashes(self):
        """Один и тот же пароль должен давать разные hashes (bcrypt salt)"""
        password = "TestPassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Hashes должны быть разными (из-за случайной соли)
        assert hash1 != hash2

    def test_verify_correct_password(self):
        """Проверка правильного пароля должна возвращать True"""
        password = "CorrectPassword123"
        hashed = get_password_hash(password)

        assert verify_password(password, hashed) is True

    def test_verify_incorrect_password(self):
        """Проверка неправильного пароля должна возвращать False"""
        correct_password = "CorrectPassword123"
        wrong_password = "WrongPassword456"
        hashed = get_password_hash(correct_password)

        assert verify_password(wrong_password, hashed) is False

    def test_verify_empty_password(self):
        """Проверка пустого пароля должна возвращать False"""
        password = "TestPassword"
        hashed = get_password_hash(password)

        assert verify_password("", hashed) is False

    def test_hash_long_password(self):
        """Хеширование длинного пароля (72 символа - лимит bcrypt)"""
        # bcrypt имеет лимит 72 байта
        long_password = "a" * 100
        hashed = get_password_hash(long_password)

        # Должно работать (bcrypt обрежет до 72 байт)
        assert isinstance(hashed, str)
        assert verify_password(long_password, hashed) is True


# ============================================================================
# Test JWT Access Token
# ============================================================================

class TestJWTAccessToken:
    """Тесты для JWT access токенов"""

    def test_create_access_token(self):
        """Создание JWT access токена"""
        data = {"sub": "123"}
        token = create_access_token(data)

        # Token должен быть строкой
        assert isinstance(token, str)

        # Token должен содержать 3 части (header.payload.signature)
        assert len(token.split(".")) == 3

    def test_access_token_contains_user_id(self):
        """JWT токен должен содержать user_id в поле 'sub'"""
        user_id = "456"
        token = create_access_token({"sub": user_id})

        # Декодируем токен
        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        assert payload["sub"] == user_id

    def test_access_token_expiration(self):
        """JWT токен должен иметь поле exp (expiration)"""
        token = create_access_token({"sub": "789"})

        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        # Проверяем наличие exp
        assert "exp" in payload

        # exp должен быть в будущем
        exp_timestamp = payload["exp"]
        now_timestamp = datetime.now(timezone.utc).timestamp()
        assert exp_timestamp > now_timestamp

    def test_access_token_custom_expiration(self):
        """JWT токен с кастомным временем истечения"""
        expires_delta = timedelta(minutes=10)
        token = create_access_token({"sub": "100"}, expires_delta=expires_delta)

        payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])

        # Проверяем, что exp примерно через 10 минут
        exp_time = datetime.fromtimestamp(payload["exp"], tz=timezone.utc)
        expected_time = datetime.now(timezone.utc) + expires_delta

        # Разница должна быть меньше 5 секунд
        time_diff = abs((exp_time - expected_time).total_seconds())
        assert time_diff < 5

    def test_decode_access_token_success(self):
        """Декодирование валидного access токена"""
        user_id = 123
        token = create_access_token({"sub": str(user_id)})

        decoded_user_id = decode_access_token(token)

        assert decoded_user_id == user_id

    def test_decode_invalid_token(self):
        """Декодирование невалидного токена должно вызывать HTTPException"""
        invalid_token = "invalid.token.here"

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(invalid_token)

        assert exc_info.value.status_code == 401

    def test_decode_expired_token(self):
        """Декодирование истекшего токена должно вызывать HTTPException"""
        # Создаем токен с истечением в прошлом
        expires_delta = timedelta(seconds=-10)  # -10 секунд (в прошлом)
        token = create_access_token({"sub": "999"}, expires_delta=expires_delta)

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)

        assert exc_info.value.status_code == 401

    def test_decode_token_without_sub(self):
        """Токен без поля 'sub' должен вызывать ошибку"""
        # Создаем токен вручную без 'sub'
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
        data = {"exp": expire}  # Нет 'sub'
        token = jwt.encode(data, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)

        assert exc_info.value.status_code == 401

    def test_decode_token_with_wrong_secret(self):
        """Токен подписанный другим ключом должен быть отклонен"""
        # Создаем токен с другим секретным ключом
        wrong_secret = "wrong_secret_key_12345"
        expire = datetime.now(timezone.utc) + timedelta(minutes=15)
        data = {"sub": "123", "exp": expire}
        token = jwt.encode(data, wrong_secret, algorithm=settings.JWT_ALGORITHM)

        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)

        assert exc_info.value.status_code == 401


# ============================================================================
# Test Refresh Token
# ============================================================================

class TestRefreshToken:
    """Тесты для refresh токенов"""

    def test_create_refresh_token(self):
        """Создание refresh токена и сохранение в БД"""
        mock_db = Mock()
        user_id = 100

        token = create_refresh_token(user_id, mock_db)

        # Token должен быть строкой
        assert isinstance(token, str)

        # Token должен быть достаточно длинным (безопасный random)
        assert len(token) > 40

        # Должен быть вызван db.add с RefreshToken
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    def test_refresh_token_expiration_days(self):
        """Refresh токен должен иметь expiration через settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS"""
        mock_db = Mock()

        # Mock RefreshToken object для проверки
        saved_token = None

        def capture_token(token):
            nonlocal saved_token
            saved_token = token

        mock_db.add.side_effect = capture_token

        create_refresh_token(200, mock_db)

        # Проверяем, что expires_at установлен правильно
        assert saved_token is not None
        assert isinstance(saved_token, RefreshToken)

        # expires_at должен быть через N дней
        expected_expiry = datetime.now(timezone.utc) + timedelta(days=settings.JWT_REFRESH_TOKEN_EXPIRE_DAYS)

        # Разница должна быть меньше 5 секунд
        time_diff = abs((saved_token.expires_at - expected_expiry).total_seconds())
        assert time_diff < 5

    def test_refresh_token_uniqueness(self):
        """Каждый refresh токен должен быть уникальным"""
        mock_db = Mock()

        token1 = create_refresh_token(300, mock_db)
        token2 = create_refresh_token(300, mock_db)

        assert token1 != token2


# ============================================================================
# Test User Authentication
# ============================================================================

class TestUserAuthentication:
    """Тесты для аутентификации пользователей"""

    def test_get_user_by_email_exists(self):
        """Поиск существующего пользователя по email"""
        mock_db = Mock()
        mock_query = Mock()
        mock_filter = Mock()

        mock_user = User(
            id=1,
            email="test@example.com",
            full_name="Test User",
            hashed_password="hashed"
        )

        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = mock_user

        user = get_user_by_email(mock_db, "test@example.com")

        assert user is not None
        assert user.email == "test@example.com"
        assert user.id == 1

    def test_get_user_by_email_not_exists(self):
        """Поиск несуществующего пользователя должен вернуть None"""
        mock_db = Mock()
        mock_query = Mock()
        mock_filter = Mock()

        mock_db.query.return_value = mock_query
        mock_query.filter.return_value = mock_filter
        mock_filter.first.return_value = None

        user = get_user_by_email(mock_db, "nonexistent@example.com")

        assert user is None

    def test_authenticate_user_success(self):
        """Успешная аутентификация с правильным паролем"""
        mock_db = Mock()

        password = "CorrectPassword123"
        hashed_password = get_password_hash(password)

        mock_user = User(
            id=1,
            email="user@example.com",
            full_name="Test User",
            hashed_password=hashed_password
        )

        with patch('services.auth_service.get_user_by_email', return_value=mock_user):
            user = authenticate_user(mock_db, "user@example.com", password)

            assert user is not None
            assert user.email == "user@example.com"

    def test_authenticate_user_wrong_password(self):
        """Аутентификация с неправильным паролем должна вернуть None"""
        mock_db = Mock()

        correct_password = "CorrectPassword123"
        wrong_password = "WrongPassword456"
        hashed_password = get_password_hash(correct_password)

        mock_user = User(
            id=1,
            email="user@example.com",
            full_name="Test User",
            hashed_password=hashed_password
        )

        with patch('services.auth_service.get_user_by_email', return_value=mock_user):
            user = authenticate_user(mock_db, "user@example.com", wrong_password)

            assert user is None

    def test_authenticate_user_not_exists(self):
        """Аутентификация несуществующего пользователя должна вернуть None"""
        mock_db = Mock()

        with patch('services.auth_service.get_user_by_email', return_value=None):
            user = authenticate_user(mock_db, "nonexistent@example.com", "password")

            assert user is None

    def test_authenticate_user_empty_password(self):
        """Аутентификация с пустым паролем должна вернуть None"""
        mock_db = Mock()

        hashed_password = get_password_hash("SomePassword")
        mock_user = User(
            id=1,
            email="user@example.com",
            hashed_password=hashed_password
        )

        with patch('services.auth_service.get_user_by_email', return_value=mock_user):
            user = authenticate_user(mock_db, "user@example.com", "")

            assert user is None


# ============================================================================
# Test Security Best Practices
# ============================================================================

class TestSecurityBestPractices:
    """Тесты для проверки security best practices"""

    def test_password_hash_not_reversible(self):
        """Hash пароля не должен быть обратимым"""
        password = "SecretPassword123"
        hashed = get_password_hash(password)

        # Hash не должен содержать оригинальный пароль
        assert password not in hashed

        # Попытка "reverse" должна провалиться
        # (bcrypt необратим - это good practice)
        # Проверяем, что у bcrypt нет метода decrypt/decode - это one-way hash
        pwd_context = __import__('passlib.context', fromlist=['CryptContext']).CryptContext
        ctx = pwd_context(schemes=["bcrypt"])
        assert not hasattr(ctx, 'decrypt')
        assert not hasattr(ctx, 'decode')

        # Попытка использовать несуществующий метод должна вызвать ошибку
        with pytest.raises(AttributeError):
            ctx.decrypt(hashed)

    def test_jwt_secret_used(self):
        """JWT токены должны использовать SECRET_KEY из настроек"""
        token = create_access_token({"sub": "123"})

        # Попытка декодировать с другим ключом должна провалиться
        with pytest.raises(Exception):
            jwt.decode(token, "wrong_secret", algorithms=[settings.JWT_ALGORITHM])

    def test_jwt_algorithm_secure(self):
        """JWT должен использовать безопасный алгоритм (HS256)"""
        token = create_access_token({"sub": "123"})

        # Проверяем, что используется HS256
        header = jwt.get_unverified_header(token)
        assert header["alg"] == "HS256"

    def test_token_expiration_enforced(self):
        """Истекшие токены должны быть отклонены"""
        # Создаем токен с истечением в прошлом
        past_delta = timedelta(seconds=-100)
        token = create_access_token({"sub": "999"}, expires_delta=past_delta)

        # Попытка декодировать должна вызвать ошибку
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)

        assert exc_info.value.status_code == 401

    def test_password_complexity_accepted(self):
        """Сложные пароли должны корректно хешироваться"""
        complex_passwords = [
            "P@ssw0rd!123",
            "MyC0mpl3x#Pass",
            "Sup3r$ecur3&Str0ng",
            "🔒Emoji🔑Allowed🔐",
            "Русский_Пароль123!"
        ]

        for password in complex_passwords:
            hashed = get_password_hash(password)
            assert verify_password(password, hashed) is True

    def test_timing_attack_resistance(self):
        """Verify password должен быть устойчив к timing attacks (bcrypt)"""
        # bcrypt автоматически защищает от timing attacks
        # через constant-time comparison

        password = "TestPassword"
        hashed = get_password_hash(password)

        # Оба вызова должны занимать примерно одинаковое время
        # (bcrypt делает это автоматически)
        import time

        # Правильный пароль
        start = time.time()
        verify_password(password, hashed)
        time1 = time.time() - start

        # Неправильный пароль
        start = time.time()
        verify_password("WrongPassword", hashed)
        time2 = time.time() - start

        # Разница должна быть минимальной (bcrypt делает constant-time)
        # Допускаем разницу до 10ms (на практике будет меньше)
        time_diff = abs(time1 - time2)
        assert time_diff < 0.01  # 10ms


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Тесты для граничных случаев"""

    def test_token_with_special_characters_in_user_id(self):
        """JWT с user_id содержащим специальные символы"""
        # user_id обычно int, но тестируем edge case
        user_id_str = "user_123_test"
        token = create_access_token({"sub": user_id_str})

        # Попытка декодировать как int должна вызвать ошибку
        with pytest.raises(HTTPException):
            decode_access_token(token)

    def test_very_long_email(self):
        """Очень длинный email"""
        mock_db = Mock()
        mock_db.query.return_value.filter.return_value.first.return_value = None
        long_email = "a" * 200 + "@example.com"

        # Должно работать без ошибок (функция не должна падать)
        user = get_user_by_email(mock_db, long_email)
        assert user is None

    def test_unicode_in_password(self):
        """Unicode символы в пароле"""
        unicode_password = "Пароль_Тест_🔐_2024"
        hashed = get_password_hash(unicode_password)

        assert verify_password(unicode_password, hashed) is True

    def test_empty_email_authentication(self):
        """Аутентификация с пустым email"""
        mock_db = Mock()

        with patch('services.auth_service.get_user_by_email', return_value=None):
            user = authenticate_user(mock_db, "", "password")
            assert user is None

    def test_whitespace_in_password(self):
        """Пароль с пробелами и табуляцией"""
        password_with_spaces = "  Test Password\t123  "
        hashed = get_password_hash(password_with_spaces)

        # Пробелы должны сохраняться
        assert verify_password(password_with_spaces, hashed) is True
        assert verify_password("Test Password\t123", hashed) is False

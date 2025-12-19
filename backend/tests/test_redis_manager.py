"""
Тесты для RedisManager - централизованная работа с Redis

Покрытие:
1. ✅ Получение Redis клиента
2. ✅ Проверка доступности Redis
3. ✅ Кеширование соединения
4. ✅ Сброс клиента
5. ✅ Обработка недоступного Redis
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from utils import RedisManager
from config import settings


# ============================================================================
# Test Redis Client Management
# ============================================================================

class TestRedisClientManagement:
    """Тесты для управления Redis клиентом"""
    
    def test_get_client_success(self):
        """Проверка успешного получения клиента"""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        
        with patch('utils.redis_manager.redis') as mock_redis_module:
            with patch('utils.redis_manager.settings') as mock_settings:
                mock_settings.REDIS_URL = "redis://localhost:6379"
                mock_settings.ENVIRONMENT = "development"
                mock_redis_module.from_url.return_value = mock_redis
                
                client = RedisManager.get_client()
                
                assert client is not None
                assert client == mock_redis
                mock_redis.ping.assert_called_once()
    
    def test_get_client_cached(self):
        """Проверка кеширования клиента"""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        
        with patch('utils.redis_manager.redis') as mock_redis_module:
            with patch('utils.redis_manager.settings') as mock_settings:
                mock_settings.REDIS_URL = "redis://localhost:6379"
                mock_settings.ENVIRONMENT = "development"
                mock_redis_module.from_url.return_value = mock_redis
                
                # Первый вызов
                client1 = RedisManager.get_client()
                
                # Второй вызов - должен вернуть кешированный клиент
                client2 = RedisManager.get_client()
                
                assert client1 == client2
                # from_url должен быть вызван только один раз
                assert mock_redis_module.from_url.call_count == 1
    
    def test_get_client_no_redis_url(self):
        """Проверка поведения при отсутствии REDIS_URL"""
        with patch('utils.redis_manager.settings') as mock_settings:
            mock_settings.REDIS_URL = None
            mock_settings.ENVIRONMENT = "development"
            
            # Сбрасываем кеш
            RedisManager.reset_client()
            
            client = RedisManager.get_client()
            
            assert client is None
    
    def test_get_client_connection_error(self):
        """Проверка обработки ошибки соединения"""
        mock_redis = MagicMock()
        mock_redis.ping.side_effect = Exception("Connection failed")
        
        with patch('utils.redis_manager.redis') as mock_redis_module:
            with patch('utils.redis_manager.settings') as mock_settings:
                mock_settings.REDIS_URL = "redis://localhost:6379"
                mock_settings.ENVIRONMENT = "development"
                mock_redis_module.from_url.return_value = mock_redis
                
                # Сбрасываем кеш
                RedisManager.reset_client()
                
                client = RedisManager.get_client()
                
                assert client is None
    
    def test_get_client_import_error(self):
        """Проверка обработки ошибки импорта redis"""
        with patch('utils.redis_manager.redis', side_effect=ImportError("No module named 'redis'")):
            with patch('utils.redis_manager.settings') as mock_settings:
                mock_settings.REDIS_URL = "redis://localhost:6379"
                mock_settings.ENVIRONMENT = "development"
                
                # Сбрасываем кеш
                RedisManager.reset_client()
                
                client = RedisManager.get_client()
                
                assert client is None
    
    def test_is_available_true(self):
        """Проверка доступности Redis (True)"""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        
        with patch('utils.redis_manager.redis') as mock_redis_module:
            with patch('utils.redis_manager.settings') as mock_settings:
                mock_settings.REDIS_URL = "redis://localhost:6379"
                mock_settings.ENVIRONMENT = "development"
                mock_redis_module.from_url.return_value = mock_redis
                
                # Сбрасываем кеш
                RedisManager.reset_client()
                
                is_available = RedisManager.is_available()
                
                assert is_available is True
    
    def test_is_available_false(self):
        """Проверка доступности Redis (False)"""
        with patch('utils.redis_manager.settings') as mock_settings:
            mock_settings.REDIS_URL = None
            
            # Сбрасываем кеш
            RedisManager.reset_client()
            
            is_available = RedisManager.is_available()
            
            assert is_available is False
    
    def test_reset_client(self):
        """Проверка сброса клиента"""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        
        with patch('utils.redis_manager.redis') as mock_redis_module:
            with patch('utils.redis_manager.settings') as mock_settings:
                mock_settings.REDIS_URL = "redis://localhost:6379"
                mock_settings.ENVIRONMENT = "development"
                mock_redis_module.from_url.return_value = mock_redis
                
                # Получаем клиент
                client1 = RedisManager.get_client()
                
                # Сбрасываем
                RedisManager.reset_client()
                
                # Получаем снова - должен быть новый вызов from_url
                client2 = RedisManager.get_client()
                
                # Клиенты должны быть одинаковыми (один и тот же mock)
                # но from_url должен быть вызван дважды
                assert mock_redis_module.from_url.call_count == 2
    
    def test_get_client_production_logging(self):
        """Проверка логирования в production режиме"""
        mock_redis = MagicMock()
        mock_redis.ping.return_value = True
        
        with patch('utils.redis_manager.redis') as mock_redis_module:
            with patch('utils.redis_manager.settings') as mock_settings:
                with patch('utils.redis_manager.logger') as mock_logger:
                    mock_settings.REDIS_URL = "redis://localhost:6379"
                    mock_settings.ENVIRONMENT = "production"
                    mock_redis_module.from_url.return_value = mock_redis
                    
                    # Сбрасываем кеш
                    RedisManager.reset_client()
                    
                    RedisManager.get_client()
                    
                    # Проверяем, что был вызван logger.info
                    mock_logger.info.assert_called()
                    assert "Redis connection established" in str(mock_logger.info.call_args)


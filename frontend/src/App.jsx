import { useState, useEffect } from 'react';
import api, { auth } from './api';
import StoryMap from './StoryMap.jsx';
import Auth from './Auth.jsx';

const MAX_CHARS = 10000;
const MIN_CHARS = 10;

function App() {
  const [token, setToken] = useState(() => localStorage.getItem('auth_token'));
  const [user, setUser] = useState(null);
  
  // Загружаем сохраненный черновик из localStorage
  const [input, setInput] = useState(() => {
    return localStorage.getItem('draft_requirements') || '';
  });
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [project, setProject] = useState(null);
  const [error, setError] = useState(null);
  
  // Проверка токена при загрузке
  useEffect(() => {
    if (token) {
      // Проверяем валидность токена
      auth.getMe()
        .then(res => setUser(res.data))
        .catch(() => {
          // Если не удалось получить пользователя - разлогиниваем
          // Интерцептор уже обработал обновление токена, если это было возможно
          // Если мы здесь, значит токен невалиден
          auth.logout();
          setToken(null);
          setUser(null);
          setProject(null);
          setInput('');
        });
    }
  }, [token]);
  
  // Автосохранение черновика
  useEffect(() => {
    const timeout = setTimeout(() => {
      if (input.trim()) {
        localStorage.setItem('draft_requirements', input);
      }
    }, 1000);
    return () => clearTimeout(timeout);
  }, [input]);
  
  // Симуляция прогресса при загрузке
  useEffect(() => {
    if (loading) {
      setProgress(10);
      const interval = setInterval(() => {
        setProgress(prev => {
          if (prev >= 90) return prev;
          return prev + Math.random() * 15;
        });
      }, 2000);
      return () => clearInterval(interval);
    } else {
      setProgress(0);
    }
  }, [loading]);
  
  // Валидация размера текста
  const isValidInput = input.trim().length >= MIN_CHARS && input.length <= MAX_CHARS;
  const charCount = input.length;
  const remainingChars = MAX_CHARS - charCount;

  const handleLogin = async (loginData) => {
    // loginData теперь приходит из Auth компонента, который использует api.js
    // Токены уже сохранены в localStorage
    setToken(localStorage.getItem('auth_token'));
    
    // Загружаем информацию о пользователе
    try {
      const res = await auth.getMe();
      setUser(res.data);
    } catch (e) {
      console.error("Failed to fetch user data:", e);
    }
  };

  const handleLogout = async () => {
    await auth.logout();
    setToken(null);
    setUser(null);
    setProject(null);
    setInput('');
  };

  // 1. Отправка требований
  const handleGenerate = async () => {
    if (!input.trim()) {
      setError('Пожалуйста, введите описание продукта');
      return;
    }
    
    if (!isValidInput) {
      if (input.trim().length < MIN_CHARS) {
        setError(`Текст слишком короткий. Минимум ${MIN_CHARS} символов.`);
      } else {
        setError(`Текст слишком длинный. Максимум ${MAX_CHARS} символов.`);
      }
      return;
    }
    
    setLoading(true);
    setError(null);
    setProgress(10);
    
    try {
      // Генерируем карту
      const res = await api.post('/generate-map', { text: input });
      setProgress(70);
      const projectId = res.data.project_id;
      
      // Забираем полные данные
      const projectRes = await api.get(`/project/${projectId}`);
      setProgress(100);
      setProject(projectRes.data);
      
      // Очищаем сохраненный черновик после успешной генерации
      localStorage.removeItem('draft_requirements');
    } catch (error) {
      console.error("Error generating map:", error);
      setProgress(0);
      // Ошибки 401 теперь обрабатываются интерцептором, но можно оставить проверку для UI
      if (error.response?.status === 401) {
        setError('Сессия истекла. Пожалуйста, войдите снова.');
        handleLogout();
      } else if (error.response) {
        const detail = error.response.data?.detail || 'Неизвестная ошибка';
        setError(`Ошибка: ${detail}`);
      } else if (error.request) {
        setError('Не удалось подключиться к серверу. Убедитесь, что backend запущен на порту 8000');
      } else {
        setError(`Ошибка: ${error.message}`);
      }
    } finally {
      setLoading(false);
      // Сбрасываем прогресс через небольшую задержку
      setTimeout(() => setProgress(0), 500);
    }
  };

  // Если не авторизован, показываем форму входа
  if (!token || !user) {
    return <Auth onLogin={handleLogin} />;
  }

  if (!project) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="bg-white p-8 rounded-xl shadow-lg max-w-2xl w-full">
          <h1 className="text-3xl font-bold mb-2 text-gray-800">AI User Story Mapper</h1>
          <p className="text-gray-600 mb-6">Превратите ваши требования в структурированную карту пользовательских историй</p>
          
          <div className="mb-2">
            <textarea
              className={`w-full h-40 p-4 border rounded-lg mb-2 focus:ring-2 focus:ring-blue-500 outline-none resize-none ${
                !isValidInput && input.length > 0
                  ? 'border-red-300 bg-red-50'
                  : 'border-gray-300'
              }`}
              placeholder="Опишите ваш продукт (например: Приложение для доставки пиццы с ролями курьера и клиента. Клиент может выбрать пиццу, оформить заказ и отслеживать доставку. Курьер получает заказы, видит маршрут и отмечает доставку...)"
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                setError(null);
              }}
              disabled={loading}
              maxLength={MAX_CHARS}
              aria-label="Описание продукта"
            />
            <div className="flex justify-between items-center text-xs">
              <span className={`${charCount < MIN_CHARS ? 'text-gray-400' : 'text-gray-600'}`}>
                {charCount < MIN_CHARS 
                  ? `Минимум ${MIN_CHARS} символов (осталось ${MIN_CHARS - charCount})`
                  : `${charCount} / ${MAX_CHARS} символов`
                }
              </span>
              {remainingChars < 100 && (
                <span className={remainingChars < 20 ? 'text-red-500 font-semibold' : 'text-orange-500'}>
                  Осталось: {remainingChars}
                </span>
              )}
            </div>
          </div>
          
          {/* Прогресс-бар */}
          {loading && (
            <div className="mb-4">
              <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
                <div 
                  className="bg-blue-600 h-2.5 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                  role="progressbar"
                  aria-valuenow={progress}
                  aria-valuemin="0"
                  aria-valuemax="100"
                ></div>
              </div>
              <p className="text-xs text-gray-600 text-center">
                AI анализирует требования... {Math.round(progress)}%
              </p>
            </div>
          )}
          
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm" role="alert">
              {error}
            </div>
          )}
          
          <button
            onClick={handleGenerate}
            disabled={loading || !isValidInput || !input.trim()}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed"
            aria-label="Сгенерировать карту пользовательских историй"
          >
            {loading ? "Генерация карты..." : "Сгенерировать карту"}
          </button>
          
          <p className="mt-4 text-xs text-gray-500 text-center">
            Для работы требуется OpenAI API ключ. Установите переменную окружения OPENAI_API_KEY
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-4 md:p-8 overflow-x-auto bg-gray-50">
      <div className="mb-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">{project.name}</h1>
          <p className="text-sm text-gray-600 mt-1">User Story Map</p>
          {user && (
            <p className="text-xs text-gray-500 mt-1">
              Пользователь: {user.email} {user.full_name && `(${user.full_name})`}
            </p>
          )}
        </div>
        <div className="flex gap-3">
          <button 
            onClick={() => {
              setProject(null);
              setInput('');
              setError(null);
              setProgress(0);
              localStorage.removeItem('draft_requirements');
            }} 
            className="text-blue-600 hover:underline font-medium"
            aria-label="Создать новую карту"
          >
            ← Создать новую карту
          </button>
          <button
            onClick={handleLogout}
            className="text-gray-600 hover:text-gray-800 font-medium"
          >
            Выйти
          </button>
        </div>
      </div>
      
      {/* Компонент Карты */}
      <StoryMap project={project} onUpdate={setProject} onUnauthorized={handleLogout} />
    </div>
  );
}

export default App;


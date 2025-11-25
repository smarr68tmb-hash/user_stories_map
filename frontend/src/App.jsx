import { useState, useEffect } from 'react';
import api, { auth } from './api';
import StoryMap from './StoryMap.jsx';
import Auth from './Auth.jsx';
import ProjectList from './ProjectList.jsx';

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
  const [view, setView] = useState('list'); // 'list' или 'create'
  
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
    setView('list');
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

  const handleSelectProject = (projectData) => {
    setProject(projectData);
  };

  const handleCreateNew = () => {
    setView('create');
    setProject(null);
    setInput('');
    setError(null);
  };

  const handleBackToList = () => {
    setView('list');
    setProject(null);
    setInput('');
    setError(null);
    localStorage.removeItem('draft_requirements');
  };

  // Если не авторизован, показываем форму входа
  if (!token || !user) {
    return <Auth onLogin={handleLogin} />;
  }

  // Если есть выбранный проект, показываем карту
  if (project) {
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
              onClick={handleBackToList}
              className="text-blue-600 hover:underline font-medium"
              aria-label="Вернуться к списку проектов"
            >
              ← К списку проектов
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

  // Если нет проекта и view === 'list', показываем список проектов
  if (view === 'list') {
    return (
      <ProjectList
        onSelectProject={handleSelectProject}
        onCreateNew={handleCreateNew}
        onLogout={handleLogout}
        user={user}
      />
    );
  }

  // Если view === 'create', показываем форму создания нового проекта
  if (view === 'create') {
    return (
      <div className="min-h-screen flex items-center justify-center p-4 bg-gray-50">
        <div className="bg-white p-8 rounded-xl shadow-lg max-w-2xl w-full">
          <div className="flex justify-between items-start mb-4">
            <div>
              <h1 className="text-3xl font-bold mb-2 text-gray-800">Создать новый проект</h1>
              <p className="text-gray-600">Превратите ваши требования в структурированную карту пользовательских историй</p>
            </div>
            <button
              onClick={handleBackToList}
              className="text-gray-500 hover:text-gray-700 text-sm font-medium"
            >
              ✕
            </button>
          </div>
          
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
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed mb-3"
            aria-label="Сгенерировать карту пользовательских историй"
          >
            {loading ? "Генерация карты..." : "Сгенерировать карту"}
          </button>
          
          <button
            onClick={handleBackToList}
            className="w-full text-gray-600 hover:text-gray-800 py-2 rounded-lg font-medium border border-gray-300 hover:border-gray-400 transition"
          >
            ← Назад к списку проектов
          </button>
          
          <p className="mt-4 text-xs text-gray-500 text-center">
            Для работы требуется OpenAI API ключ. Установите переменную окружения OPENAI_API_KEY
          </p>
        </div>
      </div>
    );
  }

  // По умолчанию возвращаемся к списку (не должно быть достигнуто)
  return null;
}

export default App;


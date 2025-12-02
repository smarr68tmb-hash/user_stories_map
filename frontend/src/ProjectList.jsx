import { useState, useEffect } from 'react';
import api, { projects as projectsApi } from './api';

function ProjectList({ onSelectProject, onCreateNew, onLogout, user }) {
  const [projects, setProjects] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [sortBy, setSortBy] = useState('newest'); // newest, oldest, name
  const [projectToDelete, setProjectToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [showSettings, setShowSettings] = useState(false);
  const [rememberCredentials, setRememberCredentials] = useState(false);

  useEffect(() => {
    loadProjects();
  }, []);

  useEffect(() => {
    const remember = localStorage.getItem('remember_credentials') === 'true';
    setRememberCredentials(remember);
  }, []);

  const loadProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.get('/projects', {
        params: {
          skip: 0,
          limit: 100
        }
      });
      setProjects(response.data.items);
    } catch (err) {
      console.error('Error loading projects:', err);
      if (err.response?.status === 401) {
        setError('Сессия истекла. Пожалуйста, войдите снова.');
        onLogout();
      } else {
        setError('Не удалось загрузить проекты');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleProjectClick = async (projectId) => {
    try {
      const response = await api.get(`/project/${projectId}`);
      onSelectProject(response.data);
    } catch (err) {
      console.error('Error loading project:', err);
      if (err.response?.status === 401) {
        alert('Сессия истекла. Пожалуйста, войдите снова.');
        onLogout();
      } else if (err.response?.status === 404) {
        alert('Проект не найден');
        loadProjects(); // Обновляем список
      } else {
        alert('Не удалось загрузить проект');
      }
    }
  };

  // Фильтрация проектов по поисковому запросу
  const filteredProjects = projects.filter(project =>
    project.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Сортировка проектов
  const sortedProjects = [...filteredProjects].sort((a, b) => {
    switch (sortBy) {
      case 'newest':
        return new Date(b.created_at) - new Date(a.created_at);
      case 'oldest':
        return new Date(a.created_at) - new Date(b.created_at);
      case 'name':
        return a.name.localeCompare(b.name);
      default:
        return 0;
    }
  });

  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const now = new Date();
    const diffMs = now - date;
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 60) {
      return `${diffMins} мин назад`;
    } else if (diffHours < 24) {
      return `${diffHours} ч назад`;
    } else if (diffDays < 7) {
      return `${diffDays} дн назад`;
    } else {
      return date.toLocaleDateString('ru-RU', {
        day: 'numeric',
        month: 'short',
        year: date.getFullYear() !== now.getFullYear() ? 'numeric' : undefined
      });
    }
  };

  const handleDeleteClick = (e, project) => {
    e.stopPropagation(); // Предотвращаем открытие проекта при клике на кнопку удаления
    setProjectToDelete(project);
  };

  const handleCancelDelete = () => {
    setProjectToDelete(null);
  };

  const handleConfirmDelete = async () => {
    if (!projectToDelete) return;

    setDeleting(true);
    try {
      await projectsApi.delete(projectToDelete.id);
      // Удаляем проект из списка
      setProjects(projects.filter(p => p.id !== projectToDelete.id));
      setProjectToDelete(null);
    } catch (err) {
      console.error('Error deleting project:', err);
      if (err.response?.status === 401) {
        alert('Сессия истекла. Пожалуйста, войдите снова.');
        onLogout();
      } else if (err.response?.status === 404) {
        alert('Проект не найден');
        // Обновляем список, так как проект уже может быть удален
        loadProjects();
      } else {
        alert('Не удалось удалить проект');
      }
    } finally {
      setDeleting(false);
    }
  };

  const handleToggleRememberCredentials = (value) => {
    setRememberCredentials(value);
    if (value) {
      localStorage.setItem('remember_credentials', 'true');
    } else {
      localStorage.removeItem('remember_credentials');
      localStorage.removeItem('remembered_login');
       localStorage.removeItem('remembered_password');
    }
  };

  const handleClearSavedCredentials = () => {
    localStorage.removeItem('remembered_login');
    localStorage.removeItem('remembered_password');
    localStorage.removeItem('remember_credentials');
    setRememberCredentials(false);
  };

  return (
    <div className="min-h-screen bg-gray-50 p-4 md:p-8">
      <div className="max-w-6xl mx-auto">
        {/* Header */}
        <div className="bg-white rounded-lg shadow-sm p-6 mb-6">
          <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-800">Мои проекты</h1>
              <p className="text-sm text-gray-600 mt-1">
                {user && `${user.email} ${user.full_name ? `(${user.full_name})` : ''}`}
              </p>
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowSettings(true)}
                className="text-gray-600 hover:text-gray-800 font-medium px-4 py-2 rounded-lg border border-gray-300 hover:border-gray-400 transition"
              >
                Настройки
              </button>
              <button
                onClick={onCreateNew}
                className="bg-blue-600 text-white px-6 py-2 rounded-lg font-semibold hover:bg-blue-700 transition shadow-sm"
              >
                + Создать новый проект
              </button>
              <button
                onClick={onLogout}
                className="text-gray-600 hover:text-gray-800 font-medium px-4 py-2 rounded-lg border border-gray-300 hover:border-gray-400 transition"
              >
                Выйти
              </button>
            </div>
          </div>

          {/* Search and Filter */}
          <div className="flex flex-col md:flex-row gap-4 mt-6">
            <div className="flex-1">
              <input
                type="text"
                placeholder="🔍 Поиск проектов по названию..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none"
              />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-sm text-gray-600 font-medium">Сортировка:</span>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 outline-none bg-white"
              >
                <option value="newest">Сначала новые</option>
                <option value="oldest">Сначала старые</option>
                <option value="name">По названию</option>
              </select>
            </div>
          </div>
        </div>

        {/* Loading State */}
        {loading && (
          <div className="text-center py-12">
            <div className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
            <p className="text-gray-600 mt-4">Загрузка проектов...</p>
          </div>
        )}

        {/* Error State */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-700">
            {error}
          </div>
        )}

        {/* Empty State */}
        {!loading && !error && sortedProjects.length === 0 && !searchQuery && (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <svg
              className="mx-auto h-24 w-24 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={1.5}
                d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"
              />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-gray-900">Нет проектов</h3>
            <p className="mt-2 text-gray-600">Начните с создания вашего первого проекта</p>
            <button
              onClick={onCreateNew}
              className="mt-6 bg-blue-600 text-white px-6 py-3 rounded-lg font-semibold hover:bg-blue-700 transition"
            >
              Создать первый проект
            </button>
          </div>
        )}

        {/* No Search Results */}
        {!loading && !error && sortedProjects.length === 0 && searchQuery && (
          <div className="bg-white rounded-lg shadow-sm p-12 text-center">
            <svg
              className="mx-auto h-16 w-16 text-gray-400"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"
              />
            </svg>
            <h3 className="mt-4 text-lg font-medium text-gray-900">Ничего не найдено</h3>
            <p className="mt-2 text-gray-600">
              По запросу "{searchQuery}" проекты не найдены
            </p>
            <button
              onClick={() => setSearchQuery('')}
              className="mt-4 text-blue-600 hover:underline"
            >
              Очистить поиск
            </button>
          </div>
        )}

        {/* Projects Grid */}
        {!loading && !error && sortedProjects.length > 0 && (
          <>
            <div className="mb-4 text-sm text-gray-600">
              Найдено проектов: {sortedProjects.length}
              {searchQuery && ` по запросу "${searchQuery}"`}
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
              {sortedProjects.map((project) => (
                <div
                  key={project.id}
                  onClick={() => handleProjectClick(project.id)}
                  className="bg-white rounded-lg shadow-sm hover:shadow-lg transition-all cursor-pointer border border-gray-200 hover:border-blue-400 overflow-hidden group relative"
                >
                  <div className="p-6">
                    <div className="flex items-start justify-between mb-3">
                      <h3 className="text-lg font-semibold text-gray-800 group-hover:text-blue-600 transition line-clamp-2 flex-1">
                        {project.name}
                      </h3>
                      <div className="flex items-center gap-2 flex-shrink-0 ml-2">
                        <button
                          onClick={(e) => handleDeleteClick(e, project)}
                          className="p-1 text-gray-400 hover:text-red-600 transition rounded hover:bg-red-50"
                          title="Удалить проект"
                        >
                          <svg
                            className="h-5 w-5"
                            fill="none"
                            viewBox="0 0 24 24"
                            stroke="currentColor"
                          >
                            <path
                              strokeLinecap="round"
                              strokeLinejoin="round"
                              strokeWidth={2}
                              d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"
                            />
                          </svg>
                        </button>
                        <svg
                          className="h-5 w-5 text-gray-400 group-hover:text-blue-600 transition"
                          fill="none"
                          viewBox="0 0 24 24"
                          stroke="currentColor"
                        >
                          <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            strokeWidth={2}
                            d="M9 5l7 7-7 7"
                          />
                        </svg>
                      </div>
                    </div>
                    
                    <div className="flex items-center text-xs text-gray-500">
                      <svg
                        className="h-4 w-4 mr-1"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                      >
                        <path
                          strokeLinecap="round"
                          strokeLinejoin="round"
                          strokeWidth={2}
                          d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"
                        />
                      </svg>
                      {formatDate(project.created_at)}
                    </div>
                  </div>
                  
                  <div className="bg-gradient-to-r from-blue-50 to-indigo-50 px-6 py-3 border-t border-gray-100">
                    <span className="text-xs font-medium text-blue-700">
                      Открыть проект →
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </>
        )}

        {/* Delete Confirmation Modal */}
        {projectToDelete && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <div className="flex items-center mb-4">
                <div className="flex-shrink-0 w-12 h-12 bg-red-100 rounded-full flex items-center justify-center mr-4">
                  <svg
                    className="h-6 w-6 text-red-600"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
                    />
                  </svg>
                </div>
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    Удалить проект?
                  </h3>
                </div>
              </div>
              
              <p className="text-gray-600 mb-6">
                Вы уверены, что хотите удалить проект <strong>"{projectToDelete.name}"</strong>?
                Это действие нельзя отменить. Все задачи и история проекта будут удалены.
              </p>
              
              <div className="flex gap-3 justify-end">
                <button
                  onClick={handleCancelDelete}
                  disabled={deleting}
                  className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Отмена
                </button>
                <button
                  onClick={handleConfirmDelete}
                  disabled={deleting}
                  className="px-4 py-2 text-white bg-red-600 rounded-lg hover:bg-red-700 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
                >
                  {deleting && (
                    <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                  )}
                  {deleting ? 'Удаление...' : 'Удалить'}
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Settings Modal */}
        {showSettings && (
          <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
            <div className="bg-white rounded-lg shadow-xl max-w-md w-full p-6">
              <div className="flex justify-between items-start mb-4">
                <div>
                  <h3 className="text-lg font-semibold text-gray-900">
                    Настройки аккаунта
                  </h3>
                  <p className="text-sm text-gray-600">
                    Управление сохранением логина и пароля на этом устройстве
                  </p>
                </div>
                <button
                  onClick={() => setShowSettings(false)}
                  className="text-gray-400 hover:text-gray-600"
                  aria-label="Закрыть настройки"
                >
                  ✕
                </button>
              </div>

              <div className="space-y-4">
                <div className="flex items-start gap-3">
                  <input
                    id="remember-credentials"
                    type="checkbox"
                    checked={rememberCredentials}
                    onChange={(e) => handleToggleRememberCredentials(e.target.checked)}
                    className="mt-1 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <label
                    htmlFor="remember-credentials"
                    className="text-sm text-gray-800 cursor-pointer"
                  >
                    <span className="font-medium block">
                      Запоминать логин и пароль на этом устройстве
                    </span>
                    <span className="text-gray-600">
                      При включении логин и пароль будут предзаполняться при следующем входе
                      в этом браузере.
                    </span>
                  </label>
                </div>

                <div className="border-t border-gray-200 pt-4 mt-2">
                  <p className="text-sm text-gray-700 mb-2 font-medium">
                    Управление сохранёнными данными
                  </p>
                  <p className="text-xs text-gray-500 mb-3">
                    Вы можете в любой момент удалить сохранённые логин и пароль с этого устройства.
                    Это не повлияет на ваш аккаунт или сессию на сервере.
                  </p>
                  <button
                    onClick={handleClearSavedCredentials}
                    className="px-4 py-2 text-sm text-red-600 border border-red-200 rounded-lg hover:bg-red-50 transition font-medium"
                  >
                    Удалить сохранённые логин и пароль
                  </button>
                </div>
              </div>

              <div className="mt-6 flex justify-end">
                <button
                  onClick={() => setShowSettings(false)}
                  className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition font-medium"
                >
                  Закрыть
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default ProjectList;


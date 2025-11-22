import { useState } from 'react';
import axios from 'axios';

// URL твоего бэкенда
const API_URL = "http://127.0.0.1:8000";

function App() {
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [project, setProject] = useState(null);
  const [error, setError] = useState(null);

  // 1. Отправка требований
  const handleGenerate = async () => {
    if (!input.trim()) {
      setError('Пожалуйста, введите описание продукта');
      return;
    }
    
    setLoading(true);
    setError(null);
    
    try {
      // Генерируем карту
      const res = await axios.post(`${API_URL}/generate-map`, { text: input });
      const projectId = res.data.project_id;
      
      // Забираем полные данные
      const projectRes = await axios.get(`${API_URL}/project/${projectId}`);
      setProject(projectRes.data);
    } catch (error) {
      console.error("Error generating map:", error);
      if (error.response) {
        setError(`Ошибка: ${error.response.data.detail || 'Неизвестная ошибка'}`);
      } else if (error.request) {
        setError('Не удалось подключиться к серверу. Убедитесь, что backend запущен на порту 8000');
      } else {
        setError(`Ошибка: ${error.message}`);
      }
    } finally {
      setLoading(false);
    }
  };

  if (!project) {
    return (
      <div className="min-h-screen flex items-center justify-center p-4">
        <div className="bg-white p-8 rounded-xl shadow-lg max-w-2xl w-full">
          <h1 className="text-3xl font-bold mb-2 text-gray-800">AI User Story Mapper</h1>
          <p className="text-gray-600 mb-6">Превратите ваши требования в структурированную карту пользовательских историй</p>
          
          <textarea
            className="w-full h-40 p-4 border border-gray-300 rounded-lg mb-4 focus:ring-2 focus:ring-blue-500 outline-none resize-none"
            placeholder="Опишите ваш продукт (например: Приложение для доставки пиццы с ролями курьера и клиента. Клиент может выбрать пиццу, оформить заказ и отслеживать доставку. Курьер получает заказы, видит маршрут и отмечает доставку...)"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
          />
          
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
              {error}
            </div>
          )}
          
          <button
            onClick={handleGenerate}
            disabled={loading || !input.trim()}
            className="w-full bg-blue-600 text-white py-3 rounded-lg font-semibold hover:bg-blue-700 transition disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {loading ? "AI анализирует требования (это займет ~20-40 сек)..." : "Сгенерировать карту"}
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
        </div>
        <button 
          onClick={() => {
            setProject(null);
            setInput('');
            setError(null);
          }} 
          className="text-blue-600 hover:underline font-medium"
        >
          ← Создать новую карту
        </button>
      </div>
      
      {/* Компонент Карты */}
      <StoryMap project={project} />
    </div>
  );
}

// --- КОМПОНЕНТ ОТРИСОВКИ КАРТЫ ---
function StoryMap({ project }) {
  // Нам нужно вытащить "Плоский" список всех Tasks, чтобы построить колонки
  const allTasks = project.activities.flatMap(act => 
    act.tasks.map(task => ({ ...task, activityTitle: act.title }))
  );

  return (
    <div className="inline-block min-w-full bg-white rounded-lg shadow-sm border border-gray-200">
      {/* 1. BACKBONE (Шапка: Активности и Таски) */}
      <div className="sticky top-0 z-10 bg-gray-50 border-b-2 border-gray-300">
        {/* Ряд Активностей */}
        <div className="flex border-b border-gray-200">
          <div className="w-32 flex-shrink-0 bg-gray-100 border-r-2 border-gray-300 p-2 flex items-center justify-center">
            <span className="text-xs font-bold text-gray-600 uppercase">Releases</span>
          </div>
          {project.activities.map(act => {
            const taskCount = act.tasks.length;
            return (
              <div 
                key={act.id} 
                className="bg-blue-100 border-r border-gray-200 p-3 text-center font-bold text-blue-800 flex items-center justify-center"
                style={{ width: `${taskCount * 220}px`, minWidth: '220px' }}
              >
                <span className="text-sm">{act.title}</span>
              </div>
            );
          })}
        </div>

        {/* Ряд Тасков (User Tasks) */}
        <div className="flex">
          <div className="w-32 flex-shrink-0 bg-gray-100 border-r-2 border-gray-300"></div>
          {allTasks.map(task => (
            <div 
              key={task.id} 
              className="w-[220px] flex-shrink-0 bg-blue-50 border-r border-gray-200 p-3 text-sm font-semibold text-center text-gray-700 min-h-[60px] flex items-center justify-center"
            >
              <span className="leading-tight">{task.title}</span>
            </div>
          ))}
        </div>
      </div>

      {/* 2. BODY (Релизы и Истории) */}
      <div>
        {project.releases.map(release => (
          <div key={release.id} className="flex border-b border-gray-200 min-h-[180px] hover:bg-gray-50 transition">
            {/* Заголовок Релиза (Слева) */}
            <div className="w-32 flex-shrink-0 bg-gray-100 p-3 font-bold flex items-center justify-center text-gray-700 border-r-2 border-gray-300">
              <span className="text-sm text-center">{release.title}</span>
            </div>

            {/* Колонки с Историями */}
            {allTasks.map(task => {
              // Фильтруем истории: они должны принадлежать и этому Таску, и этому Релизу
              const storiesInCell = task.stories.filter(s => s.release_id === release.id);

              return (
                <div 
                  key={`${task.id}-${release.id}`} 
                  className="w-[220px] flex-shrink-0 p-2 border-r border-dashed border-gray-300 bg-white"
                >
                  <div className="flex flex-col gap-2 min-h-[150px]">
                    {storiesInCell.length > 0 ? (
                      storiesInCell.map(story => (
                        <div 
                          key={story.id} 
                          className="bg-yellow-200 p-3 rounded shadow-sm hover:shadow-md transition cursor-pointer text-sm border border-yellow-300 group"
                        >
                          <div className="font-medium mb-1 text-gray-800">{story.title}</div>
                          {story.description && (
                            <div className="text-xs text-gray-600 line-clamp-2 mb-2">{story.description}</div>
                          )}
                          <div className="flex items-center justify-between mt-2">
                            {story.priority && (
                              <span className="text-[10px] uppercase px-2 py-0.5 bg-white/70 rounded font-semibold text-gray-700">
                                {story.priority}
                              </span>
                            )}
                            {story.acceptance_criteria && story.acceptance_criteria.length > 0 && (
                              <span className="text-[10px] text-gray-500">
                                {story.acceptance_criteria.length} AC
                              </span>
                            )}
                          </div>
                          {/* Показываем Acceptance Criteria при наведении */}
                          {story.acceptance_criteria && story.acceptance_criteria.length > 0 && (
                            <div className="hidden group-hover:block mt-2 pt-2 border-t border-yellow-300">
                              <div className="text-[10px] font-semibold text-gray-700 mb-1">Acceptance Criteria:</div>
                              <ul className="text-[10px] text-gray-600 space-y-1">
                                {story.acceptance_criteria.slice(0, 3).map((ac, idx) => (
                                  <li key={idx} className="flex items-start">
                                    <span className="mr-1">•</span>
                                    <span>{ac}</span>
                                  </li>
                                ))}
                                {story.acceptance_criteria.length > 3 && (
                                  <li className="text-gray-500">+{story.acceptance_criteria.length - 3} more</li>
                                )}
                              </ul>
                            </div>
                          )}
                        </div>
                      ))
                    ) : (
                      <div className="text-xs text-gray-400 text-center py-4">—</div>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </div>
  );
}

export default App;


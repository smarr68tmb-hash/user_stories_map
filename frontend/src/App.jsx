import { useState, useEffect, useCallback } from 'react';
import { Bot, Sparkles, Pencil } from 'lucide-react';
import api, { auth, enhancement, projects } from './api';
import StoryMap from './StoryMap.jsx';
import Auth from './Auth.jsx';
import ProjectList from './ProjectList.jsx';
import EnhancementPreview from './EnhancementPreview.jsx';
import Breadcrumb from './components/common/Breadcrumb.jsx';
import AutoResizeTextarea from './components/common/AutoResizeTextarea.jsx';
import { ToastProvider, useToast } from './hooks/useToast';
import { ProjectRefreshProvider, useProjectRefreshContext } from './context/ProjectRefreshContext';
import { useStreamingGeneration } from './hooks/useStreamingGeneration';
import { AIAssistantSidebar } from './components/AIAssistantSidebar';

const MAX_CHARS = 10000;
const MIN_CHARS = 10;

// Контекстные сообщения прогресса (обновлено для Phase 1 streaming)
const getProgressMessage = (progress, stage) => {
  if (stage === 'enhancing') {
    if (progress < 20) return '🔍 Анализирую требования...';
    return '✨ Улучшаю структуру...';
  }

  if (stage === 'generating') {
    if (progress < 30) return '👥 Выделяю роли пользователей...';
    if (progress < 50) return '🎯 Определяю основные активности...';
    if (progress < 70) return '📋 Генерирую пользовательские задачи...';
    return '✍️ Создаю истории пользователей...';
  }

  if (stage === 'validating') {
    if (progress < 80) return '🔍 Проверяю качество карты...';
    return '📊 Анализирую дубликаты...';
  }

  if (stage === 'saving') {
    return '💾 Сохраняю проект в базу данных...';
  }

  if (stage === 'complete') {
    return '🎉 Готово!';
  }

  // Для demo или загрузки примера
  if (progress < 50) return '📥 Загружаю данные...';
  return '✨ Подготавливаю визуализацию...';
};

function AppContent() {
  const [user, setUser] = useState(null);
  const [authChecked, setAuthChecked] = useState(false);

  // Загружаем сохраненный черновик из localStorage
  const [input, setInput] = useState(() => {
    return localStorage.getItem('draft_requirements') || '';
  });
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);
  const [project, setProject] = useState(null);
  const [error, setError] = useState(null);
  const [view, setView] = useState('list'); // 'list' или 'create' или 'demo'
  const [demoMode, setDemoMode] = useState(false); // флаг демо-режима
  
  // Two-Stage AI Processing состояния
  const [enhancementData, setEnhancementData] = useState(null);
  const [showEnhancementPreview, setShowEnhancementPreview] = useState(false);
  const [enhancementLoading, setEnhancementLoading] = useState(false);
  const [stage, setStage] = useState(null); // 'enhancing' | 'generating' | null

  // AI Agent состояние
  const [useAgent, setUseAgent] = useState(false);
  const toast = useToast();
  
  // Состояние для полного анализа
  const [isRunningFullAnalysis, setIsRunningFullAnalysis] = useState(false);

  // Локальное состояние для analysisResults (независимо от streaming)
  const [localAnalysisResults, setLocalAnalysisResults] = useState(null);

  // Обработчик запуска полного анализа
  const handleRunFullAnalysis = useCallback(async () => {
    if (!project || !project.id) {
      toast.error('Проект не загружен');
      return;
    }
    
    setIsRunningFullAnalysis(true);
    toast.info('Запуск полного анализа...');
    
    try {
      const response = await api.post(`/project/${project.id}/analyze/full`, {
        include_ai_conflicts: false,
        similarity_threshold: 0.7,
        duplicate_threshold: 0.9
      });
      
      // Обновляем результаты анализа на основе ответа
      const fullAnalysis = response.data;
      const updatedAnalysisResults = {
        duplicates: fullAnalysis.similarity?.stats?.duplicates_found || 0,
        similar: fullAnalysis.similarity?.stats?.similar_groups_found || 0,
        score: fullAnalysis.overall_score || 0,
        issues: fullAnalysis.validation?.issues || [],
        totalIssues: fullAnalysis.validation?.issues?.length || 0
      };

      // Обновляем локальное состояние analysisResults
      setLocalAnalysisResults(updatedAnalysisResults);

      toast.success(`Анализ завершен! Оценка: ${fullAnalysis.overall_score}/100`);
      console.log('Full analysis result:', fullAnalysis);
    } catch (error) {
      console.error('Full analysis error:', error);
      const errorMessage = error.response?.data?.detail || error.message || 'Ошибка при выполнении анализа';
      toast.error(`Ошибка анализа: ${errorMessage}`);
    } finally {
      setIsRunningFullAnalysis(false);
    }
  }, [project, toast, setLocalAnalysisResults]);

  // SSE Streaming hook (Phase 1)
  const {
    progress: streamProgress,
    stage: streamStage,
    analysisResults: streamingAnalysisResults,
    stats: streamStats,
    isStreaming,
    error: streamError,
    generateWithStreaming,
    cancelStreaming
  } = useStreamingGeneration();

  // Merged analysis results: приоритет у localAnalysisResults
  const analysisResults = localAnalysisResults || streamingAnalysisResults;

  // Редактирование названия проекта
  const [isEditingProjectName, setIsEditingProjectName] = useState(false);
  const [editedProjectName, setEditedProjectName] = useState('');
  const [projectNameError, setProjectNameError] = useState(null);
  const [updatingProjectName, setUpdatingProjectName] = useState(false);
  
  // Проверка текущей сессии при загрузке
  // Используем tryRestoreSession для восстановления сессии из localStorage (refresh token)
  useEffect(() => {
    let mounted = true;

    const checkSession = async () => {
      try {
        // Сначала пробуем восстановить сессию из localStorage (refresh token)
        const restoredUser = await auth.tryRestoreSession();
        if (mounted) {
          if (restoredUser) {
            setUser(restoredUser);
          } else {
            setUser(null);
          }
        }
      } catch {
        if (mounted) {
          setUser(null);
        }
      } finally {
        if (mounted) {
          setAuthChecked(true);
        }
      }
    };

    checkSession();

    return () => {
      mounted = false;
    };
  }, []);
  
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

  const handleLogin = async () => {
    // После успешного логина получаем пользователя из /me
    try {
      const res = await auth.getMe();
      setUser(res.data);
    } catch (e) {
      console.error("Failed to fetch user data:", e);
    } finally {
      setAuthChecked(true);
    }
  };

  const handleLogout = useCallback(async () => {
    await auth.logout();
    setUser(null);
    setProject(null);
    setLocalAnalysisResults(null);
    setInput('');
    setView('list');
    setDemoMode(false);
  }, []);

  const handleTryDemo = () => {
    setDemoMode(true);
    setView('demo');
    setAuthChecked(true);
  };

  const handleViewExample = async () => {
    setLoading(true);
    setProgress(10);
    setError(null);

    try {
      // Загружаем пример из локального JSON
      const response = await fetch('/examples/hybe-assist-recommendations.json');
      if (!response.ok) {
        throw new Error('Не удалось загрузить пример');
      }

      const exampleProject = await response.json();
      setProgress(100);
      setProject(exampleProject);
      setDemoMode(true);
      setAuthChecked(true);
      toast.success('🎉 Пример карты загружен! Зарегистрируйтесь чтобы создавать свои проекты.');
    } catch (error) {
      console.error('Error loading example:', error);
      setError('Не удалось загрузить пример. Попробуйте еще раз.');
    } finally {
      setLoading(false);
      setTimeout(() => setProgress(0), 500);
    }
  };

  // Stage 1: Улучшение требований
  const handleEnhanceRequirements = async () => {
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
    
    setEnhancementLoading(true);
    setStage('enhancing');
    setError(null);
    setProgress(10);
    
    try {
      // Stage 1: Улучшаем требования
      const enhanceRes = await enhancement.enhance(input);
      setProgress(40);
      setEnhancementData(enhanceRes.data);
      setShowEnhancementPreview(true);
    } catch (error) {
      console.error("Error enhancing requirements:", error);
      setProgress(0);
      if (error.response?.status === 401) {
        setError('Сессия истекла. Пожалуйста, войдите снова.');
        handleLogout();
      } else if (error.response) {
        const detail = error.response.data?.detail || 'Неизвестная ошибка';
        setError(`Ошибка улучшения: ${detail}`);
      } else if (error.request) {
        setError('Не удалось подключиться к серверу. Убедитесь, что backend запущен на порту 8000');
      } else {
        setError(`Ошибка: ${error.message}`);
      }
    } finally {
      setEnhancementLoading(false);
      setStage(null);
    }
  };
  
  // Stage 2: Генерация карты (после выбора текста)
  const handleGenerateWithText = async (textToUse, skipEnhancement = true) => {
    setShowEnhancementPreview(false);
    setLoading(true);
    setStage('generating');
    setProgress(50);
    
    try {
      // Генерируем карту с выбранным текстом (передаем useAgent)
      const res = await enhancement.generateMap(textToUse, skipEnhancement, true, useAgent);
      setProgress(80);
      const projectId = res.data.project_id;
      
      // Забираем полные данные
      const projectRes = await api.get(`/project/${projectId}`);
      setProgress(100);
      setProject(projectRes.data);
      
      // Очищаем сохраненный черновик после успешной генерации
      localStorage.removeItem('draft_requirements');
      setEnhancementData(null);
    } catch (error) {
      console.error("Error generating map:", error);
      setProgress(0);
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
      setStage(null);
      setTimeout(() => setProgress(0), 500);
    }
  };
  
  // Обработчики выбора в EnhancementPreview
  const handleUseOriginal = () => {
    handleGenerateWithText(input, true);
  };
  
  const handleUseEnhanced = (enhancedText) => {
    handleGenerateWithText(enhancedText, true);
  };
  
  const handleEditEnhanced = (editedText) => {
    handleGenerateWithText(editedText, true);
  };
  
  const handleCloseEnhancementPreview = () => {
    setShowEnhancementPreview(false);
  };

  // ============= Phase 1: SSE STREAMING GENERATION =============

  // Auto-show analysis notification when results arrive
  useEffect(() => {
    if (analysisResults) {
      const { duplicates, score, issues } = analysisResults;

      // Show notification for duplicates
      if (duplicates > 0) {
        toast.warning(`Найдено ${duplicates} дубликатов! Рекомендуется проверить истории.`);
      }

      // Show notification for low score
      if (score < 50) {
        toast.warning(`Оценка качества: ${score}/100. Требуется улучшение.`);
      } else if (score >= 80) {
        toast.success(`Отличная оценка качества: ${score}/100!`);
      }

      // Show notification for issues
      if (issues && issues.length > 0) {
        toast.info(`Обнаружено ${analysisResults.totalIssues} проблем. Проверьте анализ.`);
      }
    }
  }, [analysisResults, toast]);

  // Handle streaming error
  useEffect(() => {
    if (streamError) {
      setError(streamError);
      toast.error(streamError);
    }
  }, [streamError, toast]);

  // Stage 2: Генерация карты со streaming (новая версия для Phase 1)
  const handleGenerateWithStreaming = async (textToUse, useEnhancement = false) => {
    setShowEnhancementPreview(false);
    setError(null);

    try {
      // Запускаем streaming генерацию
      const result = await generateWithStreaming(textToUse, useEnhancement, useAgent);

      // Загружаем полный проект после завершения
      const projectRes = await api.get(`/project/${result.projectId}`);
      setProject(projectRes.data);

      // Очищаем черновик
      localStorage.removeItem('draft_requirements');
      setEnhancementData(null);

      toast.success(`Проект "${result.projectName}" создан! ${result.stats?.stories || 0} историй сгенерировано.`);

    } catch (error) {
      console.error("Error in streaming generation:", error);

      if (error.message.includes('SSE connection failed')) {
        setError('Соединение прервано. Попробуйте еще раз.');
      } else if (error.message.includes('Сессия истекла')) {
        setError('Сессия истекла. Пожалуйста, войдите снова.');
        handleLogout();
      } else {
        setError(error.message || 'Ошибка генерации карты');
      }
    }
  };

  // Обновленные обработчики для использования streaming
  const handleUseOriginalStreaming = () => {
    handleGenerateWithStreaming(input, false);
  };

  const handleUseEnhancedStreaming = (enhancedText) => {
    handleGenerateWithStreaming(enhancedText, false);
  };

  const handleEditEnhancedStreaming = (editedText) => {
    handleGenerateWithStreaming(editedText, false);
  };
  
  // Прямая генерация с использованием streaming (Phase 1)
  const handleDirectGenerate = async () => {
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

    // Используем новый streaming метод вместо старого
    handleGenerateWithStreaming(input, false);
  };

  // Демо-генерация (без регистрации)
  const handleDemoGenerate = async () => {
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
    setStage('generating');
    setProgress(10);
    setError(null);

    try {
      const res = await enhancement.generateMapDemo(input);
      setProgress(90);

      // Преобразуем ответ демо-API в формат проекта
      const demoProject = {
        id: -1, // фейковый ID для демо
        name: res.data.project_name,
        raw_requirements: input,
        activities: [],
        releases: res.data.releases,
        demo_mode: true,
      };

      // Парсим карту в формат activities/tasks/stories
      res.data.map.forEach((activityItem, actIdx) => {
        const activity = {
          id: -(actIdx + 1),
          title: activityItem.activity,
          position: actIdx,
          tasks: [],
        };

        activityItem.tasks?.forEach((taskItem, taskIdx) => {
          const task = {
            id: -(actIdx * 100 + taskIdx + 1),
            title: taskItem.taskTitle,
            position: taskIdx,
            stories: [],
          };

          taskItem.stories?.forEach((storyItem, storyIdx) => {
            const story = {
              id: -(actIdx * 10000 + taskIdx * 100 + storyIdx + 1),
              title: storyItem.title,
              description: storyItem.description,
              priority: storyItem.priority,
              acceptance_criteria: storyItem.acceptanceCriteria || [],
              release_id: storyItem.priority === 'MVP' ? -1 : storyItem.priority.includes('1') ? -2 : -3,
              position: storyIdx,
              status: 'todo',
            };
            task.stories.push(story);
          });

          activity.tasks.push(task);
        });

        demoProject.activities.push(activity);
      });

      setProgress(100);
      setProject(demoProject);
      toast.success(res.data.message || 'Демо-карта сгенерирована! Зарегистрируйтесь чтобы сохранить.');
    } catch (error) {
      console.error('Error generating demo map:', error);
      setProgress(0);
      if (error.response) {
        const detail = error.response.data?.detail || 'Неизвестная ошибка';
        setError(`Ошибка: ${detail}`);
      } else if (error.request) {
        setError('Не удалось подключиться к серверу');
      } else {
        setError(`Ошибка: ${error.message}`);
      }
    } finally {
      setLoading(false);
      setStage(null);
      setTimeout(() => setProgress(0), 500);
    }
  };

  // Основной метод генерации (с Two-Stage Processing)
  const handleGenerate = handleEnhanceRequirements;

  const handleSelectProject = (projectData) => {
    setProject(projectData);
  };

  const handleCreateNew = () => {
    setView('create');
    setProject(null);
    setLocalAnalysisResults(null);
    setInput('');
    setError(null);
  };

  const handleBackToList = () => {
    setView('list');
    setProject(null);
    setLocalAnalysisResults(null);
    setInput('');
    setError(null);
    localStorage.removeItem('draft_requirements');
    setIsEditingProjectName(false);
    setEditedProjectName('');
    setProjectNameError(null);
  };
  
  // Обработчики редактирования названия проекта
  const handleStartEditProjectName = () => {
    if (project) {
      setEditedProjectName(project.name);
      setIsEditingProjectName(true);
      setProjectNameError(null);
    }
  };
  
  const handleCancelEditProjectName = () => {
    setIsEditingProjectName(false);
    setEditedProjectName('');
    setProjectNameError(null);
  };
  
  const handleSaveProjectName = async () => {
    if (!project) return;
    
    const trimmedName = editedProjectName.trim();
    
    // Валидация
    if (!trimmedName) {
      setProjectNameError('Название проекта не может быть пустым');
      return;
    }
    
    if (trimmedName.length > 255) {
      setProjectNameError('Название проекта не может превышать 255 символов');
      return;
    }
    
    if (trimmedName === project.name) {
      // Не изменилось, просто отменяем редактирование
      handleCancelEditProjectName();
      return;
    }
    
    setUpdatingProjectName(true);
    setProjectNameError(null);
    
    try {
      const response = await projects.update(project.id, trimmedName);
      // Обновляем проект с новыми данными
      setProject(response.data);
      setIsEditingProjectName(false);
      setEditedProjectName('');
    } catch (err) {
      console.error('Error updating project name:', err);
      if (err.response?.status === 401) {
        setProjectNameError('Сессия истекла. Пожалуйста, войдите снова.');
        handleLogout();
      } else if (err.response?.status === 400) {
        setProjectNameError(err.response.data?.detail || 'Некорректное название проекта');
      } else if (err.response?.status === 404) {
        setProjectNameError('Проект не найден');
      } else {
        setProjectNameError('Не удалось обновить название проекта');
      }
    } finally {
      setUpdatingProjectName(false);
    }
  };

  // Если не авторизован, показываем форму входа
  if (!authChecked) {
    return (
      <div className="min-h-screen flex items-center justify-center text-gray-600">
        Проверяем сессию...
      </div>
    );
  }

  if (!user && !demoMode) {
    return (
      <>
        <a href="#main-content" className="skip-to-content">
          Перейти к содержимому
        </a>
        <Auth onLogin={handleLogin} onTryDemo={handleTryDemo} onViewExample={handleViewExample} />
      </>
    );
  }

  // Если есть выбранный проект, показываем карту
  if (project) {
    return (
      <>
        <a href="#main-content" className="skip-to-content">
          Перейти к содержимому
        </a>
        <ProjectRefreshProvider
          projectId={project.id}
          onUpdate={setProject}
          onUnauthorized={handleLogout}
          toast={toast}
        >
          <ProjectPage
          project={project}
          user={user}
          isEditingProjectName={isEditingProjectName}
          editedProjectName={editedProjectName}
          projectNameError={projectNameError}
          updatingProjectName={updatingProjectName}
          handleStartEditProjectName={handleStartEditProjectName}
          handleSaveProjectName={handleSaveProjectName}
          handleCancelEditProjectName={handleCancelEditProjectName}
          setEditedProjectName={setEditedProjectName}
          setProjectNameError={setProjectNameError}
          handleBackToList={handleBackToList}
          handleLogout={handleLogout}
          onUpdateProject={setProject}
          analysisResults={analysisResults}
          toast={toast}
          handleRunFullAnalysis={handleRunFullAnalysis}
          isRunningFullAnalysis={isRunningFullAnalysis}
        />
      </ProjectRefreshProvider>
      </>
    );
  }

  // Если нет проекта и view === 'list', показываем список проектов
  if (view === 'list') {
    return (
      <>
        <a href="#main-content" className="skip-to-content">
          Перейти к содержимому
        </a>
        <ProjectList
        onSelectProject={handleSelectProject}
        onCreateNew={handleCreateNew}
        onLogout={handleLogout}
        user={user}
      />
      </>
    );
  }

  // Если view === 'demo', показываем демо-форму
  if (view === 'demo' && demoMode) {
    return (
      <>
        <a href="#main-content" className="skip-to-content">
          Перейти к содержимому
        </a>
        <div className="min-h-screen flex items-center justify-center p-4 bg-gray-50">
          <div id="main-content" className="bg-white p-8 rounded-xl shadow-lg max-w-2xl w-full">
            <div className="mb-6 p-4 bg-gradient-to-r from-purple-50 to-blue-50 border border-purple-200 rounded-lg">
              <div className="flex items-center gap-2 mb-2">
                <span className="text-2xl">✨</span>
                <h2 className="font-bold text-gray-800">Демо-режим</h2>
              </div>
              <p className="text-sm text-gray-600">
                Вы можете сгенерировать одну карту бесплатно без регистрации.
                Зарегистрируйтесь чтобы сохранить и редактировать проекты!
              </p>
            </div>

            <div className="flex justify-between items-start mb-4">
              <div>
                <h1 className="text-3xl font-bold mb-2 text-gray-800">Попробуйте AI User Story Mapper</h1>
                <p className="text-gray-600">Превратите ваши требования в структурированную карту пользовательских историй</p>
              </div>
              <button
                onClick={() => {
                  setDemoMode(false);
                  setView('list');
                }}
                className="text-gray-500 hover:text-gray-700 text-sm font-medium"
              >
                ✕
              </button>
            </div>

            <div className="mb-2">
              <AutoResizeTextarea
                value={input}
                onChange={(e) => {
                  setInput(e.target.value);
                  setError(null);
                }}
                minHeight={160}
                maxHeight={600}
                className={`w-full p-4 border rounded-lg mb-2 focus:ring-2 focus:ring-purple-500 outline-none ${
                  !isValidInput && input.length > 0
                    ? 'border-red-300 bg-red-50'
                    : 'border-gray-300'
                }`}
                placeholder="Опишите ваш продукт (например: Приложение для доставки пиццы с ролями курьера и клиента. Клиент может выбрать пиццу, оформить заказ и отслеживать доставку. Курьер получает заказы, видит маршрут и отмечает доставку...)"
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

            {(loading || enhancementLoading || isStreaming) && (
              <div className="mb-4">
                <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
                  <div
                    className="h-2.5 rounded-full transition-all duration-300 bg-gradient-to-r from-purple-600 to-blue-600"
                    style={{ width: `${isStreaming ? streamProgress : progress}%` }}
                    role="progressbar"
                    aria-valuenow={isStreaming ? streamProgress : progress}
                    aria-valuemin="0"
                    aria-valuemax="100"
                  ></div>
                </div>
                <p className="text-xs text-gray-600 text-center">
                  <span className="flex items-center justify-center gap-2">
                    <span className="inline-block w-2 h-2 bg-purple-600 rounded-full animate-pulse"></span>
                    {getProgressMessage(isStreaming ? streamProgress : progress, isStreaming ? streamStage : 'generating')} {Math.round(isStreaming ? streamProgress : progress)}%
                  </span>
                </p>
              </div>
            )}

            {error && (
              <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm" role="alert">
                {error}
              </div>
            )}

            <button
              onClick={handleDemoGenerate}
              disabled={loading || enhancementLoading || !isValidInput || !input.trim()}
              className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white py-4 rounded-lg font-semibold hover:from-purple-700 hover:to-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
            >
              {loading ? (
                <span className="flex items-center justify-center gap-2">
                  <span className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full"></span>
                  Генерация...
                </span>
              ) : (
                <span className="flex items-center justify-center gap-2">
                  <Sparkles className="w-5 h-5" />
                  Сгенерировать демо-карту
                </span>
              )}
            </button>

            <div className="mt-4 text-center">
              <button
                onClick={() => {
                  setDemoMode(false);
                  setView('list');
                }}
                className="text-blue-600 hover:underline text-sm"
              >
                Уже есть аккаунт? Войти
              </button>
            </div>
          </div>
        </div>
      </>
    );
  }

  // Если view === 'create', показываем форму создания нового проекта
  if (view === 'create') {
    return (
      <>
        <a href="#main-content" className="skip-to-content">
          Перейти к содержимому
        </a>
        <div className="min-h-screen flex items-center justify-center p-4 bg-gray-50">
          <div id="main-content" className="bg-white p-8 rounded-xl shadow-lg max-w-2xl w-full">
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
            <AutoResizeTextarea
              value={input}
              onChange={(e) => {
                setInput(e.target.value);
                setError(null);
              }}
              minHeight={160}
              maxHeight={600}
              className={`w-full p-4 border rounded-lg mb-2 focus:ring-2 focus:ring-blue-500 outline-none ${
                !isValidInput && input.length > 0
                  ? 'border-red-300 bg-red-50'
                  : 'border-gray-300'
              }`}
              placeholder="Опишите ваш продукт (например: Приложение для доставки пиццы с ролями курьера и клиента. Клиент может выбрать пиццу, оформить заказ и отслеживать доставку. Курьер получает заказы, видит маршрут и отмечает доставку...)"
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
          
          {/* Прогресс-бар с этапами */}
          {(loading || enhancementLoading) && (
            <div className="mb-4">
              <div className="w-full bg-gray-200 rounded-full h-2.5 mb-2">
                <div 
                  className={`h-2.5 rounded-full transition-all duration-300 ${
                    stage === 'enhancing' ? 'bg-indigo-500' : 'bg-blue-600'
                  }`}
                  style={{ width: `${progress}%` }}
                  role="progressbar"
                  aria-valuenow={progress}
                  aria-valuemin="0"
                  aria-valuemax="100"
                ></div>
              </div>
              <p className="text-xs text-gray-600 text-center">
                <span className="flex items-center justify-center gap-2">
                  <span className={`inline-block w-2 h-2 rounded-full animate-pulse ${
                    stage === 'enhancing' ? 'bg-indigo-500' : 'bg-blue-600'
                  }`}></span>
                  {getProgressMessage(progress, stage)} {Math.round(progress)}%
                </span>
              </p>
            </div>
          )}
          
          {error && (
            <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm" role="alert">
              {error}
            </div>
          )}

          {/* AI Agent Checkbox */}
          <div className="mb-4 p-4 bg-gradient-to-r from-blue-50 to-indigo-50 border border-blue-200 rounded-lg">
            <label className="flex items-start gap-3 cursor-pointer group">
              <input
                type="checkbox"
                checked={useAgent}
                onChange={(e) => setUseAgent(e.target.checked)}
                disabled={loading || enhancementLoading}
                className="mt-1 w-4 h-4 text-blue-600 border-gray-300 rounded focus:ring-blue-500 focus:ring-2 disabled:opacity-50 disabled:cursor-not-allowed"
              />
              <div className="flex-1">
                <div className="flex items-center gap-2">
                  <span className="font-semibold text-gray-800 group-hover:text-blue-700 transition flex items-center gap-2">
                    <Bot className="w-5 h-5" />
                    AI-Агент (MVP)
                  </span>
                  <span className="px-2 py-0.5 text-xs font-semibold bg-green-100 text-green-700 rounded-full">
                    +15% качество
                  </span>
                </div>
                <p className="text-xs text-gray-600 mt-1 leading-relaxed">
                  Улучшенная генерация с автоматической валидацией и исправлением ошибок.
                  Агент проверит структуру карты и автоматически исправит критические проблемы.
                </p>
                <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                  <span className="flex items-center gap-1">
                    <svg className="w-3 h-3 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    Валидация
                  </span>
                  <span className="flex items-center gap-1">
                    <svg className="w-3 h-3 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    Автоисправление
                  </span>
                  <span className="flex items-center gap-1">
                    <svg className="w-3 h-3 text-green-500" fill="currentColor" viewBox="0 0 20 20">
                      <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                    </svg>
                    Метрики качества
                  </span>
                </div>
              </div>
            </label>
          </div>

          {/* Основная кнопка - с улучшением */}
          <button
            onClick={handleGenerate}
            disabled={loading || enhancementLoading || !isValidInput || !input.trim()}
            className="w-full bg-gradient-to-r from-indigo-600 to-purple-600 text-white py-3 rounded-lg font-semibold hover:from-indigo-700 hover:to-purple-700 transition disabled:opacity-50 disabled:cursor-not-allowed mb-2 shadow-lg shadow-indigo-200"
            aria-label="Сгенерировать карту с улучшением требований"
          >
            {enhancementLoading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></span>
                Анализируем требования...
              </span>
            ) : loading ? (
              <span className="flex items-center justify-center gap-2">
                <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></span>
                Генерация карты...
              </span>
            ) : (
              <span className="flex items-center justify-center gap-2">
                <Sparkles className="w-5 h-5" />
                Сгенерировать с улучшением (рекомендуется)
              </span>
            )}
          </button>
          
          {/* Альтернативная кнопка - без улучшения */}
          <button
            onClick={handleDirectGenerate}
            disabled={loading || enhancementLoading || !isValidInput || !input.trim()}
            className="w-full text-gray-600 hover:text-gray-800 py-2 rounded-lg font-medium border border-gray-300 hover:border-gray-400 transition disabled:opacity-50 disabled:cursor-not-allowed mb-3 text-sm"
            aria-label="Сгенерировать карту без улучшения требований"
          >
            Сгенерировать без улучшения
          </button>
          
          <button
            onClick={handleBackToList}
            className="w-full text-gray-600 hover:text-gray-800 py-2 rounded-lg font-medium border border-gray-300 hover:border-gray-400 transition"
          >
            ← Назад к списку проектов
          </button>
          
          <p className="mt-4 text-xs text-gray-500 text-center">
            💡 Two-Stage AI: сначала AI улучшает требования, затем генерирует качественную карту
          </p>
          
          {/* EnhancementPreview Modal */}
          <EnhancementPreview
            originalText={input}
            enhancementData={enhancementData}
            isOpen={showEnhancementPreview}
            onClose={handleCloseEnhancementPreview}
            onUseOriginal={handleUseOriginal}
            onUseEnhanced={handleUseEnhanced}
            onEdit={handleEditEnhanced}
          />
        </div>
      </div>
      </>
    );
  }

  // По умолчанию возвращаемся к списку (не должно быть достигнуто)
  return null;
}

function ProjectPage({
  project,
  user,
  isEditingProjectName,
  editedProjectName,
  projectNameError,
  updatingProjectName,
  handleStartEditProjectName,
  handleSaveProjectName,
  handleCancelEditProjectName,
  setEditedProjectName,
  setProjectNameError,
  handleBackToList,
  handleLogout,
  onUpdateProject,
  analysisResults,
  toast,
  handleRunFullAnalysis,
  isRunningFullAnalysis,
}) {
  const { isRefreshing, refreshProject } = useProjectRefreshContext();
  const [isMapLoading, setIsMapLoading] = useState(true);

  // Проверяем, является ли проект demo-проектом
  const isDemoProject = project && (project.demo_mode || (typeof project.id === 'number' && project.id < 0));

  useEffect(() => {
    let mounted = true;

    const hydrate = async () => {
      setIsMapLoading(true);
      try {
        // Для demo-проектов не делаем запрос к API
        if (isDemoProject) {
          setIsMapLoading(false);
          return;
        }
        await refreshProject({ silent: false });
      } catch (error) {
        console.error('Failed to refresh project', error);
      } finally {
        if (mounted) {
          setIsMapLoading(false);
        }
      }
    };

    hydrate();

    return () => {
      mounted = false;
    };
  }, [refreshProject, isDemoProject]);

  const breadcrumbItems = [
    {
      label: 'Проекты',
      href: '#',
      onClick: handleBackToList,
    },
    {
      label: project.name,
    },
  ];

  return (
    <div className="min-h-screen p-4 md:p-8 overflow-x-auto bg-gray-50">
      <Breadcrumb items={breadcrumbItems} />

      <div id="main-content" className="mb-6 flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div className="flex-1">
          {isEditingProjectName ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={editedProjectName}
                  onChange={(e) => {
                    setEditedProjectName(e.target.value);
                    setProjectNameError(null);
                  }}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') {
                      handleSaveProjectName();
                    } else if (e.key === 'Escape') {
                      handleCancelEditProjectName();
                    }
                  }}
                  disabled={updatingProjectName}
                  maxLength={255}
                  className="flex-1 px-3 py-2 text-2xl font-bold text-gray-800 border-2 border-blue-500 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  autoFocus
                />
                <button
                  onClick={handleSaveProjectName}
                  disabled={updatingProjectName || !editedProjectName.trim()}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg font-medium hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Сохранить название проекта"
                >
                  {updatingProjectName ? (
                    <span className="flex items-center gap-2">
                      <span className="animate-spin h-4 w-4 border-2 border-white border-t-transparent rounded-full"></span>
                      Сохранение...
                    </span>
                  ) : (
                    'Сохранить'
                  )}
                </button>
                <button
                  onClick={handleCancelEditProjectName}
                  disabled={updatingProjectName}
                  className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg font-medium hover:bg-gray-300 transition disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Отменить редактирование"
                >
                  Отмена
                </button>
              </div>
              {projectNameError && (
                <div className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">
                  {projectNameError}
                </div>
              )}
              <div className="text-xs text-gray-500">
                {editedProjectName.length} / 255 символов
              </div>
            </div>
          ) : (
            <div className="flex items-center gap-2 group">
              <h1 className="text-2xl font-bold text-gray-800">{project.name}</h1>
              {isRefreshing && (
                <span className="text-xs text-gray-500 flex items-center gap-1">
                  <span className="animate-pulse text-green-500">●</span>
                  Синхронизация
                </span>
              )}
              <button
                onClick={handleStartEditProjectName}
                className="opacity-0 group-hover:opacity-100 transition-opacity p-1 text-gray-400 hover:text-blue-600"
                aria-label="Редактировать название проекта"
                title="Редактировать название проекта"
              >
                <Pencil className="w-5 h-5" />
              </button>
            </div>
          )}
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

      {/* Main content with sidebar spacing */}
      <div className="relative">
        <StoryMap
          project={project}
          onUpdate={onUpdateProject}
          onUnauthorized={handleLogout}
          isLoading={isMapLoading || isRefreshing}
        />

        {/* AI Assistant Sidebar - shown when project is loaded */}
        {project && (
          <AIAssistantSidebar
            project={project}
            analysisResults={analysisResults}
            onRunFullAnalysis={handleRunFullAnalysis}
            isAnalyzing={isRunningFullAnalysis}
          />
        )}
      </div>
    </div>
  );
}

function App() {
  return (
    <ToastProvider>
      <AppContent />
    </ToastProvider>
  );
}

export default App;


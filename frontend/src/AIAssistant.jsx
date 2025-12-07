import { useRef, useState } from 'react';
import {
  Sparkles, X, FileText, CheckSquare, Scissors, AlertTriangle,
  Loader2, CheckCircle, Info
} from 'lucide-react';
import api from './api';
import AutoResizeTextarea from './components/common/AutoResizeTextarea.jsx';
import useFocusTrap from './hooks/useFocusTrap';
import useKeyboardShortcuts from './hooks/useKeyboardShortcuts';

/**
 * @typedef {Object} Story
 * @property {number} id
 * @property {string} title
 * @property {string} description
 * @property {string[]} acceptance_criteria
 * @property {string} [priority]
 */

/**
 * @typedef {Object} AIResult
 * @property {boolean} success
 * @property {string} message
 * @property {string} [suggestion]
 * @property {Story} [improved_story]
 * @property {Story[]} [additional_stories]
 */

/**
 * @typedef {Object} AIAssistantProps
 * @property {Story} story
 * @property {number} taskId
 * @property {number} releaseId
 * @property {boolean} isOpen
 * @property {() => void} onClose
 * @property {(story: Story) => void} onStoryImproved
 */

/**
 * @param {AIAssistantProps} props
 */
function AIAssistant({ story, taskId, releaseId, isOpen, onClose, onStoryImproved }) {
  const [prompt, setPrompt] = useState('');
  const [selectedActionId, setSelectedActionId] = useState(/** @type {string | null} */ (null));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(/** @type {string | null} */ (null));
  const [result, setResult] = useState(/** @type {AIResult | null} */ (null));
  const [improvementHistory, setImprovementHistory] = useState(/** @type {Array<{timestamp: string, prompt: string, success: boolean, message: string}>} */ ([]));
  const modalRef = useRef(null);
  useFocusTrap(modalRef, isOpen);

  // Keyboard shortcuts
  useKeyboardShortcuts([
    { key: 'Escape', handler: onClose },
    { key: 'Enter', ctrl: true, handler: () => !loading && prompt.trim() && handleImprove() },
  ], isOpen);

  const quickActions = [
    {
      id: 'details',
      label: 'Улучшить описание',
      icon: FileText,
      prompt: 'Сделай лучше и понятнее описание по best практикам User Story. Добавь контекст использования, бизнес-ценность и детали реализации. Убедись, что описание следует формату "Как [роль], я хочу [действие], чтобы [результат]" и содержит достаточно информации для понимания функциональности.'
    },
    {
      id: 'criteria',
      label: 'Улучшить критерии',
      icon: CheckSquare,
      prompt: 'Улучши и расширь acceptance criteria. Сделай их более конкретными, измеримыми и полными. Каждый критерий должен быть проверяемым, содержать конкретные условия и ожидаемые результаты. Добавь критерии для успешных сценариев и обработки ошибок.'
    },
    {
      id: 'split',
      label: 'Разделить',
      icon: Scissors,
      prompt: 'Проанализируй историю и предложи, как её можно разделить на 2-3 более мелкие, независимые истории. Каждая новая история должна быть самодостаточной и иметь четкую бизнес-ценность.'
    },
    {
      id: 'edge_cases',
      label: 'Edge cases',
      icon: AlertTriangle,
      prompt: 'Добавь edge cases (граничные случаи) в acceptance criteria. Подумай об ошибках, крайних ситуациях, невалидных данных, сетевых проблемах и других исключительных сценариях, которые нужно обработать.'
    }
  ];

  /**
   * @param {typeof quickActions[0]} action
   */
  const handleQuickAction = (action) => {
    setPrompt(action.prompt);
    setSelectedActionId(action.id);
  };

  const handleImprove = async () => {
    if (!prompt.trim()) {
      setError('Пожалуйста, введите запрос');
      return;
    }

    setLoading(true);
    setError(null);
    setResult(null);

    try {
      // Определяем action: используем сохраненный selectedActionId или ищем по промпту
      const actionId = selectedActionId || quickActions.find(a => a.prompt === prompt)?.id || null;
      
      const response = await api.post(`/story/${story.id}/ai-improve`, {
        prompt: prompt,
        action: actionId
      });

      const data = response.data;
      setResult(data);

      // Добавляем в историю улучшений
      setImprovementHistory(prev => [...prev, {
        timestamp: new Date().toLocaleString('ru-RU'),
        prompt: prompt,
        success: data.success,
        message: data.message
      }]);

      // Если успешно улучшена, обновляем карту
      if (data.success && data.improved_story) {
        setTimeout(() => {
          onStoryImproved();
          // Не закрываем сразу, чтобы пользователь увидел результат
        }, 1500);
      }
    } catch (err) {
      console.error('Error improving story:', err);
      setError(/** @type {any} */ (err).response?.data?.detail || 'Не удалось улучшить историю');
    } finally {
      setLoading(false);
    }
  };

  const handleCreateSplitStories = async () => {
    if (!result?.additional_stories) return;

    try {
      // Создаём новые истории из результата split
      for (const newStory of result.additional_stories) {
        await api.post('/story', {
          task_id: taskId,
          release_id: releaseId,
          title: newStory.title,
          description: newStory.description,
          priority: newStory.priority,
          acceptance_criteria: newStory.acceptance_criteria
        });
      }

      // Удаляем оригинальную историю
      await api.delete(`/story/${story.id}`);

      // Обновляем карту
      onStoryImproved();
      onClose();
    } catch (err) {
      console.error('Error creating split stories:', err);
      setError('Не удалось создать разделённые истории');
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4 animate-fade-in"
      role="dialog"
      aria-modal="true"
    >
      <div
        ref={modalRef}
        className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto animate-scale-in"
        tabIndex={-1}
      >
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-purple-600 to-blue-600 text-white p-6 rounded-t-lg">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-2xl font-bold flex items-center gap-2">
                <Sparkles className="w-6 h-6" />
                AI Ассистент
              </h2>
              <p className="text-sm text-purple-100 mt-1">
                Интерактивное улучшение карточки через AI
              </p>
            </div>
            <button
              onClick={onClose}
              className="min-w-[44px] min-h-[44px] flex items-center justify-center text-white hover:text-gray-200 rounded-lg hover:bg-white/10 transition"
              aria-label="Закрыть"
            >
              <X className="w-6 h-6" />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="p-6">
          {/* Current Story Info */}
          <div className="mb-6 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
            <h3 className="font-semibold text-gray-800 mb-2">Текущая история:</h3>
            <div className="text-sm">
              <p className="font-medium text-gray-900">{story.title}</p>
              {story.description && (
                <p className="text-gray-600 mt-1">{story.description}</p>
              )}
              <div className="flex gap-2 mt-2">
                <span className="text-xs px-2 py-1 bg-white rounded border border-yellow-300">
                  {story.priority}
                </span>
                {story.acceptance_criteria && story.acceptance_criteria.length > 0 && (
                  <span className="text-xs px-2 py-1 bg-white rounded border border-yellow-300">
                    {story.acceptance_criteria.length} КП
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="mb-6">
            <h3 className="font-semibold text-gray-800 mb-3">Быстрые действия:</h3>
            <div className="grid grid-cols-2 gap-3">
              {quickActions.map(action => {
                const IconComponent = action.icon;
                return (
                  <button
                    key={action.id}
                    onClick={() => handleQuickAction(action)}
                    className="p-3 text-left border-2 border-gray-200 rounded-lg hover:border-purple-400 hover:bg-purple-50 transition flex items-center gap-2"
                  >
                    <IconComponent className="w-4 h-4 text-purple-600" />
                    <span className="font-medium text-sm">{action.label}</span>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Custom Prompt */}
          <div className="mb-6">
            <h3 className="font-semibold text-gray-800 mb-3">Или напишите свой запрос:</h3>
            <AutoResizeTextarea
              value={prompt}
              onChange={(/** @type {React.ChangeEvent<HTMLTextAreaElement>} */ e) => {
                setPrompt(e.target.value);
                // Сбрасываем selectedActionId если пользователь редактирует промпт вручную
                if (selectedActionId && e.target.value !== quickActions.find(a => a.id === selectedActionId)?.prompt) {
                  setSelectedActionId(null);
                }
              }}
              minHeight={80}
              maxHeight={300}
              placeholder="Например: Улучши описание истории по best практикам User Story, добавь больше контекста и деталей..."
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 outline-none"
              disabled={loading}
            />
          </div>

          {/* Action Button */}
          <button
            onClick={handleImprove}
            disabled={loading || !prompt.trim()}
            className="w-full bg-gradient-to-r from-purple-600 to-blue-600 text-white py-3 px-6 rounded-lg font-semibold hover:from-purple-700 hover:to-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition flex items-center justify-center gap-2"
          >
            {loading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                <span>Улучшаем...</span>
              </>
            ) : (
              <>
                <Sparkles className="w-5 h-5" />
                <span>Улучшить историю</span>
              </>
            )}
          </button>

          {/* Error */}
          {error && (
            <div className="mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
              {error}
            </div>
          )}

          {/* Result */}
          {result && (
            <div className="mt-6 p-4 bg-green-50 border border-green-200 rounded-lg">
              <div className="flex items-start gap-3 mb-3">
                <CheckCircle className="w-6 h-6 text-green-600 flex-shrink-0" />
                <div className="flex-1">
                  <h4 className="font-semibold text-green-800">{result.message}</h4>
                  {result.suggestion && (
                    <p className="text-sm text-green-700 mt-1">{result.suggestion}</p>
                  )}
                </div>
              </div>

              {/* Split Result */}
              {result.additional_stories && result.additional_stories.length > 0 && (
                <div className="mt-4">
                  <h5 className="font-semibold text-gray-800 mb-2">
                    Предлагаемые истории ({result.additional_stories.length}):
                  </h5>
                  <div className="space-y-3">
                    {result.additional_stories.map((newStory, idx) => (
                      <div key={idx} className="bg-white p-3 rounded border border-green-300">
                        <p className="font-medium text-gray-900">{newStory.title}</p>
                        {newStory.description && (
                          <p className="text-sm text-gray-600 mt-1">{newStory.description}</p>
                        )}
                        <div className="flex gap-2 mt-2">
                          <span className="text-xs px-2 py-1 bg-gray-100 rounded">
                            {newStory.priority}
                          </span>
                          {newStory.acceptance_criteria && newStory.acceptance_criteria.length > 0 && (
                            <span className="text-xs px-2 py-1 bg-gray-100 rounded">
                              {newStory.acceptance_criteria.length} КП
                            </span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                  <button
                    onClick={handleCreateSplitStories}
                    className="mt-4 w-full bg-green-600 text-white py-2 px-4 rounded-lg font-semibold hover:bg-green-700 transition"
                  >
                    Применить разделение
                  </button>
                </div>
              )}

              {/* Improved Story Preview */}
              {result.improved_story && (
                <div className="mt-4 bg-white p-3 rounded border border-green-300">
                  <p className="text-xs text-green-700 mb-2">Обновлённая история:</p>
                  <p className="font-medium text-gray-900">{result.improved_story.title}</p>
                  {result.improved_story.description && (
                    <p className="text-sm text-gray-600 mt-1">{result.improved_story.description}</p>
                  )}
                  {result.improved_story.acceptance_criteria && result.improved_story.acceptance_criteria.length > 0 && (
                    <div className="mt-2">
                      <p className="text-xs font-semibold text-gray-700">Критерии приёмки:</p>
                      <ul className="text-xs text-gray-600 mt-1 space-y-1">
                        {result.improved_story.acceptance_criteria.map((ac, idx) => (
                          <li key={idx} className="flex items-start">
                            <span className="mr-1">•</span>
                            <span>{ac}</span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}

          {/* Improvement History */}
          {improvementHistory.length > 0 && (
            <div className="mt-6">
              <h3 className="font-semibold text-gray-800 mb-3">История улучшений:</h3>
              <div className="space-y-2 max-h-48 overflow-y-auto">
                {improvementHistory.map((item, idx) => (
                  <div key={idx} className="p-3 bg-gray-50 border border-gray-200 rounded text-sm">
                    <div className="flex justify-between items-start mb-1">
                      <span className="text-xs text-gray-500">{item.timestamp}</span>
                      <span className={`text-xs px-2 py-0.5 rounded flex items-center gap-1 ${item.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                        {item.success ? <CheckCircle className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                      </span>
                    </div>
                    <p className="text-gray-700">{item.prompt}</p>
                    <p className="text-xs text-gray-500 mt-1">{item.message}</p>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Rate Limit Info */}
          <div className="mt-6 p-3 bg-blue-50 border border-blue-200 rounded-lg text-sm text-blue-700">
            <p className="flex items-center gap-2">
              <Info className="w-4 h-4" />
              <span>Лимит: 20 запросов в час на карточку</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AIAssistant;


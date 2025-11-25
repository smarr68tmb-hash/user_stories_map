import { useState } from 'react';
import api from './api';

function AIAssistant({ story, taskId, releaseId, isOpen, onClose, onStoryImproved }) {
  const [prompt, setPrompt] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [result, setResult] = useState(null);
  const [improvementHistory, setImprovementHistory] = useState([]);

  const quickActions = [
    {
      id: 'details',
      label: '📝 Добавить детали',
      prompt: 'Добавь больше деталей про оплату и обработку ошибок'
    },
    {
      id: 'criteria',
      label: '✅ Улучшить критерии',
      prompt: 'Улучши acceptance criteria, сделай их более конкретными'
    },
    {
      id: 'split',
      label: '✂️ Разделить',
      prompt: 'Раздели эту историю на 2 отдельные независимые истории'
    },
    {
      id: 'edge_cases',
      label: '⚠️ Edge cases',
      prompt: 'Добавь edge cases для offline режима и обработки ошибок'
    }
  ];

  const handleQuickAction = (action) => {
    setPrompt(action.prompt);
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
      const response = await api.post(`/story/${story.id}/ai-improve`, {
        prompt: prompt,
        action: quickActions.find(a => a.prompt === prompt)?.id || null
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
      setError(err.response?.data?.detail || 'Не удалось улучшить историю');
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
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-3xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="sticky top-0 bg-gradient-to-r from-purple-600 to-blue-600 text-white p-6 rounded-t-lg">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-2xl font-bold flex items-center gap-2">
                <span>✨</span>
                AI Assistant
              </h2>
              <p className="text-sm text-purple-100 mt-1">
                Интерактивное улучшение карточки через AI
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-white hover:text-gray-200 text-2xl font-bold"
            >
              ×
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
                    {story.acceptance_criteria.length} AC
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div className="mb-6">
            <h3 className="font-semibold text-gray-800 mb-3">Быстрые действия:</h3>
            <div className="grid grid-cols-2 gap-3">
              {quickActions.map(action => (
                <button
                  key={action.id}
                  onClick={() => handleQuickAction(action)}
                  className="p-3 text-left border-2 border-gray-200 rounded-lg hover:border-purple-400 hover:bg-purple-50 transition"
                >
                  <span className="font-medium text-sm">{action.label}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Custom Prompt */}
          <div className="mb-6">
            <h3 className="font-semibold text-gray-800 mb-3">Или напишите свой запрос:</h3>
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              placeholder="Например: Добавь больше информации про обработку платежей..."
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-purple-500 outline-none resize-none"
              rows="3"
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
                <div className="animate-spin rounded-full h-5 w-5 border-b-2 border-white"></div>
                <span>Улучшаем...</span>
              </>
            ) : (
              <>
                <span>✨</span>
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
              <div className="flex items-start gap-2 mb-3">
                <span className="text-2xl">✅</span>
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
                              {newStory.acceptance_criteria.length} AC
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
                      <p className="text-xs font-semibold text-gray-700">Acceptance Criteria:</p>
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
                      <span className={`text-xs px-2 py-0.5 rounded ${item.success ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'}`}>
                        {item.success ? '✓' : '✗'}
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
              <span>ℹ️</span>
              <span>Лимит: 20 запросов в час на карточку</span>
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

export default AIAssistant;


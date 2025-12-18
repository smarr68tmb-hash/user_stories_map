/**
 * AI Assistant Sidebar Component (Phase 1)
 *
 * Permanently visible panel showing:
 * - Analysis summary (duplicates, score, issues)
 * - AI recommendations
 * - Quick actions
 *
 * Features:
 * - Auto-updates from streaming analysis
 * - Collapsible/expandable
 * - Sticky positioning
 */

import { useState } from 'react';
import { Bot, ChevronRight, ChevronLeft, AlertTriangle, CheckCircle2, AlertCircle, Sparkles, TrendingUp, Loader2 } from 'lucide-react';

export function AIAssistantSidebar({ project, analysisResults, onRunFullAnalysis, isAnalyzing = false }) {
  const [isExpanded, setIsExpanded] = useState(true);

  // If no analysis results yet, show minimal state
  if (!analysisResults && !project) {
    return null;
  }

  // Get score badge color
  const getScoreBadgeColor = (score) => {
    if (score >= 80) return 'bg-green-100 text-green-800 border-green-300';
    if (score >= 50) return 'bg-yellow-100 text-yellow-800 border-yellow-300';
    return 'bg-red-100 text-red-800 border-red-300';
  };

  // Get score label
  const getScoreLabel = (score) => {
    if (score >= 80) return 'Отлично';
    if (score >= 50) return 'Хорошо';
    return 'Требует улучшения';
  };

  return (
    <div
      className={`fixed right-0 top-0 h-screen bg-white shadow-2xl transition-all duration-300 z-40 flex ${
        isExpanded ? 'w-80' : 'w-12'
      }`}
    >
      {/* Toggle button */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-full bg-white shadow-lg rounded-l-lg p-2 hover:bg-gray-50 transition"
        aria-label={isExpanded ? 'Скрыть панель' : 'Показать панель'}
      >
        {isExpanded ? (
          <ChevronRight className="w-5 h-5 text-gray-600" />
        ) : (
          <ChevronLeft className="w-5 h-5 text-gray-600" />
        )}
      </button>

      {/* Sidebar content */}
      {isExpanded && (
        <div className="flex-1 overflow-y-auto p-6">
          {/* Header */}
          <div className="flex items-center gap-3 mb-6 pb-4 border-b">
            <div className="p-2 bg-gradient-to-br from-purple-100 to-blue-100 rounded-lg">
              <Bot className="w-6 h-6 text-purple-600" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-gray-900">AI Assistant</h2>
              <p className="text-xs text-gray-500">Анализ и рекомендации</p>
            </div>
          </div>

          {/* Analysis Summary */}
          {!analysisResults && (
            <div className="mb-6">
              <div className="p-4 bg-gradient-to-br from-purple-50 to-blue-50 border border-purple-200 rounded-lg text-center">
                {isAnalyzing ? (
                  <>
                    <Loader2 className="w-8 h-8 mx-auto mb-2 text-purple-600 animate-spin" />
                    <p className="text-sm text-gray-700 font-medium mb-1">Анализируем карту...</p>
                    <p className="text-xs text-gray-600">
                      Проверяем качество и ищем проблемы
                    </p>
                  </>
                ) : (
                  <>
                    <div className="text-4xl mb-2">🔍</div>
                    <p className="text-sm text-gray-700 font-medium mb-1">Анализ не запущен</p>
                    <p className="text-xs text-gray-600">
                      Нажмите "Полный анализ" для проверки карты
                    </p>
                  </>
                )}
              </div>
            </div>
          )}

          {analysisResults && (
            <div className="mb-6">
              <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
                <Sparkles className="w-4 h-4 text-purple-600" />
                Результаты анализа
              </h3>

              {/* Score */}
              <div className="mb-4 p-3 rounded-lg border bg-gray-50">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs text-gray-600">Оценка качества</span>
                  <span
                    className={`text-xl font-bold px-3 py-1 rounded-full border ${getScoreBadgeColor(
                      analysisResults.score
                    )}`}
                  >
                    {analysisResults.score}/100
                  </span>
                </div>
                <p className="text-xs text-gray-500">{getScoreLabel(analysisResults.score)}</p>
              </div>

              {/* Duplicates */}
              {analysisResults.duplicates > 0 && (
                <div className="mb-3 p-3 rounded-lg bg-yellow-50 border border-yellow-200">
                  <div className="flex items-start gap-2">
                    <AlertTriangle className="w-4 h-4 text-yellow-600 mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-yellow-900">
                        Найдено дубликатов: {analysisResults.duplicates}
                      </p>
                      <p className="text-xs text-yellow-700 mt-1">
                        Рекомендуется объединить или удалить похожие истории
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Similar stories */}
              {analysisResults.similar > 0 && (
                <div className="mb-3 p-3 rounded-lg bg-blue-50 border border-blue-200">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-blue-600 mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-blue-900">
                        Похожих историй: {analysisResults.similar}
                      </p>
                      <p className="text-xs text-blue-700 mt-1">
                        Проверьте на возможное дублирование
                      </p>
                    </div>
                  </div>
                </div>
              )}

              {/* Issues */}
              {analysisResults.totalIssues > 0 && (
                <div className="mb-3 p-3 rounded-lg bg-orange-50 border border-orange-200">
                  <div className="flex items-start gap-2">
                    <AlertCircle className="w-4 h-4 text-orange-600 mt-0.5 flex-shrink-0" />
                    <div className="flex-1">
                      <p className="text-sm font-medium text-orange-900">
                        Проблем найдено: {analysisResults.totalIssues}
                      </p>
                      {analysisResults.issues && analysisResults.issues.length > 0 && (
                        <ul className="text-xs text-orange-700 mt-2 space-y-1">
                          {analysisResults.issues.slice(0, 3).map((issue, idx) => (
                            <li key={idx} className="flex items-start gap-1">
                              <span className="text-orange-500">•</span>
                              <span>{issue}</span>
                            </li>
                          ))}
                          {analysisResults.totalIssues > 3 && (
                            <li className="text-orange-600 font-medium">
                              +{analysisResults.totalIssues - 3} еще...
                            </li>
                          )}
                        </ul>
                      )}
                    </div>
                  </div>
                </div>
              )}

              {/* Perfect score */}
              {analysisResults.score >= 80 &&
                analysisResults.duplicates === 0 &&
                analysisResults.totalIssues === 0 && (
                  <div className="mb-3 p-3 rounded-lg bg-green-50 border border-green-200">
                    <div className="flex items-start gap-2">
                      <CheckCircle2 className="w-4 h-4 text-green-600 mt-0.5 flex-shrink-0" />
                      <div className="flex-1">
                        <p className="text-sm font-medium text-green-900">Отличная работа!</p>
                        <p className="text-xs text-green-700 mt-1">
                          Карта готова к использованию
                        </p>
                      </div>
                    </div>
                  </div>
                )}
            </div>
          )}

          {/* Recommendations */}
          <div className="mb-6">
            <h3 className="text-sm font-semibold text-gray-700 mb-3 flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-blue-600" />
              Рекомендации
            </h3>

            <div className="space-y-2">
              {analysisResults?.score < 80 && (
                <div className="text-xs text-gray-600 p-2 bg-gray-50 rounded border border-gray-200">
                  <span className="text-purple-600 font-medium">💡 Совет:</span> Добавьте детальные
                  критерии приемки к историям
                </div>
              )}

              {analysisResults?.duplicates > 0 && (
                <div className="text-xs text-gray-600 p-2 bg-gray-50 rounded border border-gray-200">
                  <span className="text-purple-600 font-medium">💡 Совет:</span> Объедините
                  дублирующиеся истории в одну
                </div>
              )}

              {project && (
                <div className="text-xs text-gray-600 p-2 bg-gray-50 rounded border border-gray-200">
                  <span className="text-purple-600 font-medium">💡 Совет:</span> Проверьте баланс
                  между MVP и Release 1
                </div>
              )}

              <div className="text-xs text-gray-600 p-2 bg-gray-50 rounded border border-gray-200">
                <span className="text-purple-600 font-medium">💡 Совет:</span> Используйте
                drag-and-drop для приоритизации
              </div>
            </div>
          </div>

          {/* Quick Actions */}
          <div>
            <h3 className="text-sm font-semibold text-gray-700 mb-3">Быстрые действия</h3>

            <div className="space-y-2">
              {onRunFullAnalysis && (
                <button
                  onClick={onRunFullAnalysis}
                  disabled={isAnalyzing}
                  className="w-full px-4 py-2 bg-gradient-to-r from-purple-600 to-blue-600 text-white text-sm font-medium rounded-lg hover:from-purple-700 hover:to-blue-700 transition shadow-sm disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                >
                  {isAnalyzing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Анализируем...</span>
                    </>
                  ) : (
                    <span>Полный анализ</span>
                  )}
                </button>
              )}

              <button
                disabled
                className="w-full px-4 py-2 border border-gray-300 text-gray-400 text-sm font-medium rounded-lg cursor-not-allowed"
              >
                Экспорт в Jira (скоро)
              </button>

              <button
                disabled
                className="w-full px-4 py-2 border border-gray-300 text-gray-400 text-sm font-medium rounded-lg cursor-not-allowed"
              >
                Экспорт в FigJam (скоро)
              </button>
            </div>
          </div>

          {/* Footer info */}
          <div className="mt-8 pt-4 border-t">
            <p className="text-xs text-gray-500 text-center">
              Анализ обновляется автоматически при изменении карты
            </p>
          </div>
        </div>
      )}

      {/* Collapsed state - icon only */}
      {!isExpanded && (
        <div className="flex flex-col items-center justify-center py-6">
          <Bot className="w-6 h-6 text-purple-600 mb-2" />
          <div className="transform -rotate-90 whitespace-nowrap text-xs font-medium text-gray-600">
            AI Assistant
          </div>
        </div>
      )}
    </div>
  );
}

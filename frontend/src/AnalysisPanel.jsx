import { useState } from 'react';
import api from './api';

/**
 * Панель анализа User Story Map
 * 
 * Включает:
 * - Валидацию структуры карты
 * - Анализ схожести историй (поиск дубликатов)
 * - Полный отчет
 */
function AnalysisPanel({ projectId, isOpen, onClose }) {
  const [activeTab, setActiveTab] = useState('full'); // 'full', 'validation', 'similarity'
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [analysisResult, setAnalysisResult] = useState(null);

  const runAnalysis = async (type) => {
    setLoading(true);
    setError(null);
    setActiveTab(type);

    try {
      let response;
      if (type === 'full') {
        response = await api.post(`/project/${projectId}/analyze/full`, {
          include_ai_conflicts: false,
          similarity_threshold: 0.7,
          duplicate_threshold: 0.9
        });
      } else if (type === 'validation') {
        response = await api.get(`/project/${projectId}/validate`);
      } else if (type === 'similarity') {
        response = await api.get(`/project/${projectId}/analyze/similarity`);
      }
      
      setAnalysisResult({ type, data: response.data });
    } catch (err) {
      console.error('Analysis error:', err);
      setError(err.response?.data?.detail || 'Ошибка при анализе');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-4xl max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white px-6 py-4 flex justify-between items-center">
          <div>
            <h2 className="text-xl font-bold">📊 Анализ карты</h2>
            <p className="text-indigo-200 text-sm">Проверка качества и поиск проблем</p>
          </div>
          <button 
            onClick={onClose}
            className="text-white/80 hover:text-white text-2xl"
          >
            ✕
          </button>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 bg-gray-50">
          <TabButton 
            active={activeTab === 'full'} 
            onClick={() => runAnalysis('full')}
            disabled={loading}
          >
            🎯 Полный анализ
          </TabButton>
          <TabButton 
            active={activeTab === 'validation'} 
            onClick={() => runAnalysis('validation')}
            disabled={loading}
          >
            ✅ Валидация
          </TabButton>
          <TabButton 
            active={activeTab === 'similarity'} 
            onClick={() => runAnalysis('similarity')}
            disabled={loading}
          >
            🔍 Схожесть
          </TabButton>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto p-6">
          {loading && (
            <div className="flex flex-col items-center justify-center py-12">
              <div className="animate-spin rounded-full h-12 w-12 border-4 border-indigo-500 border-t-transparent mb-4"></div>
              <p className="text-gray-500">Анализируем карту...</p>
            </div>
          )}

          {error && (
            <div className="bg-red-50 border border-red-200 text-red-700 px-4 py-3 rounded-lg">
              <p className="font-medium">Ошибка</p>
              <p className="text-sm">{error}</p>
            </div>
          )}

          {!loading && !error && !analysisResult && (
            <div className="text-center py-12">
              <div className="text-6xl mb-4">📊</div>
              <h3 className="text-lg font-medium text-gray-700 mb-2">
                Выберите тип анализа
              </h3>
              <p className="text-gray-500">
                Нажмите на одну из вкладок выше, чтобы начать анализ карты
              </p>
            </div>
          )}

          {!loading && !error && analysisResult && (
            <>
              {analysisResult.type === 'full' && (
                <FullAnalysisResult data={analysisResult.data} />
              )}
              {analysisResult.type === 'validation' && (
                <ValidationResult data={analysisResult.data} />
              )}
              {analysisResult.type === 'similarity' && (
                <SimilarityResult data={analysisResult.data} />
              )}
            </>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-gray-200 px-6 py-4 bg-gray-50 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition"
          >
            Закрыть
          </button>
        </div>
      </div>
    </div>
  );
}

function TabButton({ active, onClick, disabled, children }) {
  return (
    <button
      onClick={onClick}
      disabled={disabled}
      className={`px-6 py-3 text-sm font-medium transition ${
        active 
          ? 'text-indigo-600 border-b-2 border-indigo-600 bg-white' 
          : 'text-gray-500 hover:text-gray-700'
      } ${disabled ? 'opacity-50 cursor-not-allowed' : ''}`}
    >
      {children}
    </button>
  );
}

function ScoreBadge({ score }) {
  let colorClass, label;
  
  if (score >= 90) {
    colorClass = 'bg-green-100 text-green-700 border-green-200';
    label = 'Отлично';
  } else if (score >= 70) {
    colorClass = 'bg-blue-100 text-blue-700 border-blue-200';
    label = 'Хорошо';
  } else if (score >= 50) {
    colorClass = 'bg-yellow-100 text-yellow-700 border-yellow-200';
    label = 'Удовлетворительно';
  } else {
    colorClass = 'bg-red-100 text-red-700 border-red-200';
    label = 'Требует улучшения';
  }

  return (
    <div className={`inline-flex items-center gap-2 px-4 py-2 rounded-full border ${colorClass}`}>
      <span className="text-2xl font-bold">{score}</span>
      <span className="text-sm">/100 • {label}</span>
    </div>
  );
}

function FullAnalysisResult({ data }) {
  return (
    <div className="space-y-6">
      {/* Summary */}
      <div className="bg-gradient-to-r from-indigo-50 to-purple-50 rounded-xl p-6 border border-indigo-100">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-gray-800">
            📈 Общая оценка: {data.project_name}
          </h3>
          <ScoreBadge score={data.overall_score} />
        </div>
        <p className="text-gray-600">{data.summary}</p>
      </div>

      {/* Validation Section */}
      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
          <h4 className="font-medium text-gray-700">✅ Валидация структуры</h4>
        </div>
        <div className="p-4">
          <ValidationResult data={data.validation} compact />
        </div>
      </div>

      {/* Similarity Section */}
      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
          <h4 className="font-medium text-gray-700">🔍 Анализ схожести</h4>
        </div>
        <div className="p-4">
          <SimilarityResult data={data.similarity} compact />
        </div>
      </div>
    </div>
  );
}

function ValidationResult({ data, compact = false }) {
  const severityColors = {
    error: 'bg-red-50 border-red-200 text-red-700',
    warning: 'bg-yellow-50 border-yellow-200 text-yellow-700',
    info: 'bg-blue-50 border-blue-200 text-blue-600'
  };

  const severityIcons = {
    error: '❌',
    warning: '⚠️',
    info: 'ℹ️'
  };

  // Группируем проблемы по severity
  const groupedIssues = {
    error: data.issues?.filter(i => i.severity === 'error') || [],
    warning: data.issues?.filter(i => i.severity === 'warning') || [],
    info: data.issues?.filter(i => i.severity === 'info') || []
  };

  return (
    <div className={compact ? 'space-y-3' : 'space-y-6'}>
      {/* Score и статус */}
      {!compact && (
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <span className={`text-2xl ${data.is_valid ? 'text-green-500' : 'text-red-500'}`}>
              {data.is_valid ? '✅' : '❌'}
            </span>
            <span className="font-medium text-gray-700">
              {data.is_valid ? 'Карта валидна' : 'Найдены проблемы'}
            </span>
          </div>
          <ScoreBadge score={data.score} />
        </div>
      )}

      {/* Статистика */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatCard label="Историй" value={data.stats?.total_stories || 0} icon="📝" />
        <StatCard label="С описанием" value={data.stats?.stories_with_description || 0} icon="📄" />
        <StatCard label="С критериями" value={data.stats?.stories_with_criteria || 0} icon="✓" />
        <StatCard label="Активностей" value={data.stats?.total_activities || 0} icon="🎯" />
      </div>

      {/* Проблемы */}
      {data.issues?.length > 0 && (
        <div className="space-y-2">
          <h5 className="font-medium text-gray-700 text-sm">
            Найденные проблемы ({data.issues.length})
          </h5>
          
          {['error', 'warning', 'info'].map(severity => (
            groupedIssues[severity].length > 0 && (
              <div key={severity} className="space-y-1">
                {groupedIssues[severity].slice(0, compact ? 3 : 10).map((issue, idx) => (
                  <div 
                    key={idx}
                    className={`px-3 py-2 rounded-lg border text-sm ${severityColors[severity]}`}
                  >
                    <span className="mr-2">{severityIcons[severity]}</span>
                    {issue.message}
                  </div>
                ))}
                {compact && groupedIssues[severity].length > 3 && (
                  <p className="text-xs text-gray-500 pl-2">
                    ...и ещё {groupedIssues[severity].length - 3} {severity === 'warning' ? 'предупреждений' : 'записей'}
                  </p>
                )}
              </div>
            )
          ))}
        </div>
      )}

      {/* Рекомендации */}
      {data.recommendations?.length > 0 && !compact && (
        <div className="bg-indigo-50 rounded-lg p-4 border border-indigo-100">
          <h5 className="font-medium text-indigo-800 mb-2">💡 Рекомендации</h5>
          <ul className="space-y-1">
            {data.recommendations.map((rec, idx) => (
              <li key={idx} className="text-sm text-indigo-700">
                • {rec}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function SimilarityResult({ data, compact = false }) {
  const hasDuplicates = data.similar_groups?.some(g => g.group_type === 'duplicate');
  const hasSimilar = data.similar_groups?.some(g => g.group_type === 'similar');

  return (
    <div className={compact ? 'space-y-3' : 'space-y-6'}>
      {/* Статистика */}
      <div className="grid grid-cols-3 gap-3">
        <StatCard 
          label="Всего историй" 
          value={data.stats?.total_stories || 0} 
          icon="📝" 
        />
        <StatCard 
          label="Дубликатов" 
          value={data.stats?.duplicates_found || 0} 
          icon="🔄" 
          highlight={data.stats?.duplicates_found > 0 ? 'warning' : null}
        />
        <StatCard 
          label="Похожих групп" 
          value={data.stats?.similar_groups_found || 0} 
          icon="🔗" 
        />
      </div>

      {/* Сообщение если всё ок */}
      {!hasDuplicates && !hasSimilar && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-4 text-center">
          <span className="text-2xl">✅</span>
          <p className="text-green-700 mt-2">Дубликатов и похожих историй не найдено</p>
        </div>
      )}

      {/* Группы похожих историй */}
      {data.similar_groups?.length > 0 && (
        <div className="space-y-3">
          {data.similar_groups.slice(0, compact ? 2 : 10).map((group, idx) => (
            <SimilarityGroup key={idx} group={group} />
          ))}
          
          {compact && data.similar_groups.length > 2 && (
            <p className="text-sm text-gray-500 text-center">
              ...и ещё {data.similar_groups.length - 2} групп
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function SimilarityGroup({ group }) {
  const isDuplicate = group.group_type === 'duplicate';
  
  return (
    <div className={`border rounded-lg overflow-hidden ${
      isDuplicate ? 'border-red-200 bg-red-50' : 'border-yellow-200 bg-yellow-50'
    }`}>
      <div className={`px-4 py-2 flex items-center gap-2 ${
        isDuplicate ? 'bg-red-100' : 'bg-yellow-100'
      }`}>
        <span>{isDuplicate ? '🔄' : '🔗'}</span>
        <span className={`text-sm font-medium ${isDuplicate ? 'text-red-700' : 'text-yellow-700'}`}>
          {isDuplicate ? 'Возможный дубликат' : 'Похожие истории'}
        </span>
        <span className="text-xs text-gray-500">
          ({group.stories.length} историй)
        </span>
      </div>
      
      <div className="p-3 space-y-2">
        {group.stories.map((story, idx) => (
          <div 
            key={story.id}
            className="bg-white rounded px-3 py-2 border border-gray-200 flex justify-between items-center"
          >
            <div>
              <p className="font-medium text-gray-800 text-sm">{story.title}</p>
              <p className="text-xs text-gray-500">
                {story.activity_title} → {story.task_title}
              </p>
            </div>
            <span className={`text-xs px-2 py-1 rounded ${
              story.similarity >= 0.9 
                ? 'bg-red-100 text-red-600' 
                : 'bg-yellow-100 text-yellow-600'
            }`}>
              {Math.round(story.similarity * 100)}%
            </span>
          </div>
        ))}
        
        <p className="text-xs text-gray-600 italic mt-2">
          💡 {group.recommendation}
        </p>
      </div>
    </div>
  );
}

function StatCard({ label, value, icon, highlight = null }) {
  let bgClass = 'bg-gray-50';
  if (highlight === 'warning') bgClass = 'bg-yellow-50';
  if (highlight === 'error') bgClass = 'bg-red-50';

  return (
    <div className={`${bgClass} rounded-lg p-3 text-center border border-gray-200`}>
      <div className="text-xl mb-1">{icon}</div>
      <div className="text-2xl font-bold text-gray-800">{value}</div>
      <div className="text-xs text-gray-500">{label}</div>
    </div>
  );
}

export default AnalysisPanel;


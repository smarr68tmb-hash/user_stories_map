import { useState } from 'react';

/**
 * Компонент для показа улучшенных требований перед генерацией карты
 * Two-Stage AI Processing: Stage 1 Preview
 */
function EnhancementPreview({ 
  originalText, 
  enhancementData, 
  isOpen, 
  onClose, 
  onUseOriginal, 
  onUseEnhanced, 
  onEdit 
}) {
  const [editedText, setEditedText] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  
  if (!isOpen || !enhancementData) return null;
  
  const { 
    enhanced_text, 
    added_aspects = [], 
    missing_info = [], 
    detected_product_type,
    detected_roles = [],
    confidence = 1.0,
    fallback = false
  } = enhancementData;
  
  // Определяем цвет и текст для confidence
  const getConfidenceStyle = () => {
    if (confidence >= 0.9) return { color: 'text-green-600', bg: 'bg-green-100', label: 'Высокая' };
    if (confidence >= 0.7) return { color: 'text-yellow-600', bg: 'bg-yellow-100', label: 'Средняя' };
    return { color: 'text-orange-600', bg: 'bg-orange-100', label: 'Низкая' };
  };
  
  const confidenceStyle = getConfidenceStyle();
  
  const handleStartEdit = () => {
    setEditedText(enhanced_text);
    setIsEditing(true);
  };
  
  const handleSaveEdit = () => {
    if (editedText.trim()) {
      onEdit(editedText);
    }
    setIsEditing(false);
  };
  
  const handleCancelEdit = () => {
    setEditedText('');
    setIsEditing(false);
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-2xl shadow-2xl max-w-4xl w-full max-h-[90vh] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="bg-gradient-to-r from-indigo-600 to-purple-600 text-white p-6">
          <div className="flex justify-between items-start">
            <div>
              <h2 className="text-2xl font-bold flex items-center gap-3">
                <span className="text-3xl">✨</span>
                Улучшение требований
              </h2>
              <p className="text-indigo-100 mt-1 text-sm">
                AI проанализировал ваши требования и предлагает улучшения
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-white/80 hover:text-white text-2xl font-light transition"
              aria-label="Закрыть"
            >
              ×
            </button>
          </div>
          
          {/* Confidence и метаданные */}
          <div className="flex flex-wrap gap-3 mt-4">
            <span className={`px-3 py-1 rounded-full text-sm font-medium ${confidenceStyle.bg} ${confidenceStyle.color}`}>
              Уверенность: {confidenceStyle.label} ({Math.round(confidence * 100)}%)
            </span>
            {detected_product_type && detected_product_type !== 'unknown' && (
              <span className="px-3 py-1 rounded-full text-sm font-medium bg-white/20 text-white">
                📱 {detected_product_type}
              </span>
            )}
            {detected_roles.length > 0 && (
              <span className="px-3 py-1 rounded-full text-sm font-medium bg-white/20 text-white">
                👥 {detected_roles.length} {detected_roles.length === 1 ? 'роль' : 'ролей'}
              </span>
            )}
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-6">
          {fallback && (
            <div className="mb-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg text-yellow-800">
              <p className="flex items-center gap-2">
                <span>⚠️</span>
                <span>AI не смог улучшить требования. Используется оригинальный текст.</span>
              </p>
            </div>
          )}
          
          {/* Сравнение текстов */}
          <div className="grid md:grid-cols-2 gap-6 mb-6">
            {/* Оригинал */}
            <div className="space-y-2">
              <h3 className="font-semibold text-gray-700 flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-gray-400"></span>
                Ваш текст
              </h3>
              <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg text-sm text-gray-700 whitespace-pre-wrap min-h-[150px]">
                {originalText}
              </div>
            </div>
            
            {/* Улучшенный */}
            <div className="space-y-2">
              <h3 className="font-semibold text-gray-700 flex items-center gap-2">
                <span className="w-3 h-3 rounded-full bg-indigo-500"></span>
                Улучшенный текст
                {!fallback && <span className="text-xs text-indigo-500 font-normal">(рекомендуется)</span>}
              </h3>
              
              {isEditing ? (
                <div className="space-y-2">
                  <textarea
                    value={editedText}
                    onChange={(e) => setEditedText(e.target.value)}
                    className="w-full p-4 border-2 border-indigo-300 rounded-lg text-sm text-gray-700 min-h-[150px] resize-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 outline-none"
                    placeholder="Редактируйте текст..."
                  />
                  <div className="flex gap-2">
                    <button
                      onClick={handleSaveEdit}
                      className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 transition"
                      aria-label="Сохранить редактированный текст"
                    >
                      Использовать этот текст
                    </button>
                    <button
                      onClick={handleCancelEdit}
                      className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg text-sm font-medium hover:bg-gray-300 transition"
                      aria-label="Отменить редактирование"
                    >
                      Отмена
                    </button>
                  </div>
                </div>
              ) : (
                <div className="p-4 bg-indigo-50 border-2 border-indigo-200 rounded-lg text-sm text-gray-700 whitespace-pre-wrap min-h-[150px]">
                  {enhanced_text}
                </div>
              )}
            </div>
          </div>
          
          {/* Что добавлено */}
          {added_aspects.length > 0 && (
            <div className="mb-4">
              <h4 className="font-medium text-gray-700 mb-2 flex items-center gap-2">
                <span className="text-green-500">✓</span>
                Добавлено:
              </h4>
              <div className="flex flex-wrap gap-2">
                {added_aspects.map((aspect, idx) => (
                  <span 
                    key={idx} 
                    className="px-3 py-1 bg-green-50 text-green-700 text-sm rounded-lg border border-green-200"
                  >
                    {aspect}
                  </span>
                ))}
              </div>
            </div>
          )}
          
          {/* Что рекомендуется уточнить */}
          {missing_info.length > 0 && (
            <div className="mb-4">
              <h4 className="font-medium text-gray-700 mb-2 flex items-center gap-2">
                <span className="text-amber-500">💡</span>
                Рекомендуется уточнить:
              </h4>
              <div className="flex flex-wrap gap-2">
                {missing_info.map((info, idx) => (
                  <span 
                    key={idx} 
                    className="px-3 py-1 bg-amber-50 text-amber-700 text-sm rounded-lg border border-amber-200"
                  >
                    {info}
                  </span>
                ))}
              </div>
            </div>
          )}
          
          {/* Выявленные роли */}
          {detected_roles.length > 0 && (
            <div className="mb-4">
              <h4 className="font-medium text-gray-700 mb-2 flex items-center gap-2">
                <span className="text-blue-500">👥</span>
                Выявленные роли:
              </h4>
              <div className="flex flex-wrap gap-2">
                {detected_roles.map((role, idx) => (
                  <span 
                    key={idx} 
                    className="px-3 py-1 bg-blue-50 text-blue-700 text-sm rounded-lg border border-blue-200"
                  >
                    {role}
                  </span>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Footer с кнопками действий */}
        <div className="border-t border-gray-200 p-6 bg-gray-50">
          <div className="flex flex-col sm:flex-row gap-3">
            <button
              onClick={onUseOriginal}
              className="flex-1 px-6 py-3 border-2 border-gray-300 text-gray-700 rounded-xl font-medium hover:bg-gray-100 hover:border-gray-400 transition"
              aria-label="Использовать оригинальный текст без улучшений"
            >
              Использовать мой текст
            </button>

            {!isEditing && (
              <button
                onClick={handleStartEdit}
                className="flex-1 px-6 py-3 border-2 border-indigo-300 text-indigo-700 rounded-xl font-medium hover:bg-indigo-50 hover:border-indigo-400 transition"
                aria-label="Редактировать улучшенный текст"
              >
                ✏️ Редактировать
              </button>
            )}

            <button
              onClick={() => onUseEnhanced(enhanced_text)}
              className="flex-1 px-6 py-3 bg-gradient-to-r from-indigo-600 to-purple-600 text-white rounded-xl font-semibold hover:from-indigo-700 hover:to-purple-700 transition shadow-lg shadow-indigo-200"
              aria-label="Использовать улучшенный текст от AI"
            >
              ✨ Использовать улучшенный
            </button>
          </div>
          
          <p className="text-xs text-gray-500 text-center mt-4">
            💡 Tip: Качественные требования = качественная карта историй
          </p>
        </div>
      </div>
    </div>
  );
}

export default EnhancementPreview;


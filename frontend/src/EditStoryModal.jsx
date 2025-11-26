import { useState, useEffect } from 'react';

function EditStoryModal({ story, releases, isOpen, onClose, onSave, onDelete }) {
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editReleaseId, setEditReleaseId] = useState(null);
  const [editAC, setEditAC] = useState('');
  const [saving, setSaving] = useState(false);

  // Синхронизация с story при открытии
  useEffect(() => {
    if (story && isOpen) {
      setEditTitle(story.title || '');
      setEditDescription(story.description || '');
      setEditReleaseId(story.release_id);
      setEditAC((story.acceptance_criteria || []).join('\n'));
    }
  }, [story, isOpen]);

  // Получаем название текущего release для отображения
  const currentRelease = releases?.find(r => r.id === editReleaseId);

  const handleSave = async () => {
    if (!editTitle.trim()) return;
    
    setSaving(true);
    try {
      await onSave({
        title: editTitle.trim(),
        description: editDescription.trim(),
        release_id: editReleaseId,
        priority: currentRelease?.title || 'Later', // Синхронизируем priority с release
        acceptance_criteria: editAC.split('\n').filter(l => l.trim())
      });
      onClose();
    } catch (error) {
      console.error('Error saving story:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm('Удалить эту карточку? Это действие нельзя отменить.')) return;
    
    setSaving(true);
    try {
      await onDelete();
      onClose();
    } catch (error) {
      console.error('Error deleting story:', error);
    } finally {
      setSaving(false);
    }
  };

  // Закрытие по Escape
  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        onClose();
      }
    };
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen || !story) return null;

  // Цвета для release/priority
  const getReleaseStyle = (releaseTitle, isSelected) => {
    const baseStyles = 'p-3 rounded-lg border-2 font-medium transition';
    
    if (!isSelected) {
      return `${baseStyles} border-gray-200 bg-white text-gray-600 hover:border-gray-300`;
    }
    
    switch (releaseTitle) {
      case 'MVP':
        return `${baseStyles} border-red-500 bg-red-50 text-red-700`;
      case 'Release 1':
        return `${baseStyles} border-orange-500 bg-orange-50 text-orange-700`;
      default:
        return `${baseStyles} border-gray-500 bg-gray-50 text-gray-700`;
    }
  };

  return (
    <div 
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg overflow-hidden">
        {/* Header */}
        <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-4">
          <div className="flex justify-between items-center">
            <h2 className="text-xl font-bold">Редактирование истории</h2>
            <button
              onClick={onClose}
              className="text-white/80 hover:text-white text-2xl font-light transition"
              disabled={saving}
            >
              ×
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="p-6 space-y-5">
          {/* Title */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Название истории *
            </label>
            <input
              type="text"
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition"
              placeholder="Как пользователь, я хочу..."
              autoFocus
              disabled={saving}
            />
          </div>

          {/* Description */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Описание
            </label>
            <textarea
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none transition"
              rows="3"
              placeholder="Подробное описание функциональности..."
              disabled={saving}
            />
          </div>

          {/* Release/Priority - теперь выбирает строку куда переместить */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Релиз
              <span className="text-gray-400 font-normal ml-2">(строка на карте)</span>
            </label>
            <div className="grid grid-cols-3 gap-3">
              {releases?.map((release) => (
                <button
                  key={release.id}
                  type="button"
                  onClick={() => setEditReleaseId(release.id)}
                  disabled={saving}
                  className={getReleaseStyle(release.title, editReleaseId === release.id)}
                >
                  {release.title}
                </button>
              ))}
            </div>
            {editReleaseId !== story.release_id && (
              <p className="text-xs text-orange-600 mt-2 flex items-center gap-1">
                <span>⚠️</span>
                <span>Карточка будет перемещена в строку "{currentRelease?.title}"</span>
              </p>
            )}
          </div>

          {/* Acceptance Criteria */}
          <div>
            <label className="block text-sm font-semibold text-gray-700 mb-2">
              Acceptance Criteria
              <span className="text-gray-400 font-normal ml-2">(каждый критерий с новой строки)</span>
            </label>
            <textarea
              value={editAC}
              onChange={(e) => setEditAC(e.target.value)}
              className="w-full p-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none resize-none transition font-mono text-sm"
              rows="4"
              placeholder="• Пользователь может войти с email и паролем&#10;• Показывается сообщение об ошибке при неверных данных&#10;• После входа перенаправляется на главную"
              disabled={saving}
            />
            {editAC.trim() && (
              <p className="text-xs text-gray-500 mt-1">
                {editAC.split('\n').filter(l => l.trim()).length} критериев
              </p>
            )}
          </div>
        </div>

        {/* Footer */}
        <div className="bg-gray-50 px-6 py-4 flex items-center justify-between border-t">
          <button
            onClick={handleDelete}
            disabled={saving}
            className="text-red-600 hover:text-red-700 hover:bg-red-50 px-4 py-2 rounded-lg font-medium transition disabled:opacity-50"
          >
            Удалить
          </button>
          
          <div className="flex gap-3">
            <button
              onClick={onClose}
              disabled={saving}
              className="px-5 py-2 rounded-lg font-medium text-gray-700 bg-gray-200 hover:bg-gray-300 transition disabled:opacity-50"
            >
              Отмена
            </button>
            <button
              onClick={handleSave}
              disabled={saving || !editTitle.trim()}
              className="px-5 py-2 rounded-lg font-medium text-white bg-blue-600 hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              {saving ? (
                <>
                  <div className="animate-spin rounded-full h-4 w-4 border-2 border-white border-t-transparent"></div>
                  <span>Сохранение...</span>
                </>
              ) : (
                'Сохранить'
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default EditStoryModal;

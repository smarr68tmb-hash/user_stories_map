import { useState, useEffect, useRef } from 'react';
import { Sparkles } from 'lucide-react';
import ConfirmDialog from './components/common/ConfirmDialog';
import AutoResizeTextarea from './components/common/AutoResizeTextarea.jsx';
import AIAssistant from './AIAssistant';
import useFocusTrap from './hooks/useFocusTrap';
import useKeyboardShortcuts from './hooks/useKeyboardShortcuts';

function EditStoryModal({ 
  story, 
  taskId, 
  releaseId, 
  releases, 
  isOpen, 
  onClose, 
  onSave, 
  onDelete,
  onStoryImproved 
}) {
  const [editTitle, setEditTitle] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [editReleaseId, setEditReleaseId] = useState(null);
  const [editStatus, setEditStatus] = useState('todo');
  const [editAC, setEditAC] = useState('');
  const [saving, setSaving] = useState(false);
  const [confirmDeleteOpen, setConfirmDeleteOpen] = useState(false);
  const [titleTouched, setTitleTouched] = useState(false);
  const [aiAssistantOpen, setAiAssistantOpen] = useState(false);
  const modalRef = useRef(null);
  useFocusTrap(modalRef, isOpen);

  // Validation
  const titleError = titleTouched && !editTitle.trim() ? 'Название обязательно' : null;
  const titleWarning = editTitle.length > 200 ? 'Рекомендуется сократить название' : null;

  // Синхронизация с story при открытии
  useEffect(() => {
    if (story && isOpen) {
      setEditTitle(story.title || '');
      setEditDescription(story.description || '');
      setEditReleaseId(story.release_id);
      setEditStatus(story.status || 'todo');
      setEditAC((story.acceptance_criteria || []).join('\n'));
      setTitleTouched(false);
      setAiAssistantOpen(false);
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
        priority: currentRelease?.title || 'Later',
        status: editStatus,
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
    setConfirmDeleteOpen(true);
  };

  const handleConfirmDelete = async () => {
    setSaving(true);
    try {
      await onDelete();
      setConfirmDeleteOpen(false);
      onClose();
    } catch (error) {
      console.error('Error deleting story:', error);
    } finally {
      setSaving(false);
    }
  };

  const handleOpenAI = () => {
    setAiAssistantOpen(true);
  };

  const handleCloseAI = () => {
    setAiAssistantOpen(false);
  };

  const handleStoryImproved = async () => {
    if (onStoryImproved) {
      await onStoryImproved();
    }
    // Close both modals - the updated story will be visible on the map
    setAiAssistantOpen(false);
    onClose();
  };

  // Keyboard shortcuts
  useKeyboardShortcuts([
    { key: 'Escape', handler: onClose },
    { key: 's', ctrl: true, handler: () => !saving && editTitle.trim() && handleSave() },
  ], isOpen && !confirmDeleteOpen && !aiAssistantOpen);

  if (!isOpen || !story) return null;

  // Цвета для release/priority
  const getReleaseStyle = (releaseTitle, isSelected) => {
    const baseStyles = 'px-4 py-3 rounded-lg border-2 font-medium transition-all duration-200';
    
    if (!isSelected) {
      return `${baseStyles} border-gray-200 bg-white text-gray-700 hover:border-gray-400 hover:bg-gray-50`;
    }
    
    switch (releaseTitle) {
      case 'MVP':
        return `${baseStyles} border-red-500 bg-red-50 text-red-700 shadow-sm`;
      case 'Release 1':
        return `${baseStyles} border-orange-500 bg-orange-50 text-orange-700 shadow-sm`;
      default:
        return `${baseStyles} border-gray-500 bg-gray-50 text-gray-700 shadow-sm`;
    }
  };

  return (
    <>
      <div 
        className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
        role="dialog"
        aria-modal="true"
        onClick={(e) => {
          if (e.target === e.currentTarget && !aiAssistantOpen) onClose();
        }}
      >
        <div
          ref={modalRef}
          className="bg-white rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-hidden flex flex-col"
          tabIndex={-1}
        >
          {/* Header */}
          <div className="bg-gradient-to-r from-blue-600 to-indigo-600 text-white px-6 py-5 flex-shrink-0">
            <div className="flex justify-between items-center">
              <h2 className="text-xl font-bold">Редактирование истории</h2>
              <button
                onClick={onClose}
                className="min-w-[44px] min-h-[44px] flex items-center justify-center text-white/90 hover:text-white text-2xl font-light transition rounded-lg hover:bg-white/10"
                disabled={saving}
                aria-label="Закрыть"
              >
                ×
              </button>
            </div>
          </div>

          {/* Body - scrollable */}
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
            {/* Title */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2.5">
                Название истории <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={editTitle}
                onChange={(e) => setEditTitle(e.target.value)}
                onBlur={() => setTitleTouched(true)}
                className={`w-full px-4 py-3.5 border-2 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all text-base ${
                  titleError
                    ? 'border-red-400 bg-red-50'
                    : titleWarning
                    ? 'border-orange-400 bg-orange-50'
                    : editTitle.trim()
                    ? 'border-green-400 bg-green-50/30'
                    : 'border-gray-300 bg-white'
                }`}
                placeholder="Как пользователь, я хочу..."
                autoFocus
                disabled={saving}
              />
              <div className="flex justify-between items-center mt-2">
                <div className="flex-1">
                  {titleError && <p className="text-xs text-red-600 font-medium">{titleError}</p>}
                  {!titleError && titleWarning && <p className="text-xs text-orange-600 font-medium">{titleWarning}</p>}
                </div>
                <span className={`text-xs font-medium ${editTitle.length > 200 ? 'text-orange-600' : 'text-gray-400'}`}>
                  {editTitle.length}/200
                </span>
              </div>
            </div>

            {/* Description */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2.5">
                Описание
              </label>
              <AutoResizeTextarea
                value={editDescription}
                onChange={(e) => setEditDescription(e.target.value)}
                minHeight={100}
                maxHeight={250}
                className="w-full px-4 py-3.5 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all text-base resize-none"
                placeholder="Подробное описание функциональности..."
                disabled={saving}
              />
            </div>

            {/* Release/Priority */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2.5">
                Релиз <span className="text-gray-400 font-normal text-xs">(строка на карте)</span>
              </label>
              <div className="grid grid-cols-3 gap-3">
                {releases?.map((release) => (
                  <button
                    key={release.id}
                    type="button"
                    onClick={() => setEditReleaseId(release.id)}
                    disabled={saving}
                    className={getReleaseStyle(release.title, editReleaseId === release.id)}
                    aria-label={`Переместить в релиз ${release.title}`}
                    aria-pressed={editReleaseId === release.id}
                  >
                    {release.title}
                  </button>
                ))}
              </div>
              {editReleaseId !== story.release_id && editReleaseId !== null && (
                <p className="text-xs text-orange-600 mt-2.5 flex items-center gap-1.5 font-medium">
                  <span>⚠️</span>
                  <span>
                    Карточка будет перемещена в строку &quot;{currentRelease?.title}&quot;
                  </span>
                </p>
              )}
            </div>

            {/* Status */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2.5">
                Статус
              </label>
              <div className="grid grid-cols-3 gap-3">
                <button
                  type="button"
                  onClick={() => setEditStatus('todo')}
                  disabled={saving}
                  className={`px-4 py-3.5 rounded-lg border-2 font-medium transition-all duration-200 flex items-center justify-center gap-2.5 ${
                    editStatus === 'todo'
                      ? 'border-gray-500 bg-gray-50 text-gray-700 shadow-sm'
                      : 'border-gray-200 bg-white text-gray-600 hover:border-gray-400 hover:bg-gray-50'
                  }`}
                  aria-label="Изменить статус на 'К выполнению'"
                  aria-pressed={editStatus === 'todo'}
                >
                  <span className="text-xl">○</span>
                  <span>К выполнению</span>
                </button>
                <button
                  type="button"
                  onClick={() => setEditStatus('in_progress')}
                  disabled={saving}
                  className={`px-4 py-3.5 rounded-lg border-2 font-medium transition-all duration-200 flex items-center justify-center gap-2.5 ${
                    editStatus === 'in_progress'
                      ? 'border-blue-500 bg-blue-50 text-blue-700 shadow-sm'
                      : 'border-gray-200 bg-white text-gray-600 hover:border-gray-400 hover:bg-gray-50'
                  }`}
                  aria-label="Изменить статус на 'В работе'"
                  aria-pressed={editStatus === 'in_progress'}
                >
                  <span className="text-xl">◐</span>
                  <span>В работе</span>
                </button>
                <button
                  type="button"
                  onClick={() => setEditStatus('done')}
                  disabled={saving}
                  className={`px-4 py-3.5 rounded-lg border-2 font-medium transition-all duration-200 flex items-center justify-center gap-2.5 ${
                    editStatus === 'done'
                      ? 'border-green-500 bg-green-50 text-green-700 shadow-sm'
                      : 'border-gray-200 bg-white text-gray-600 hover:border-gray-400 hover:bg-gray-50'
                  }`}
                  aria-label="Изменить статус на 'Готово'"
                  aria-pressed={editStatus === 'done'}
                >
                  <span className="text-xl">✓</span>
                  <span>Готово</span>
                </button>
              </div>
            </div>

            {/* Acceptance Criteria */}
            <div>
              <label className="block text-sm font-semibold text-gray-700 mb-2.5">
                Критерии приёмки <span className="text-gray-400 font-normal text-xs">(каждый критерий с новой строки)</span>
              </label>
              <AutoResizeTextarea
                value={editAC}
                onChange={(e) => setEditAC(e.target.value)}
                minHeight={120}
                maxHeight={300}
                className="w-full px-4 py-3.5 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500 outline-none transition-all font-mono text-sm resize-none"
                placeholder="• Пользователь может войти с email и паролем&#10;• Показывается сообщение об ошибке при неверных данных&#10;• После входа перенаправляется на главную"
                disabled={saving}
              />
              {editAC.trim() && (
                <p className="text-xs text-gray-500 mt-2 font-medium">
                  {editAC.split('\n').filter(l => l.trim()).length} критериев
                </p>
              )}
            </div>
          </div>

          {/* Footer */}
          <div className="bg-gray-50 px-6 py-4 border-t flex-shrink-0">
            <div className="flex items-center justify-between mb-3">
              <button
                onClick={handleDelete}
                disabled={saving}
                className="text-red-600 hover:text-red-700 hover:bg-red-50 px-4 py-2.5 rounded-lg font-medium transition disabled:opacity-50 disabled:cursor-not-allowed"
                aria-label="Удалить историю"
              >
                Удалить
              </button>

              {/* AI Button */}
              {taskId && releaseId && (
                <button
                  onClick={handleOpenAI}
                  disabled={saving}
                  className="px-4 py-2.5 rounded-lg font-medium transition-all duration-200 bg-gradient-to-r from-purple-500 to-indigo-500 text-white hover:from-purple-600 hover:to-indigo-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-sm"
                  aria-label="Улучшить с помощью AI"
                >
                  <Sparkles className="w-4 h-4" />
                  <span>AI Улучшение</span>
                </button>
              )}

              <div className="flex gap-3">
                <button
                  onClick={onClose}
                  disabled={saving}
                  className="px-5 py-2.5 rounded-lg font-medium text-gray-700 bg-gray-200 hover:bg-gray-300 transition disabled:opacity-50 disabled:cursor-not-allowed"
                  aria-label="Отменить изменения"
                >
                  Отмена
                </button>
                <button
                  onClick={handleSave}
                  disabled={saving || !editTitle.trim()}
                  className="px-5 py-2.5 rounded-lg font-medium text-white bg-blue-600 hover:bg-blue-700 transition disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2 shadow-sm"
                  aria-label="Сохранить изменения"
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
            <div className="text-xs text-gray-400 text-center">
              <kbd className="px-2 py-1 bg-gray-200 rounded text-gray-600 font-mono">⌘S</kbd> сохранить
              <span className="mx-2">·</span>
              <kbd className="px-2 py-1 bg-gray-200 rounded text-gray-600 font-mono">Esc</kbd> закрыть
            </div>
          </div>
        </div>
      </div>

      {/* AI Assistant Modal */}
      {taskId && releaseId && (
        <AIAssistant
          story={story}
          taskId={taskId}
          releaseId={releaseId}
          isOpen={aiAssistantOpen}
          onClose={handleCloseAI}
          onStoryImproved={handleStoryImproved}
        />
      )}

      {/* Confirm Delete Dialog */}
      <ConfirmDialog
        isOpen={confirmDeleteOpen}
        title="Удалить эту карточку?"
        description="Действие нельзя отменить. Карточка будет удалена без возможности восстановления."
        confirmText="Удалить"
        cancelText="Отмена"
        onConfirm={handleConfirmDelete}
        onCancel={() => setConfirmDeleteOpen(false)}
        loading={saving}
      />
    </>
  );
}

export default EditStoryModal;

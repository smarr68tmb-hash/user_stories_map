import { useState } from 'react';
import { CheckCircle2, Circle, AlertTriangle, Pencil, Check, X, Plus } from 'lucide-react';
import { useToast } from '../../hooks/useToast';

function EpicBreakdownView({
  epics = [],
  project,
  onGenerateEpics,
  onUpdateEpic,
  onAddStoryToEpic,
  onRemoveStoryFromEpic,
  onAcceptEpic,
  onRejectEpic,
  loading = {},
  generatingEpics = false,
}) {
  const toast = useToast();

  const [editingEpicId, setEditingEpicId] = useState(null);
  const [editedTitle, setEditedTitle] = useState('');
  const [editedDescription, setEditedDescription] = useState('');

  // Если эпиков нет, показываем кнопку генерации
  if (epics.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4">
        <div className="text-center max-w-md">
          <h2 className="text-2xl font-bold text-gray-800 mb-4">Эпики еще не созданы</h2>
          <p className="text-gray-600 mb-6">
            Создайте эпики для группировки историй вашего проекта. Это поможет лучше организовать работу.
          </p>
          <button
            onClick={onGenerateEpics}
            disabled={generatingEpics || !project?.id}
            className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium"
          >
            {generatingEpics ? 'Генерация эпиков...' : 'Сгенерировать эпики'}
          </button>
        </div>
      </div>
    );
  }

  // Вычисление прогресса эпика (сколько историй done)
  const getEpicProgress = (epic) => {
    if (!epic.stories || epic.stories.length === 0) return 0;
    const doneCount = epic.stories.filter((story) => story.status === 'done').length;
    return Math.round((doneCount / epic.stories.length) * 100);
  };

  // Начало редактирования эпика
  const handleStartEdit = (epic) => {
    setEditingEpicId(epic.id);
    setEditedTitle(epic.title);
    setEditedDescription(epic.description || '');
  };

  // Сохранение изменений эпика
  const handleSaveEdit = async () => {
    if (!editingEpicId) return;

    try {
      await onUpdateEpic(editingEpicId, {
        title: editedTitle,
        description: editedDescription || null,
      });
      setEditingEpicId(null);
      setEditedTitle('');
      setEditedDescription('');
    } catch (error) {
      console.error('Error updating epic:', error);
    }
  };

  // Отмена редактирования
  const handleCancelEdit = () => {
    setEditingEpicId(null);
    setEditedTitle('');
    setEditedDescription('');
  };

  return (
    <div className="space-y-6">
      {/* Заголовок с кнопкой генерации новых эпиков */}
      <div className="flex justify-between items-center mb-4">
        <h2 className="text-xl font-bold text-gray-800">Epic Breakdown</h2>
        <button
          onClick={onGenerateEpics}
          disabled={generatingEpics}
          className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors text-sm font-medium flex items-center gap-2"
        >
          <Plus className="w-4 h-4" />
          {generatingEpics ? 'Генерация...' : 'Сгенерировать новые'}
        </button>
      </div>

      {/* Список эпиков */}
      {epics.map((epic) => {
        const progress = getEpicProgress(epic);
        const storiesCount = epic.stories?.length || 0;
        const confidenceScore = epic.confidence_score || 0;
        const isLowConfidence = confidenceScore < 0.7;
        const isEditing = editingEpicId === epic.id;

        return (
          <div
            key={epic.id}
            className="bg-white rounded-xl shadow-md border-2 border-gray-200 hover:shadow-lg transition-shadow p-6"
          >
            {/* Заголовок эпика */}
            <div className="flex items-start justify-between mb-4">
              <div className="flex-1">
                {isEditing ? (
                  <div className="space-y-3">
                    <input
                      type="text"
                      value={editedTitle}
                      onChange={(e) => setEditedTitle(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 text-lg font-semibold"
                      placeholder="Название эпика"
                      autoFocus
                    />
                    <textarea
                      value={editedDescription}
                      onChange={(e) => setEditedDescription(e.target.value)}
                      className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 resize-none"
                      placeholder="Описание эпика (необязательно)"
                      rows="2"
                    />
                    <div className="flex gap-2">
                      <button
                        onClick={handleSaveEdit}
                        disabled={!editedTitle.trim() || loading.update?.[epic.id]}
                        className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-2 text-sm"
                      >
                        <Check className="w-4 h-4" />
                        Сохранить
                      </button>
                      <button
                        onClick={handleCancelEdit}
                        className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 transition-colors flex items-center gap-2 text-sm"
                      >
                        <X className="w-4 h-4" />
                        Отмена
                      </button>
                    </div>
                  </div>
                ) : (
                  <>
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-gray-800">{epic.title}</h3>
                      {isLowConfidence && (
                        <div className="flex items-center gap-1 px-2 py-1 bg-yellow-100 text-yellow-800 rounded-md text-xs font-medium">
                          <AlertTriangle className="w-3 h-3" />
                          Низкая уверенность
                        </div>
                      )}
                    </div>
                    {epic.description && (
                      <p className="text-sm text-gray-600 mb-3">{epic.description}</p>
                    )}
                    <div className="flex items-center gap-4 text-sm text-gray-600">
                      <span>Истории: {storiesCount}</span>
                      <span>Прогресс: {progress}%</span>
                      {confidenceScore > 0 && (
                        <span>Уверенность: {Math.round(confidenceScore * 100)}%</span>
                      )}
                    </div>
                  </>
                )}
              </div>

              {/* Кнопки действий (когда не редактируется) */}
              {!isEditing && (
                <div className="flex items-center gap-2 ml-4">
                  <button
                    onClick={() => handleStartEdit(epic)}
                    disabled={loading.update?.[epic.id]}
                    className="p-2 text-gray-600 hover:bg-gray-100 rounded-lg transition-colors"
                    title="Редактировать"
                  >
                    <Pencil className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => onAcceptEpic(epic.id)}
                    disabled={loading.accept?.[epic.id]}
                    className="p-2 text-green-600 hover:bg-green-50 rounded-lg transition-colors"
                    title="Принять эпик"
                  >
                    <Check className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => {
                      if (window.confirm('Вы уверены, что хотите отклонить этот эпик? Все истории будут отвязаны от эпика.')) {
                        onRejectEpic(epic.id);
                      }
                    }}
                    disabled={loading.reject?.[epic.id]}
                    className="p-2 text-red-600 hover:bg-red-50 rounded-lg transition-colors"
                    title="Отклонить эпик"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>

            {/* Прогресс-бар */}
            <div className="mb-4">
              <div className="w-full bg-gray-200 rounded-full h-2">
                <div
                  className="bg-blue-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            {/* Список историй */}
            {epic.stories && epic.stories.length > 0 ? (
              <div className="space-y-2">
                {epic.stories.map((story) => {
                  const isDone = story.status === 'done';
                  return (
                    <div
                      key={story.id}
                      className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg hover:bg-gray-100 transition-colors group"
                    >
                      <button
                        onClick={() => {
                          // Можно добавить функционал изменения статуса истории здесь
                          toast.info('Измените статус истории на карте');
                        }}
                        className="text-gray-400 hover:text-green-600 transition-colors"
                        title={isDone ? 'Выполнено' : 'Не выполнено'}
                      >
                        {isDone ? (
                          <CheckCircle2 className="w-5 h-5 text-green-600" />
                        ) : (
                          <Circle className="w-5 h-5" />
                        )}
                      </button>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium text-gray-800">{story.title}</div>
                        {story.description && (
                          <div className="text-xs text-gray-500 mt-1 line-clamp-2">{story.description}</div>
                        )}
                      </div>
                      <button
                        onClick={() => onRemoveStoryFromEpic(epic.id, story.id)}
                        disabled={loading.removeStory?.[`${epic.id}-${story.id}`]}
                        className="p-1 text-gray-400 hover:text-red-600 opacity-0 group-hover:opacity-100 transition-opacity"
                        title="Удалить из эпика"
                      >
                        <X className="w-4 h-4" />
                      </button>
                    </div>
                  );
                })}
              </div>
            ) : (
              <div className="text-sm text-gray-500 italic py-4">Нет историй в этом эпике</div>
            )}
          </div>
        );
      })}
    </div>
  );
}

export default EpicBreakdownView;


import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { useDroppable } from '@dnd-kit/core';
import StoryCard from './StoryCard';

function StoryCell({
  cellId,
  taskId,
  releaseId,
  stories,
  isAdding,
  draft,
  onOpenAddForm,
  onCloseAddForm,
  onUpdateDraft,
  onAddStory,
  storyLoading,
  onEditStory,
  onOpenAI,
  onStatusChange,
  isStoryHandleDisabled,
  isStoryDragDisabled,
}) {
  return (
    <DroppableCell cellId={cellId} taskId={taskId} releaseId={releaseId}>
      <SortableContext
        items={stories.map((s) => `${s.id}-${taskId}-${releaseId}`)}
        strategy={verticalListSortingStrategy}
      >
        <div className="flex flex-col gap-2 min-h-[150px]">
          {stories.map((story) => (
            <StoryCard
              key={story.id}
              story={story}
              taskId={taskId}
              releaseId={releaseId}
              onEdit={() => onEditStory(story)}
              onOpenAI={() => onOpenAI(story, taskId, releaseId)}
              onStatusChange={onStatusChange}
              dragDisabled={isStoryDragDisabled(story.id)}
              handleDisabled={isStoryHandleDisabled(story.id)}
              statusLoading={storyLoading.isChangingStatus(story.id)}
            />
          ))}

          {isAdding ? (
            <div className="bg-green-50 p-3 rounded border border-green-300">
              <input
                type="text"
                placeholder="Название истории"
                value={draft.title}
                onChange={(e) => onUpdateDraft(cellId, { title: e.target.value, error: null })}
                className="w-full mb-2 p-2 text-sm border rounded"
                autoFocus
                aria-label="Название истории"
              />
              <textarea
                placeholder="Описание (опционально)"
                value={draft.description}
                onChange={(e) => onUpdateDraft(cellId, { description: e.target.value })}
                className="w-full mb-2 p-2 text-xs border rounded resize-none"
                rows="2"
              />
              <select
                value={draft.priority}
                onChange={(e) => onUpdateDraft(cellId, { priority: e.target.value })}
                className="w-full mb-2 p-1 text-xs border rounded"
              >
                <option value="MVP">MVP</option>
                <option value="Release 1">Release 1</option>
                <option value="Later">Later</option>
              </select>
              {draft.error && (
                <p className="text-[11px] text-red-600 mb-2">{draft.error}</p>
              )}
              <div className="flex gap-2">
                <button
                  onClick={() => onAddStory(taskId, releaseId)}
                  disabled={storyLoading.isAdding(cellId)}
                  aria-busy={storyLoading.isAdding(cellId)}
                  className={`flex-1 bg-green-600 text-white text-xs py-1 px-2 rounded hover:bg-green-700 ${storyLoading.isAdding(cellId) ? 'opacity-60 cursor-not-allowed' : ''}`}
                >
                  {storyLoading.isAdding(cellId) ? 'Добавление...' : 'Добавить'}
                </button>
                <button
                  onClick={() => onCloseAddForm(cellId)}
                  className="flex-1 bg-gray-300 text-gray-700 text-xs py-1 px-2 rounded hover:bg-gray-400"
                >
                  Отмена
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={() => onOpenAddForm(cellId)}
              className="text-xs text-gray-400 hover:text-gray-600 py-2 border-2 border-dashed border-gray-300 rounded hover:border-gray-400 transition disabled:opacity-60"
              disabled={storyLoading.isAdding(cellId)}
            >
              + Добавить карточку
            </button>
          )}
        </div>
      </SortableContext>
    </DroppableCell>
  );
}

function DroppableCell({ cellId, taskId, releaseId, children }) {
  const { setNodeRef, isOver } = useDroppable({
    id: cellId,
    data: {
      type: 'cell',
      taskId,
      releaseId,
    },
  });

  return (
    <div
      ref={setNodeRef}
      className={`w-[220px] flex-shrink-0 p-2 border-r border-dashed border-gray-300 transition-colors ${
        isOver ? 'bg-blue-50 border-blue-400' : 'bg-white'
      }`}
    >
      {children}
    </div>
  );
}

export default StoryCell;


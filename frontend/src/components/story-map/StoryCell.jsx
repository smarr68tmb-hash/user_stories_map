import { useCallback, useMemo } from 'react';
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable';
import { useDroppable } from '@dnd-kit/core';
import { FixedSizeList as List } from 'react-window';
import StoryCard from './StoryCard';

const STORY_CARD_HEIGHT = 156;
const STORY_ROW_GAP = 8;
const STORY_ROW_HEIGHT = STORY_CARD_HEIGHT + STORY_ROW_GAP;
const MIN_VISIBLE_ROWS = 3;
const MAX_VISIBLE_ROWS = 6;
const VIRTUALIZATION_THRESHOLD = 12;

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
  const shouldVirtualize = stories.length >= VIRTUALIZATION_THRESHOLD;

  const listHeight = useMemo(() => {
    if (!shouldVirtualize) return 0;
    const visibleRows = Math.min(Math.max(stories.length, MIN_VISIBLE_ROWS), MAX_VISIBLE_ROWS);
    return visibleRows * STORY_ROW_HEIGHT - STORY_ROW_GAP;
  }, [shouldVirtualize, stories.length]);

  const renderStoryRow = useCallback(
    ({ index, style }) => {
      const story = stories[index];
      const rowStyle = {
        ...style,
        paddingBottom: STORY_ROW_GAP,
        width: '100%',
      };

      return (
        <div style={rowStyle}>
          <StoryCard
            story={story}
            taskId={taskId}
            releaseId={releaseId}
            onEdit={() => onEditStory(story)}
            onOpenAI={() => onOpenAI(story, taskId, releaseId)}
            onStatusChange={onStatusChange}
            dragDisabled={isStoryDragDisabled(story.id)}
            handleDisabled={isStoryHandleDisabled(story.id)}
            statusLoading={storyLoading.isChangingStatus(story.id)}
            containerStyle={{ height: STORY_CARD_HEIGHT }}
          />
        </div>
      );
    },
    [isStoryDragDisabled, isStoryHandleDisabled, onEditStory, onOpenAI, onStatusChange, releaseId, stories, storyLoading, taskId],
  );

  return (
    <DroppableCell cellId={cellId} taskId={taskId} releaseId={releaseId}>
      <SortableContext
        items={stories.map((s) => `${s.id}-${taskId}-${releaseId}`)}
        strategy={verticalListSortingStrategy}
      >
        <div className="flex flex-col gap-2 min-h-[150px]">
          {stories.length > 0 && (
            shouldVirtualize ? (
              <List
                height={listHeight}
                itemCount={stories.length}
                itemSize={STORY_ROW_HEIGHT}
                width="100%"
              >
                {renderStoryRow}
              </List>
            ) : (
              stories.map((story) => (
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
              ))
            )
          )}

          {isAdding ? (
            <div className="bg-green-50 p-3 rounded border border-green-300">
              <input
                type="text"
                placeholder="Название истории"
                value={draft.title}
                onChange={(e) => onUpdateDraft(cellId, { title: e.target.value, error: null })}
                className={`w-full mb-1 p-2 text-sm border rounded transition ${
                  draft.error
                    ? 'border-red-400 bg-red-50'
                    : draft.title && draft.title.length < 3
                    ? 'border-orange-400 bg-orange-50'
                    : draft.title && draft.title.length >= 3
                    ? 'border-green-400'
                    : 'border-gray-300'
                }`}
                autoFocus
                aria-label="Название истории"
              />
              {draft.title && draft.title.length > 0 && draft.title.length < 3 && (
                <p className="text-[11px] text-orange-600 mb-1">Минимум 3 символа</p>
              )}
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
  const { setNodeRef, isOver, active } = useDroppable({
    id: cellId,
    data: {
      type: 'cell',
      taskId,
      releaseId,
    },
  });

  // Показываем visual feedback только когда есть активный drag
  const showDropIndicator = isOver && active;

  return (
    <div
      ref={setNodeRef}
      className={`w-[220px] flex-shrink-0 p-2 border-r transition-all duration-200 ${
        showDropIndicator
          ? 'bg-blue-100 border-2 border-blue-500 border-dashed shadow-inner'
          : 'bg-white border-dashed border-gray-300'
      }`}
    >
      {showDropIndicator && (
        <div className="mb-2 py-2 border-2 border-dashed border-blue-400 rounded-lg bg-blue-50 text-center text-xs text-blue-600 font-medium animate-pulse">
          Отпустите здесь
        </div>
      )}
      {children}
    </div>
  );
}

export default StoryCell;


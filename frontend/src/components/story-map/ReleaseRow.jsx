import StoryCell from './StoryCell';
import { getStatusToken, TEXT_TOKENS } from '../../theme/tokens';

// Local tokens for release row
const RELEASE_ROW_TOKENS = {
  surface: 'bg-gray-100 border-r-2 border-gray-300',
  rowHover: 'hover:bg-gray-50',
  progressBg: 'bg-gray-200',
  progressComplete: 'bg-green-500',
  progressInProgress: 'bg-blue-500',
};

function ReleaseRow({
  release,
  activities,
  addingToCell,
  storyDrafts,
  openAddForm,
  closeAddForm,
  updateDraft,
  onAddStory,
  storyLoading,
  onEditStory,
  onOpenAI,
  onStatusChange,
  isStoryHandleDisabled,
  isStoryDragDisabled,
  progress,
  activityWidths,
  taskColumnWidth = 220,
}) {
  return (
    <div className={`flex border-b border-gray-200 min-h-[180px] transition ${RELEASE_ROW_TOKENS.rowHover}`}>
      <div className={`w-32 flex-shrink-0 p-3 font-bold flex flex-col items-center justify-center gap-2 ${RELEASE_ROW_TOKENS.surface} ${TEXT_TOKENS.secondary}`}>
        <span className="text-sm text-center">{release.title}</span>
        {progress.total > 0 && (
          <div className="w-full px-1">
            <div className={`w-full rounded-full h-1.5 overflow-hidden ${RELEASE_ROW_TOKENS.progressBg}`} aria-label="Прогресс релиза">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  progress.percent === 100 ? RELEASE_ROW_TOKENS.progressComplete : RELEASE_ROW_TOKENS.progressInProgress
                }`}
                style={{ width: `${progress.percent}%` }}
              />
            </div>
            <div className={`text-[10px] text-center mt-1 ${TEXT_TOKENS.muted}`}>
              {progress.done}/{progress.total}
            </div>
          </div>
        )}
      </div>

      {activities.map((act) => {
        const activityWidth = activityWidths?.[act.id] ?? (act.tasks.length + 1) * taskColumnWidth;
        return (
          <div
            key={`activity-body-${act.id}`}
            className="flex"
            style={{ width: activityWidth, flexShrink: 0 }}
          >
            {act.tasks.map((task) => {
              const storiesInCell = task.stories.filter((s) => s.release_id === release.id);
              const cellId = `cell-${task.id}-${release.id}`;
              const isAdding = addingToCell === cellId;
              const draft = storyDrafts[cellId] || { title: '', description: '', priority: 'MVP', error: null };

              return (
                <StoryCell
                  key={`${task.id}-${release.id}`}
                  cellId={cellId}
                  taskId={task.id}
                  releaseId={release.id}
                  stories={storiesInCell}
                  isAdding={isAdding}
                  draft={draft}
                  onOpenAddForm={openAddForm}
                  onCloseAddForm={closeAddForm}
                  onUpdateDraft={updateDraft}
                  onAddStory={onAddStory}
                  storyLoading={storyLoading}
                  onEditStory={onEditStory}
                  onOpenAI={onOpenAI}
                  onStatusChange={onStatusChange}
                  isStoryHandleDisabled={isStoryHandleDisabled}
                  isStoryDragDisabled={isStoryDragDisabled}
                />
              );
            })}
            <div className="w-[280px] flex-shrink-0 border-r border-gray-200"></div>
          </div>
        );
      })}
    </div>
  );
}

export default ReleaseRow;


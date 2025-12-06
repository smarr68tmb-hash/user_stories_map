import StoryCell from './StoryCell';

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
}) {
  return (
    <div className="flex border-b border-gray-200 min-h-[180px] hover:bg-gray-50 transition">
      <div className="w-32 flex-shrink-0 bg-gray-100 p-3 font-bold flex flex-col items-center justify-center text-gray-700 border-r-2 border-gray-300 gap-2">
        <span className="text-sm text-center">{release.title}</span>
        {progress.total > 0 && (
          <div className="w-full px-1">
            <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden" aria-label="Прогресс релиза">
              <div
                className={`h-full rounded-full transition-all duration-500 ${
                  progress.percent === 100 ? 'bg-green-500' : 'bg-blue-500'
                }`}
                style={{ width: `${progress.percent}%` }}
              />
            </div>
            <div className="text-[10px] text-gray-500 text-center mt-1">
              {progress.done}/{progress.total}
            </div>
          </div>
        )}
      </div>

      {activities.map((act) => {
        const taskCount = act.tasks.length;
        const activityWidth = (taskCount + 1) * 220;
        return (
          <div
            key={`activity-body-${act.id}`}
            className="flex"
            style={{ width: `${activityWidth}px`, flexShrink: 0 }}
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
            <div className="w-[220px] flex-shrink-0 border-r border-gray-200"></div>
          </div>
        );
      })}
    </div>
  );
}

export default ReleaseRow;


import { DndContext, closestCenter } from '@dnd-kit/core';
import StoryMapModals from './components/story-map/StoryMapModals';
import StoryMapSkeleton from './components/story-map/StoryMapSkeleton';
import FilterPanel from './components/story-map/FilterPanel';
import SearchPanel from './components/story-map/SearchPanel';
import StoryMapBoard from './components/story-map/StoryMapBoard';
import useActivities from './hooks/useActivities';
import useTasks from './hooks/useTasks';
import useStories from './hooks/useStories';
import useDnD from './hooks/useDnD';
import useStoryMapFilters from './hooks/useStoryMapFilters';
import useStoryMapDrag from './hooks/useStoryMapDrag';
import useStoryMapInteractions from './hooks/useStoryMapInteractions';
import { useToast } from './hooks/useToast';
import { useProjectRefreshContext } from './context/ProjectRefreshContext';
import { STATUS_OPTIONS } from './theme/tokens';

const TASK_COLUMN_WIDTH = 220;
const ACTIVITY_PADDING_COLUMNS = 1;

function StoryMap({ project, onUpdate, onUnauthorized, isLoading = false }) {
  const toast = useToast();
  const { refreshProject, isRefreshing } = useProjectRefreshContext();
  const activitiesApi = useActivities({ project, onUpdate, refreshProject, onUnauthorized, toast });
  const tasksApi = useTasks({ project, onUpdate, refreshProject, onUnauthorized, toast });
  const storiesApi = useStories({ project, onUpdate, refreshProject, onUnauthorized, toast });

  const {
    createActivity,
    updateActivity,
    deleteActivity,
    activityLoading,
  } = activitiesApi;
  const {
    createTask,
    updateTaskTitle,
    deleteTask,
    moveTask,
    taskLoading,
    taskDrafts,
    updateTaskDraft,
    addingTaskActivityId,
    startAddingTask,
    stopAddingTask,
  } = tasksApi;
  const {
    addStory,
    updateStory,
    deleteStory,
    moveStory,
    changeStatus,
    storyLoading,
    addingToCell,
    openAddForm,
    closeAddForm,
    storyDrafts,
    updateDraft,
  } = storiesApi;

  const { statusFilter, releaseFilter, searchQuery, setSearchQuery, toggleStatus, toggleRelease, handleResetFilters, filteredProject, allTasks, activityWidths, releaseProgress } =
    useStoryMapFilters({
      project,
      taskColumnWidth: TASK_COLUMN_WIDTH,
      activityPaddingColumns: ACTIVITY_PADDING_COLUMNS,
    });

  const {
    editingStory,
    editingTaskId,
    pendingDeleteTaskId,
    aiAssistantOpen,
    aiAssistantStory,
    aiAssistantTaskId,
    aiAssistantReleaseId,
    analysisPanelOpen,
    setAnalysisPanelOpen,
    activityHeaderProps: interactionActivityHeaderProps,
    baseReleaseRowProps,
    modalHandlers,
    closeEditModal,
    onOpenEditModal,
    onOpenAIAssistant,
    onStatusChange,
  } = useStoryMapInteractions({
    addStory,
    updateStory,
    deleteStory,
    changeStatus,
    createActivity,
    updateActivity,
    deleteActivity,
    createTask,
    updateTaskTitle,
    deleteTask,
    taskLoading,
    activityLoading,
    addingTaskActivityId,
    taskDrafts,
    updateTaskDraft,
    startAddingTask,
    stopAddingTask,
    storyLoading,
    toast,
    refreshProject,
  });

  const { isTaskDragDisabled, isTaskHandleDisabled, isStoryDragDisabled, isStoryHandleDisabled } = useDnD({
    storyLoading,
    taskLoading,
    editingStoryId: editingStory?.id || null,
    editingTaskId,
    pendingDeleteTaskId,
  });

  const { sensors, handleDragEnd } = useStoryMapDrag({
    project,
    allTasks,
    moveTask,
    moveStory,
    isTaskDragDisabled,
    isStoryDragDisabled,
  });

  const activityHeaderProps = {
    ...interactionActivityHeaderProps,
    isTaskHandleDisabled,
    isTaskDragDisabled,
  };

  const releaseRowProps = {
    ...baseReleaseRowProps,
    addingToCell,
    storyDrafts,
    openAddForm,
    closeAddForm,
    updateDraft,
    releaseProgress,
    isStoryHandleDisabled,
    isStoryDragDisabled,
  };

  if (isLoading) {
    return (
      <StoryMapSkeleton
        activityWidths={activityWidths}
        releases={filteredProject.releases}
        taskColumnWidth={TASK_COLUMN_WIDTH}
      />
    );
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <div className="mb-4 flex flex-col gap-3">
        <FilterPanel
          statusFilter={statusFilter}
          releaseFilter={releaseFilter}
          releases={project.releases}
          onToggleStatus={toggleStatus}
          onToggleRelease={toggleRelease}
          onReset={handleResetFilters}
        />
        <SearchPanel
          searchQuery={searchQuery}
          onSearchChange={setSearchQuery}
          onOpenAnalysis={() => setAnalysisPanelOpen(true)}
          isRefreshing={isRefreshing}
          statusSummary={{ shown: statusFilter.length, total: STATUS_OPTIONS.length }}
          releaseSummary={{ shown: releaseFilter.length, total: project.releases.length }}
        />
      </div>

      <StoryMapBoard
        filteredProject={filteredProject}
        activityWidths={activityWidths}
        taskColumnWidth={TASK_COLUMN_WIDTH}
        activityHeaderProps={activityHeaderProps}
        releaseRowProps={releaseRowProps}
      />

      <StoryMapModals
        editingStory={editingStory}
        releases={project.releases}
        onCloseEdit={closeEditModal}
        onSaveStory={modalHandlers.handleUpdateStory}
        onDeleteStory={modalHandlers.handleDeleteStory}
        aiAssistantOpen={aiAssistantOpen}
        aiAssistantStory={aiAssistantStory}
        aiAssistantTaskId={aiAssistantTaskId}
        aiAssistantReleaseId={aiAssistantReleaseId}
        onCloseAI={modalHandlers.handleCloseAIAssistant}
        onStoryImproved={modalHandlers.handleStoryImproved}
        analysisPanelOpen={analysisPanelOpen}
        onCloseAnalysis={() => setAnalysisPanelOpen(false)}
        projectId={project.id}
      />
    </DndContext>
  );
}

export default StoryMap;


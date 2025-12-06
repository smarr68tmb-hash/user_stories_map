import { useMemo, useState } from 'react';
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import ActivityHeader from './components/story-map/ActivityHeader';
import ReleaseRow from './components/story-map/ReleaseRow';
import StoryMapModals from './components/story-map/StoryMapModals';
import useActivities from './hooks/useActivities';
import useTasks from './hooks/useTasks';
import useStories from './hooks/useStories';
import useDnD from './hooks/useDnD';
import { useToast } from './hooks/useToast';
import { useProjectRefreshContext } from './context/ProjectRefreshContext';

function StoryMap({ project, onUpdate, onUnauthorized }) {
  const toast = useToast();
  const { refreshProject, isRefreshing } = useProjectRefreshContext();
  const {
    createActivity,
    updateActivity,
    deleteActivity,
    activityLoading,
  } = useActivities({ project, onUpdate, refreshProject, onUnauthorized, toast });
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
  } = useTasks({ project, onUpdate, refreshProject, onUnauthorized, toast });
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
  } = useStories({ project, onUpdate, refreshProject, onUnauthorized, toast });

  const [editingStory, setEditingStory] = useState(null);
  const [aiAssistantOpen, setAiAssistantOpen] = useState(false);
  const [aiAssistantStory, setAiAssistantStory] = useState(null);
  const [aiAssistantTaskId, setAiAssistantTaskId] = useState(null);
  const [aiAssistantReleaseId, setAiAssistantReleaseId] = useState(null);
  const [analysisPanelOpen, setAnalysisPanelOpen] = useState(false);
  const [editingActivityId, setEditingActivityId] = useState(null);
  const [editingActivityTitle, setEditingActivityTitle] = useState('');
  const [addingActivity, setAddingActivity] = useState(false);
  const [newActivityTitle, setNewActivityTitle] = useState('');
  const [editingTaskId, setEditingTaskId] = useState(null);
  const [editingTaskTitle, setEditingTaskTitle] = useState('');
  const [pendingDeleteActivityId, setPendingDeleteActivityId] = useState(null);
  const [pendingDeleteTaskId, setPendingDeleteTaskId] = useState(null);

  const { isTaskDragDisabled, isTaskHandleDisabled, isStoryDragDisabled, isStoryHandleDisabled } = useDnD({
    storyLoading,
    taskLoading,
    editingStoryId: editingStory?.id || null,
    editingTaskId,
    pendingDeleteTaskId,
  });

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 3,
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    }),
  );

  const allTasks = useMemo(
    () =>
      project.activities.flatMap((act) =>
        act.tasks.map((task) => ({ ...task, activityTitle: act.title })),
      ),
    [project.activities],
  );

  const findStory = (taskId, releaseId, storyId) => {
    const task = allTasks.find((t) => t.id === taskId);
    if (!task) return null;
    return task.stories.find((s) => s.id === storyId && s.release_id === releaseId);
  };

  const handleDragEnd = async (event) => {
    const { active, over } = event;
    
    if (!over || active.id === over.id) return;

    const activeId = String(active.id);
    const overId = String(over.id);

    if (activeId.startsWith('task-')) {
      const taskId = Number(activeId.replace('task-', ''));
      if (isTaskDragDisabled(taskId)) return;
      const activity = project.activities.find((a) => a.tasks.some((t) => t.id === taskId));
      if (!activity) return;

      if (overId.startsWith('task-')) {
        const targetTaskId = Number(overId.replace('task-', ''));
        const targetTask = activity.tasks.find((t) => t.id === targetTaskId);
        
        if (targetTask && targetTask.id !== taskId) {
          await moveTask(activity.id, taskId, targetTask.position);
        }
      } else if (overId.startsWith('activity-tasks-')) {
        const activityId = Number(overId.replace('activity-tasks-', ''));
        if (activityId === activity.id) {
          const endPosition = Math.max(activity.tasks.length - 1, 0);
          await moveTask(activity.id, taskId, endPosition);
        }
      }
      return;
    }

    const activeParts = activeId.split('-');
    const storyId = Number(activeParts[0]);
    if (isStoryDragDisabled(storyId)) return;

    if (overId.startsWith('cell-')) {
      const cellParts = overId.replace('cell-', '').split('-');
      const targetTaskId = Number(cellParts[0]);
      const targetReleaseId = Number(cellParts[1]);
      await moveStory(storyId, targetTaskId, targetReleaseId, 0);
      return;
    }

    const overParts = overId.split('-');
    if (overParts.length === 3) {
      const targetStoryId = Number(overParts[0]);
      const targetTaskId = Number(overParts[1]);
      const targetReleaseId = Number(overParts[2]);

      if (targetStoryId !== storyId) {
        const targetStory = findStory(targetTaskId, targetReleaseId, targetStoryId);
        if (targetStory) {
          await moveStory(storyId, targetTaskId, targetReleaseId, targetStory.position);
        }
      }
    }
  };

  const handleAddStory = async (taskId, releaseId) => {
    const cellId = `cell-${taskId}-${releaseId}`;
    await addStory(taskId, releaseId, cellId);
  };

  const handleUpdateStory = async (updates) => {
    if (!editingStory) return;
    await updateStory(editingStory.id, updates);
    setEditingStory(null);
  };

  const handleDeleteStory = async () => {
    if (!editingStory) return;
    await deleteStory(editingStory.id);
    setEditingStory(null);
  };

  const handleOpenEditModal = (story) => {
    setEditingStory(story);
  };

  const handleOpenAIAssistant = (story, taskId, releaseId) => {
    setAiAssistantStory(story);
    setAiAssistantTaskId(taskId);
    setAiAssistantReleaseId(releaseId);
    setAiAssistantOpen(true);
  };

  const handleCloseAIAssistant = () => {
    setAiAssistantOpen(false);
    setAiAssistantStory(null);
    setAiAssistantTaskId(null);
    setAiAssistantReleaseId(null);
  };

  const handleStoryImproved = async () => {
    await refreshProject({ silent: false });
  };

  const handleStatusChange = async (storyId, newStatus) => {
    await changeStatus(storyId, newStatus);
  };

  const calculateReleaseProgress = (releaseId) => {
    let total = 0;
    let done = 0;
    
    allTasks.forEach((task) => {
      task.stories.forEach((story) => {
        if (story.release_id === releaseId) {
          total += 1;
          if (story.status === 'done') done += 1;
        }
      });
    });
    
    return { total, done, percent: total > 0 ? Math.round((done / total) * 100) : 0 };
  };
  
  const handleAddActivity = async () => {
    if (!newActivityTitle.trim()) {
      setAddingActivity(false);
      setNewActivityTitle('');
      return;
    }

    const ok = await createActivity(newActivityTitle.trim());
    if (ok) {
      setNewActivityTitle('');
      setAddingActivity(false);
    }
  };

  const handleUpdateActivity = async (activityId) => {
    if (!editingActivityTitle.trim()) {
      setEditingActivityId(null);
      setEditingActivityTitle('');
      return;
    }

    const ok = await updateActivity(activityId, editingActivityTitle.trim());
    if (ok) {
      setEditingActivityId(null);
      setEditingActivityTitle('');
    }
  };

  const handleDeleteActivity = async (activityId) => {
    if (pendingDeleteActivityId === activityId) {
      await deleteActivity(activityId);
      setPendingDeleteActivityId(null);
      return;
    }

    setPendingDeleteActivityId(activityId);
    toast.info('Нажмите ещё раз, чтобы удалить активность');
  };

  const startEditingActivity = (activity) => {
    if (!activity) {
      setEditingActivityId(null);
      setEditingActivityTitle('');
      return;
    }
    setEditingActivityId(activity.id);
    setEditingActivityTitle(activity.title);
  };
  
  const handleAddTask = async (activityId) => {
    await createTask(activityId);
  };

  const handleUpdateTask = async (taskId) => {
    const ok = await updateTaskTitle(taskId, editingTaskTitle);
    if (ok) {
      setEditingTaskId(null);
      setEditingTaskTitle('');
    }
  };

  const handleDeleteTask = async (taskId) => {
    if (pendingDeleteTaskId === taskId) {
      await deleteTask(taskId);
      setPendingDeleteTaskId(null);
      return;
    }

    setPendingDeleteTaskId(taskId);
    toast.info('Нажмите ещё раз, чтобы удалить шаг');
  };

  const startEditingTask = (task) => {
    setEditingTaskId(task.id);
    setEditingTaskTitle(task.title);
  };

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <div className="mb-4 flex justify-end">
        <button
          onClick={() => setAnalysisPanelOpen(true)}
          className="bg-gradient-to-r from-indigo-500 to-purple-500 text-white px-4 py-2 rounded-lg font-medium shadow-lg hover:from-indigo-600 hover:to-purple-600 transition flex items-center gap-2"
        >
          <span>📊</span>
          Анализ карты
        </button>
        {isRefreshing && (
          <span className="ml-3 text-xs text-gray-500 flex items-center gap-1">
            <span className="animate-pulse">●</span>
            Синхронизация…
          </span>
        )}
      </div>

      <div className="w-full overflow-x-auto">
        <div className="inline-block min-w-full bg-white rounded-lg shadow-sm border border-gray-200">
          <ActivityHeader
            activities={project.activities}
            editingActivityId={editingActivityId}
            editingActivityTitle={editingActivityTitle}
            setEditingActivityTitle={setEditingActivityTitle}
            onUpdateActivity={handleUpdateActivity}
            onStartEditingActivity={startEditingActivity}
            onDeleteActivity={handleDeleteActivity}
            activityLoading={activityLoading}
            pendingDeleteActivityId={pendingDeleteActivityId}
            addingActivity={addingActivity}
            onStartAddActivity={() => setAddingActivity(true)}
            onCancelAddActivity={() => {
                        setAddingActivity(false);
                        setNewActivityTitle('');
                      }}
            newActivityTitle={newActivityTitle}
            setNewActivityTitle={setNewActivityTitle}
            onAddActivity={handleAddActivity}
            onAddTask={handleAddTask}
            taskLoading={taskLoading}
            editingTaskId={editingTaskId}
                          editingTaskTitle={editingTaskTitle}
                          setEditingTaskTitle={setEditingTaskTitle}
                          onUpdateTask={handleUpdateTask}
            onStartEditingTask={startEditingTask}
            onDeleteTask={handleDeleteTask}
                          setEditingTaskId={setEditingTaskId}
            pendingDeleteTaskId={pendingDeleteTaskId}
            addingTaskActivityId={addingTaskActivityId}
            taskDrafts={taskDrafts}
            updateTaskDraft={updateTaskDraft}
            startAddingTask={startAddingTask}
            stopAddingTask={stopAddingTask}
            isTaskHandleDisabled={isTaskHandleDisabled}
            isTaskDragDisabled={isTaskDragDisabled}
          />

        <div>
            {project.releases.map((release) => (
              <ReleaseRow
                key={release.id}
                release={release}
                activities={project.activities}
                addingToCell={addingToCell}
                storyDrafts={storyDrafts}
                openAddForm={openAddForm}
                closeAddForm={closeAddForm}
                updateDraft={updateDraft}
                onAddStory={handleAddStory}
                storyLoading={storyLoading}
                onEditStory={handleOpenEditModal}
                onOpenAI={handleOpenAIAssistant}
                                  onStatusChange={handleStatusChange}
                isStoryHandleDisabled={isStoryHandleDisabled}
                isStoryDragDisabled={isStoryDragDisabled}
                progress={calculateReleaseProgress(release.id)}
                                />
                              ))}
        </div>
        </div>
      </div>

      <StoryMapModals
        editingStory={editingStory}
        releases={project.releases}
        onCloseEdit={() => setEditingStory(null)}
        onSaveStory={handleUpdateStory}
        onDeleteStory={handleDeleteStory}
        aiAssistantOpen={aiAssistantOpen}
        aiAssistantStory={aiAssistantStory}
        aiAssistantTaskId={aiAssistantTaskId}
        aiAssistantReleaseId={aiAssistantReleaseId}
        onCloseAI={handleCloseAIAssistant}
          onStoryImproved={handleStoryImproved}
        analysisPanelOpen={analysisPanelOpen}
        onCloseAnalysis={() => setAnalysisPanelOpen(false)}
        projectId={project.id}
      />
    </DndContext>
  );
}

export default StoryMap;


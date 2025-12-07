import { useCallback, useState } from 'react';

function useStoryMapInteractions({
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
}) {
  const [editingStory, setEditingStory] = useState(null);
  const [editingStoryTaskId, setEditingStoryTaskId] = useState(null);
  const [editingStoryReleaseId, setEditingStoryReleaseId] = useState(null);
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

  const handleAddStory = useCallback(
    async (taskId, releaseId) => {
      const cellId = `cell-${taskId}-${releaseId}`;
      await addStory(taskId, releaseId, cellId);
    },
    [addStory],
  );

  const handleUpdateStory = useCallback(
    async (updates) => {
      if (!editingStory) return;
      await updateStory(editingStory.id, updates);
      setEditingStory(null);
    },
    [editingStory, updateStory],
  );

  const handleDeleteStory = useCallback(async () => {
    if (!editingStory) return;
    await deleteStory(editingStory.id);
    setEditingStory(null);
  }, [deleteStory, editingStory]);

  const handleOpenEditModal = useCallback((story, taskId, releaseId) => {
    setEditingStory(story);
    setEditingStoryTaskId(taskId);
    setEditingStoryReleaseId(releaseId);
  }, []);

  const handleOpenAIAssistant = useCallback((story, taskId, releaseId) => {
    setAiAssistantStory(story);
    setAiAssistantTaskId(taskId);
    setAiAssistantReleaseId(releaseId);
    setAiAssistantOpen(true);
  }, []);

  const handleCloseAIAssistant = useCallback(() => {
    setAiAssistantOpen(false);
    setAiAssistantStory(null);
    setAiAssistantTaskId(null);
    setAiAssistantReleaseId(null);
  }, []);

  const closeEditModal = useCallback(() => {
    setEditingStory(null);
    setEditingStoryTaskId(null);
    setEditingStoryReleaseId(null);
  }, []);

  const handleStoryImproved = useCallback(async () => {
    // Silent refresh to avoid full-page flicker after AI improvements
    await refreshProject({ silent: true });
  }, [refreshProject]);

  const handleStatusChange = useCallback(async (storyId, newStatus) => {
    await changeStatus(storyId, newStatus);
  }, [changeStatus]);

  const handleAddActivity = useCallback(async () => {
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
  }, [createActivity, newActivityTitle]);

  const handleUpdateActivity = useCallback(
    async (activityId) => {
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
    },
    [editingActivityTitle, updateActivity],
  );

  const handleDeleteActivity = useCallback(
    async (activityId) => {
      if (pendingDeleteActivityId === activityId) {
        await deleteActivity(activityId);
        setPendingDeleteActivityId(null);
        return;
      }

      setPendingDeleteActivityId(activityId);
      toast.info('Нажмите ещё раз, чтобы удалить активность');
    },
    [deleteActivity, pendingDeleteActivityId, toast],
  );

  const startEditingActivity = useCallback((activity) => {
    if (!activity) {
      setEditingActivityId(null);
      setEditingActivityTitle('');
      return;
    }
    setEditingActivityId(activity.id);
    setEditingActivityTitle(activity.title);
  }, []);

  const handleAddTask = useCallback(async (activityId) => {
    await createTask(activityId);
  }, [createTask]);

  const handleUpdateTask = useCallback(
    async (taskId) => {
      const ok = await updateTaskTitle(taskId, editingTaskTitle);
      if (ok) {
        setEditingTaskId(null);
        setEditingTaskTitle('');
      }
    },
    [editingTaskTitle, updateTaskTitle],
  );

  const handleDeleteTask = useCallback(
    async (taskId) => {
      if (pendingDeleteTaskId === taskId) {
        await deleteTask(taskId);
        setPendingDeleteTaskId(null);
        return;
      }

      setPendingDeleteTaskId(taskId);
      toast.info('Нажмите ещё раз, чтобы удалить шаг');
    },
    [deleteTask, pendingDeleteTaskId, toast],
  );

  const startEditingTask = useCallback((task) => {
    setEditingTaskId(task.id);
    setEditingTaskTitle(task.title);
  }, []);

  const activityHeaderProps = {
    editingActivityId,
    editingActivityTitle,
    setEditingActivityTitle,
    onUpdateActivity: handleUpdateActivity,
    onStartEditingActivity: startEditingActivity,
    onDeleteActivity: handleDeleteActivity,
    activityLoading,
    pendingDeleteActivityId,
    addingActivity,
    onStartAddActivity: () => setAddingActivity(true),
    onCancelAddActivity: () => {
      setAddingActivity(false);
      setNewActivityTitle('');
    },
    newActivityTitle,
    setNewActivityTitle,
    onAddActivity: handleAddActivity,
    onAddTask: handleAddTask,
    taskLoading,
    editingTaskId,
    editingTaskTitle,
    setEditingTaskTitle,
    onUpdateTask: handleUpdateTask,
    onStartEditingTask: startEditingTask,
    onDeleteTask: handleDeleteTask,
    setEditingTaskId,
    pendingDeleteTaskId,
    addingTaskActivityId,
    taskDrafts,
    updateTaskDraft,
    startAddingTask,
    stopAddingTask,
  };

  return {
    editingStory,
    editingStoryTaskId,
    editingStoryReleaseId,
    editingTaskId,
    pendingDeleteTaskId,
    aiAssistantOpen,
    aiAssistantStory,
    aiAssistantTaskId,
    aiAssistantReleaseId,
    analysisPanelOpen,
    setAnalysisPanelOpen,
    activityHeaderProps,
    baseReleaseRowProps: {
      onAddStory: handleAddStory,
      storyLoading,
      onEditStory: handleOpenEditModal,
      onOpenAI: handleOpenAIAssistant,
      onStatusChange: handleStatusChange,
    },
    modalHandlers: {
      handleUpdateStory,
      handleDeleteStory,
      handleCloseAIAssistant,
      handleStoryImproved,
    },
    closeEditModal,
    onOpenEditModal: handleOpenEditModal,
    onOpenAIAssistant: handleOpenAIAssistant,
    onStatusChange: handleStatusChange,
  };
}

export default useStoryMapInteractions;


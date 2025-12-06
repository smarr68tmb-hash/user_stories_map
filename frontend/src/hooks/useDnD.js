import { useMemo } from 'react';

export function useDnD({
  storyLoading,
  taskLoading,
  editingStoryId = null,
  editingTaskId = null,
  pendingDeleteTaskId = null,
}) {
  const isTaskHandleDisabled = useMemo(
    () => (taskId) =>
      taskLoading?.isMoving(taskId) ||
      taskLoading?.isUpdating(taskId) ||
      taskLoading?.isDeleting(taskId) ||
      editingTaskId === taskId ||
      pendingDeleteTaskId === taskId,
    [editingTaskId, pendingDeleteTaskId, taskLoading],
  );

  const isTaskDragDisabled = useMemo(
    () => (taskId) => isTaskHandleDisabled(taskId),
    [isTaskHandleDisabled],
  );

  const isStoryHandleDisabled = useMemo(
    () => (storyId) =>
      storyLoading?.isMoving(storyId) ||
      storyLoading?.isDeleting(storyId) ||
      storyLoading?.isUpdating(storyId) ||
      storyLoading?.isChangingStatus(storyId) ||
      editingStoryId === storyId,
    [editingStoryId, storyLoading],
  );

  const isStoryDragDisabled = useMemo(
    () => (storyId) => isStoryHandleDisabled(storyId),
    [isStoryHandleDisabled],
  );

  return {
    isTaskDragDisabled,
    isTaskHandleDisabled,
    isStoryDragDisabled,
    isStoryHandleDisabled,
  };
}

export default useDnD;


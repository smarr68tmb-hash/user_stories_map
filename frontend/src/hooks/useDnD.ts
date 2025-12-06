import { useMemo } from 'react';
import type { Identifier } from '../types';

type LoadingGuards = {
  isMoving?: (id: Identifier) => boolean;
  isUpdating?: (id: Identifier) => boolean;
  isDeleting?: (id: Identifier) => boolean;
  isChangingStatus?: (id: Identifier) => boolean;
};

interface UseDnDParams {
  storyLoading?: LoadingGuards;
  taskLoading?: Omit<LoadingGuards, 'isChangingStatus'>;
  editingStoryId?: Identifier | null;
  editingTaskId?: Identifier | null;
  pendingDeleteTaskId?: Identifier | null;
}

interface UseDnDResult {
  isTaskDragDisabled: (taskId: Identifier) => boolean;
  isTaskHandleDisabled: (taskId: Identifier) => boolean;
  isStoryDragDisabled: (storyId: Identifier) => boolean;
  isStoryHandleDisabled: (storyId: Identifier) => boolean;
}

export function useDnD({
  storyLoading,
  taskLoading,
  editingStoryId = null,
  editingTaskId = null,
  pendingDeleteTaskId = null,
}: UseDnDParams): UseDnDResult {
  const isTaskHandleDisabled = useMemo(
    () => (taskId: Identifier) =>
      taskLoading?.isMoving?.(taskId) ||
      taskLoading?.isUpdating?.(taskId) ||
      taskLoading?.isDeleting?.(taskId) ||
      editingTaskId === taskId ||
      pendingDeleteTaskId === taskId,
    [editingTaskId, pendingDeleteTaskId, taskLoading],
  );

  const isTaskDragDisabled = useMemo(
    () => (taskId: Identifier) => isTaskHandleDisabled(taskId),
    [isTaskHandleDisabled],
  );

  const isStoryHandleDisabled = useMemo(
    () => (storyId: Identifier) =>
      storyLoading?.isMoving?.(storyId) ||
      storyLoading?.isDeleting?.(storyId) ||
      storyLoading?.isUpdating?.(storyId) ||
      storyLoading?.isChangingStatus?.(storyId) ||
      editingStoryId === storyId,
    [editingStoryId, storyLoading],
  );

  const isStoryDragDisabled = useMemo(
    () => (storyId: Identifier) => isStoryHandleDisabled(storyId),
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


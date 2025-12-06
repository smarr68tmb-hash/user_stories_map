import { useMemo } from 'react';

export function useDnD({ storyLoading, taskLoading }) {
  const isTaskDragDisabled = useMemo(() => (taskId) => taskLoading?.isMoving(taskId), [taskLoading]);
  const isStoryDragDisabled = useMemo(() => (storyId) => storyLoading?.isMoving(storyId), [storyLoading]);

  return {
    isTaskDragDisabled,
    isStoryDragDisabled,
  };
}

export default useDnD;


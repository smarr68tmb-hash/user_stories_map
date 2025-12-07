import { useCallback } from 'react';
import { KeyboardSensor, PointerSensor, useSensor, useSensors } from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';

function useStoryMapDrag({
  project,
  allTasks,
  moveTask,
  moveStory,
  isTaskDragDisabled,
  isStoryDragDisabled,
}) {
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

  const findStory = useCallback(
    (taskId, releaseId, storyId) => {
      const task = allTasks.find((t) => t.id === taskId);
      if (!task) return null;
      return task.stories.find((s) => s.id === storyId && s.release_id === releaseId);
    },
    [allTasks],
  );

  const findStoriesInCell = useCallback(
    (taskId, releaseId) => {
      const task = allTasks.find((t) => t.id === taskId);
      if (!task) return [];
      return task.stories.filter((s) => s.release_id === releaseId);
    },
    [allTasks],
  );

  const handleDragEnd = useCallback(
    async (event) => {
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
        const targetReleaseIdRaw = Number(cellParts[1]);
        const targetReleaseId = Number.isNaN(targetReleaseIdRaw) ? null : targetReleaseIdRaw;
        const storiesInCell = findStoriesInCell(targetTaskId, targetReleaseId);
        await moveStory(storyId, targetTaskId, targetReleaseId, storiesInCell.length);
        return;
      }

      const overParts = overId.split('-');
      if (overParts.length === 3) {
        const targetStoryId = Number(overParts[0]);
        const targetTaskId = Number(overParts[1]);
        const targetReleaseIdRaw = Number(overParts[2]);
        const targetReleaseId = Number.isNaN(targetReleaseIdRaw) ? null : targetReleaseIdRaw;

        if (targetStoryId !== storyId) {
          const targetStory = findStory(targetTaskId, targetReleaseId, targetStoryId);
          if (targetStory) {
            const sortableIndex = over?.data?.current?.sortable?.index;
            const targetPosition =
              typeof sortableIndex === 'number'
                ? sortableIndex
                : typeof targetStory.position === 'number'
                  ? targetStory.position
                  : 0;
            await moveStory(storyId, targetTaskId, targetReleaseId, targetPosition);
          }
        }
      }
    },
    [findStoriesInCell, findStory, isStoryDragDisabled, isTaskDragDisabled, moveStory, moveTask, project.activities],
  );

  return { sensors, handleDragEnd };
}

export default useStoryMapDrag;


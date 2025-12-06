import { useCallback, useMemo, useState } from 'react';
import { tasks } from '../api';
import handleApiError from '../utils/handleApiError';
import {
  addTask,
  moveTask as moveTaskTransform,
  removeTask,
  updateTask as updateTaskTransform,
} from '../utils/projectTransforms';

const defaultTaskDraft = { title: '', error: null };

export function useTasks({ project, onUpdate, refreshProject, onUnauthorized, toast }) {
  const [loading, setLoading] = useState({
    create: {},
    update: {},
    delete: {},
    move: {},
  });
  const [taskDrafts, setTaskDrafts] = useState({});
  const [addingTaskActivityId, setAddingTaskActivityId] = useState(null);

  const setScopedLoading = useCallback((key, id, value) => {
    setLoading((prev) => ({
      ...prev,
      [key]: { ...prev[key], [id]: value },
    }));
  }, []);

  const ensureDraft = useCallback((activityId) => {
    setTaskDrafts((prev) => {
      if (prev[activityId]) return prev;
      return { ...prev, [activityId]: { ...defaultTaskDraft } };
    });
  }, []);

  const updateTaskDraft = useCallback((activityId, patch) => {
    setTaskDrafts((prev) => ({
      ...prev,
      [activityId]: { ...(prev[activityId] || defaultTaskDraft), ...patch },
    }));
  }, []);

  const resetTaskDraft = useCallback((activityId) => {
    setTaskDrafts((prev) => ({
      ...prev,
      [activityId]: { ...defaultTaskDraft },
    }));
  }, []);

  const startAddingTask = useCallback((activityId) => {
    ensureDraft(activityId);
    setAddingTaskActivityId(activityId);
  }, [ensureDraft]);

  const stopAddingTask = useCallback(() => {
    if (addingTaskActivityId) {
      resetTaskDraft(addingTaskActivityId);
    }
    setAddingTaskActivityId(null);
  }, [addingTaskActivityId, resetTaskDraft]);

  const createTask = useCallback(async (activityId, titleFromArgs) => {
    const draft = taskDrafts[activityId] || defaultTaskDraft;
    const titleValue = titleFromArgs != null ? titleFromArgs : draft.title;
    const trimmed = (titleValue || '').trim();
    if (!trimmed) {
      toast?.warning('Поле названия шага должно быть заполнено');
      updateTaskDraft(activityId, { error: 'Поле названия шага должно быть заполнено' });
      return false;
    }
    const prev = project;
    setScopedLoading('create', activityId, true);
    const tempTask = { id: `tmp-${Date.now()}`, title: trimmed, position: project.activities.find((a) => a.id === activityId)?.tasks.length || 0, stories: [] };
    onUpdate(addTask(project, activityId, tempTask));

    try {
      const res = await tasks.create(activityId, trimmed);
      const realTask = res?.data || tempTask;
      onUpdate(addTask(removeTask(project, tempTask.id), activityId, realTask));
      toast?.success('Шаг добавлен');
      resetTaskDraft(activityId);
      setAddingTaskActivityId(null);
      await refreshProject?.({ silent: true });
      return true;
    } catch (error) {
      onUpdate(prev);
      const msg = handleApiError(error, onUnauthorized);
      toast?.error(msg);
      return false;
    } finally {
      setScopedLoading('create', activityId, false);
    }
  }, [addTask, onUnauthorized, onUpdate, project, refreshProject, removeTask, setScopedLoading, tasks, toast, updateTaskDraft, resetTaskDraft, taskDrafts]);

  const updateTaskTitle = useCallback(async (taskId, title) => {
    const trimmed = title.trim();
    if (!trimmed) {
      toast?.warning('Поле названия шага должно быть заполнено');
      return false;
    }
    const prev = project;
    setScopedLoading('update', taskId, true);
    onUpdate(updateTaskTransform(project, taskId, { title: trimmed }));

    try {
      const res = await tasks.update(taskId, trimmed);
      const payload = res?.data || { title: trimmed };
      onUpdate(updateTaskTransform(project, taskId, payload));
      toast?.success('Шаг обновлён');
      await refreshProject?.({ silent: true });
      return true;
    } catch (error) {
      onUpdate(prev);
      const msg = handleApiError(error, onUnauthorized);
      toast?.error(msg);
      return false;
    } finally {
      setScopedLoading('update', taskId, false);
    }
  }, [onUnauthorized, onUpdate, project, refreshProject, setScopedLoading, toast]);

  const deleteTask = useCallback(async (taskId) => {
    const prev = project;
    setScopedLoading('delete', taskId, true);
    onUpdate(removeTask(project, taskId));

    try {
      await tasks.delete(taskId);
      toast?.success('Шаг удалён');
      await refreshProject?.({ silent: true });
    } catch (error) {
      onUpdate(prev);
      const msg = handleApiError(error, onUnauthorized);
      toast?.error(msg);
    } finally {
      setScopedLoading('delete', taskId, false);
    }
  }, [onUnauthorized, onUpdate, project, refreshProject, setScopedLoading, toast]);

  const moveTask = useCallback(async (activityId, taskId, newPosition) => {
    const prev = project;
    setScopedLoading('move', taskId, true);
    onUpdate(moveTaskTransform(project, activityId, taskId, newPosition));

    try {
      await tasks.move(taskId, newPosition);
      await refreshProject?.({ silent: true });
    } catch (error) {
      onUpdate(prev);
      const msg = handleApiError(error, onUnauthorized);
      toast?.error(msg);
    } finally {
      setScopedLoading('move', taskId, false);
    }
  }, [onUnauthorized, onUpdate, project, refreshProject, setScopedLoading, toast]);

  const taskLoading = useMemo(() => ({
    isCreating: (activityId) => !!loading.create[activityId],
    isUpdating: (taskId) => !!loading.update[taskId],
    isDeleting: (taskId) => !!loading.delete[taskId],
    isMoving: (taskId) => !!loading.move[taskId],
  }), [loading]);

  return {
    createTask,
    updateTaskTitle,
    deleteTask,
    moveTask,
    taskLoading,
    taskDrafts,
    updateTaskDraft,
    resetTaskDraft,
    addingTaskActivityId,
    startAddingTask,
    stopAddingTask,
  };
}

export default useTasks;


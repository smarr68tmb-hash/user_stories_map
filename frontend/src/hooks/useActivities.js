import { useCallback, useMemo, useState } from 'react';
import { activities } from '../api';
import handleApiError from '../utils/handleApiError';
import { addActivity, removeActivity, updateActivity as updateActivityTransform } from '../utils/projectTransforms';

export function useActivities({ project, onUpdate, refreshProject, onUnauthorized, toast }) {
  const [loading, setLoading] = useState({
    create: false,
    update: {},
    delete: {},
  });

  const setUpdateLoading = useCallback((activityId, value) => {
    setLoading((prev) => ({
      ...prev,
      update: { ...prev.update, [activityId]: value },
    }));
  }, []);

  const setDeleteLoading = useCallback((activityId, value) => {
    setLoading((prev) => ({
      ...prev,
      delete: { ...prev.delete, [activityId]: value },
    }));
  }, []);

  const createActivity = useCallback(async (title) => {
    const trimmed = title.trim();
    if (!trimmed) {
      toast?.warning('Название активности не может быть пустым');
      return false;
    }
    const prev = project;
    setLoading((prevState) => ({ ...prevState, create: true }));

    try {
      const res = await activities.create(project.id, trimmed);
      const newActivity = res?.data || { id: `tmp-${Date.now()}`, title: trimmed, position: project.activities.length, tasks: [] };
      onUpdate(addActivity(project, newActivity));
      toast?.success('Активность добавлена');
      await refreshProject?.({ silent: true });
      return true;
    } catch (error) {
      const msg = handleApiError(error, onUnauthorized);
      toast?.error(msg);
      onUpdate(prev);
      return false;
    } finally {
      setLoading((prevState) => ({ ...prevState, create: false }));
    }
  }, [onUnauthorized, onUpdate, project, refreshProject, toast]);

  const updateActivity = useCallback(async (activityId, title) => {
    const trimmed = title.trim();
    if (!trimmed) {
      toast?.warning('Название активности не может быть пустым');
      return false;
    }
    const prev = project;
    setUpdateLoading(activityId, true);
    const optimistic = updateActivityTransform(project, activityId, { title: trimmed });
    onUpdate(optimistic);

    try {
      const res = await activities.update(activityId, trimmed);
      const payload = res?.data || { title: trimmed };
      onUpdate(updateActivityTransform(project, activityId, payload));
      toast?.success('Активность обновлена');
      await refreshProject?.({ silent: true });
      return true;
    } catch (error) {
      onUpdate(prev);
      const msg = handleApiError(error, onUnauthorized);
      toast?.error(msg);
      return false;
    } finally {
      setUpdateLoading(activityId, false);
    }
  }, [onUnauthorized, onUpdate, project, refreshProject, setUpdateLoading, toast]);

  const deleteActivity = useCallback(async (activityId) => {
    const prev = project;
    setDeleteLoading(activityId, true);
    onUpdate(removeActivity(project, activityId));

    try {
      await activities.delete(activityId);
      toast?.success('Активность удалена');
      await refreshProject?.({ silent: true });
      return true;
    } catch (error) {
      onUpdate(prev);
      const msg = handleApiError(error, onUnauthorized);
      toast?.error(msg);
      return false;
    } finally {
      setDeleteLoading(activityId, false);
    }
  }, [onUnauthorized, onUpdate, project, refreshProject, setDeleteLoading, toast]);

  const activityLoading = useMemo(() => ({
    isCreating: loading.create,
    isUpdating: (id) => !!loading.update[id],
    isDeleting: (id) => !!loading.delete[id],
  }), [loading]);

  return {
    createActivity,
    updateActivity,
    deleteActivity,
    activityLoading,
  };
}

export default useActivities;


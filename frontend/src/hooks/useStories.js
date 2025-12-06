import { useCallback, useMemo, useState } from 'react';
import api from '../api';
import handleApiError from '../utils/handleApiError';
import {
  addStory as addStoryTransform,
  moveStory as moveStoryTransform,
  removeStory as removeStoryTransform,
  updateStory as updateStoryTransform,
  updateStoryStatus,
} from '../utils/projectTransforms';

const defaultDraft = {
  title: '',
  description: '',
  priority: 'MVP',
  error: null,
};

export function useStories({ project, onUpdate, refreshProject, onUnauthorized, toast }) {
  const [loading, setLoading] = useState({
    add: {},
    update: {},
    delete: {},
    move: {},
    status: {},
  });
  const [addingToCell, setAddingToCell] = useState(null);
  const [storyDrafts, setStoryDrafts] = useState({});

  const setScopedLoading = useCallback((key, id, value) => {
    setLoading((prev) => ({
      ...prev,
      [key]: { ...prev[key], [id]: value },
    }));
  }, []);

  const ensureDraft = useCallback((cellId) => {
    setStoryDrafts((prev) => {
      if (prev[cellId]) return prev;
      return { ...prev, [cellId]: { ...defaultDraft } };
    });
  }, []);

  const updateDraft = useCallback((cellId, patch) => {
    setStoryDrafts((prev) => ({
      ...prev,
      [cellId]: { ...(prev[cellId] || defaultDraft), ...patch },
    }));
  }, []);

  const resetDraft = useCallback((cellId) => {
    setStoryDrafts((prev) => ({
      ...prev,
      [cellId]: { ...defaultDraft },
    }));
  }, []);

  const openAddForm = useCallback((cellId) => {
    ensureDraft(cellId);
    setAddingToCell(cellId);
  }, [ensureDraft]);

  const closeAddForm = useCallback((cellId) => {
    if (cellId) {
      resetDraft(cellId);
    }
    setAddingToCell(null);
  }, [resetDraft]);

  const addStory = useCallback(async (taskId, releaseId, cellId) => {
    const draft = storyDrafts[cellId] || defaultDraft;
    const title = (draft.title || '').trim();
    if (!title) {
      updateDraft(cellId, { error: 'Название истории обязательно' });
      toast?.warning('Название истории обязательно');
      return;
    }
    const prev = project;
    setScopedLoading('add', cellId, true);
    const payload = {
      task_id: taskId,
      release_id: releaseId,
      title,
      description: draft.description || '',
      priority: draft.priority || 'MVP',
    };

    try {
      const res = await api.post('/story', payload);
      const story = res?.data || { id: `tmp-${Date.now()}`, ...payload };
      onUpdate(addStoryTransform(project, taskId, releaseId, story));
      toast?.success('История добавлена');
      closeAddForm(cellId);
      await refreshProject?.({ silent: true });
    } catch (error) {
      onUpdate(prev);
      const msg = handleApiError(error, onUnauthorized);
      toast?.error(msg);
      updateDraft(cellId, { error: msg });
    } finally {
      setScopedLoading('add', cellId, false);
    }
  }, [closeAddForm, onUnauthorized, onUpdate, project, refreshProject, setScopedLoading, storyDrafts, toast, updateDraft]);

  const updateStory = useCallback(async (storyId, updates) => {
    const prev = project;
    setScopedLoading('update', storyId, true);
    onUpdate(updateStoryTransform(project, storyId, updates));

    try {
      const res = await api.put(`/story/${storyId}`, updates);
      const payload = res?.data || updates;
      onUpdate(updateStoryTransform(project, storyId, payload));
      toast?.success('История обновлена');
      await refreshProject?.({ silent: true });
    } catch (error) {
      onUpdate(prev);
      const msg = handleApiError(error, onUnauthorized);
      toast?.error(msg);
    } finally {
      setScopedLoading('update', storyId, false);
    }
  }, [onUnauthorized, onUpdate, project, refreshProject, setScopedLoading, toast]);

  // Store pending deletes for undo functionality
  const [pendingDeletes, setPendingDeletes] = useState({});

  const deleteStory = useCallback(async (storyId) => {
    const prev = project;

    // Find the story before removing it (for undo)
    let deletedStory = null;
    let deletedFromTask = null;
    let deletedFromRelease = null;

    for (const activity of project.activities || []) {
      for (const task of activity.tasks || []) {
        const story = task.stories?.find(s => s.id === storyId);
        if (story) {
          deletedStory = { ...story };
          deletedFromTask = task.id;
          deletedFromRelease = story.release_id;
          break;
        }
      }
      if (deletedStory) break;
    }

    if (!deletedStory) {
      toast?.error('История не найдена');
      return;
    }

    setScopedLoading('delete', storyId, true);
    onUpdate(removeStoryTransform(project, storyId));

    // Set up pending delete with timeout
    const deleteTimeout = setTimeout(async () => {
      try {
        await api.delete(`/story/${storyId}`);
        await refreshProject?.({ silent: true });
      } catch (error) {
        // If deletion fails, restore the story
        onUpdate(prev);
        const msg = handleApiError(error, onUnauthorized);
        toast?.error(msg);
      } finally {
        setPendingDeletes((p) => {
          const newPending = { ...p };
          delete newPending[storyId];
          return newPending;
        });
        setScopedLoading('delete', storyId, false);
      }
    }, 8000);

    // Store pending delete info
    setPendingDeletes((p) => ({
      ...p,
      [storyId]: {
        story: deletedStory,
        taskId: deletedFromTask,
        releaseId: deletedFromRelease,
        timeout: deleteTimeout,
        prevProject: prev,
      },
    }));

    // Show undo toast
    toast?.showWithUndo('Карточка удалена', () => {
      // Undo: cancel the delete
      clearTimeout(deleteTimeout);
      setPendingDeletes((p) => {
        const newPending = { ...p };
        delete newPending[storyId];
        return newPending;
      });
      onUpdate(prev);
      setScopedLoading('delete', storyId, false);
      toast?.success('Карточка восстановлена');
    });
  }, [onUnauthorized, onUpdate, project, refreshProject, setScopedLoading, toast]);

  const moveStory = useCallback(async (storyId, targetTaskId, targetReleaseId, targetPosition) => {
    const prev = project;
    setScopedLoading('move', storyId, true);
    onUpdate(moveStoryTransform(project, storyId, targetTaskId, targetReleaseId, targetPosition));

    try {
      await api.patch(`/story/${storyId}/move`, {
        task_id: targetTaskId,
        release_id: targetReleaseId,
        position: targetPosition,
      });
      await refreshProject?.({ silent: true });
    } catch (error) {
      onUpdate(prev);
      const msg = handleApiError(error, onUnauthorized);
      toast?.error(msg);
    } finally {
      setScopedLoading('move', storyId, false);
    }
  }, [onUnauthorized, onUpdate, project, refreshProject, setScopedLoading, toast]);

  const changeStatus = useCallback(async (storyId, status) => {
    const prev = project;
    setScopedLoading('status', storyId, true);
    onUpdate(updateStoryStatus(project, storyId, status));

    try {
      const res = await api.patch(`/story/${storyId}/status`, { status });
      const payload = res?.data || { status };
      onUpdate(updateStoryTransform(project, storyId, payload));
      await refreshProject?.({ silent: true });
    } catch (error) {
      onUpdate(prev);
      const msg = handleApiError(error, onUnauthorized);
      toast?.error(msg);
    } finally {
      setScopedLoading('status', storyId, false);
    }
  }, [onUnauthorized, onUpdate, project, refreshProject, setScopedLoading, toast]);

  const storyLoading = useMemo(() => ({
    isAdding: (cellId) => !!loading.add[cellId],
    isUpdating: (storyId) => !!loading.update[storyId],
    isDeleting: (storyId) => !!loading.delete[storyId],
    isMoving: (storyId) => !!loading.move[storyId],
    isChangingStatus: (storyId) => !!loading.status[storyId],
  }), [loading]);

  return {
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
  };
}

export default useStories;


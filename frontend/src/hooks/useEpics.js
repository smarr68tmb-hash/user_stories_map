import { useState, useCallback, useEffect } from 'react';
import { epics } from '../api';
import handleApiError from '../utils/handleApiError';

export function useEpics({ project, refreshProject, onUnauthorized, toast }) {
  const [epicsList, setEpicsList] = useState([]);
  const [loading, setLoading] = useState({
    generate: false,
    fetch: false,
    update: {},
    addStory: {},
    removeStory: {},
    accept: {},
    reject: {},
  });

  const setScopedLoading = useCallback((key, id, value) => {
    setLoading((prev) => ({
      ...prev,
      [key]: id !== undefined ? { ...prev[key], [id]: value } : value,
    }));
  }, []);

  // Загрузка эпиков проекта
  const fetchEpics = useCallback(async () => {
    if (!project?.id) return;

    setScopedLoading('fetch', undefined, true);
    try {
      const response = await epics.getByProject(project.id);
      setEpicsList(response.data || []);
    } catch (error) {
      handleApiError(error, toast, onUnauthorized);
    } finally {
      setScopedLoading('fetch', undefined, false);
    }
  }, [project?.id, toast, onUnauthorized, setScopedLoading]);

  // Загружаем эпики при изменении проекта
  useEffect(() => {
    fetchEpics();
  }, [fetchEpics]);

  // Генерация эпиков
  const generateEpics = useCallback(
    async (minEpics = 3, maxEpics = 7) => {
      if (!project?.id) return;

      setScopedLoading('generate', undefined, true);
      try {
        const response = await epics.generate(project.id, { min_epics: minEpics, max_epics: maxEpics });
        toast.success(response.data.message || `Генерировано ${response.data.epics.length} эпиков`);
        
        // Обновляем список эпиков
        await fetchEpics();
        
        // Обновляем проект чтобы получить обновленные истории с epic_id
        if (refreshProject) {
          await refreshProject();
        }
        
        return response.data;
      } catch (error) {
        handleApiError(error, toast, onUnauthorized);
        throw error;
      } finally {
        setScopedLoading('generate', undefined, false);
      }
    },
    [project?.id, toast, onUnauthorized, setScopedLoading, fetchEpics, refreshProject]
  );

  // Обновление эпика
  const updateEpic = useCallback(
    async (epicId, updates) => {
      setScopedLoading('update', epicId, true);
      try {
        await epics.update(epicId, updates);
        toast.success('Эпик обновлен');
        
        // Обновляем список эпиков
        await fetchEpics();
      } catch (error) {
        handleApiError(error, toast, onUnauthorized);
      } finally {
        setScopedLoading('update', epicId, false);
      }
    },
    [toast, onUnauthorized, setScopedLoading, fetchEpics]
  );

  // Добавление истории в эпик
  const addStoryToEpic = useCallback(
    async (epicId, storyId) => {
      setScopedLoading('addStory', `${epicId}-${storyId}`, true);
      try {
        await epics.addStory(epicId, storyId);
        toast.success('История добавлена в эпик');
        
        // Обновляем список эпиков
        await fetchEpics();
        
        // Обновляем проект
        if (refreshProject) {
          await refreshProject();
        }
      } catch (error) {
        handleApiError(error, toast, onUnauthorized);
      } finally {
        setScopedLoading('addStory', `${epicId}-${storyId}`, false);
      }
    },
    [toast, onUnauthorized, setScopedLoading, fetchEpics, refreshProject]
  );

  // Удаление истории из эпика
  const removeStoryFromEpic = useCallback(
    async (epicId, storyId) => {
      setScopedLoading('removeStory', `${epicId}-${storyId}`, true);
      try {
        await epics.removeStory(epicId, storyId);
        toast.success('История удалена из эпика');
        
        // Обновляем список эпиков
        await fetchEpics();
        
        // Обновляем проект
        if (refreshProject) {
          await refreshProject();
        }
      } catch (error) {
        handleApiError(error, toast, onUnauthorized);
      } finally {
        setScopedLoading('removeStory', `${epicId}-${storyId}`, false);
      }
    },
    [toast, onUnauthorized, setScopedLoading, fetchEpics, refreshProject]
  );

  // Принятие эпика
  const acceptEpic = useCallback(
    async (epicId) => {
      setScopedLoading('accept', epicId, true);
      try {
        await epics.accept(epicId);
        toast.success('Эпик принят');
      } catch (error) {
        handleApiError(error, toast, onUnauthorized);
      } finally {
        setScopedLoading('accept', epicId, false);
      }
    },
    [toast, onUnauthorized, setScopedLoading]
  );

  // Отклонение эпика
  const rejectEpic = useCallback(
    async (epicId) => {
      setScopedLoading('reject', epicId, true);
      try {
        await epics.reject(epicId);
        toast.success('Эпик отклонен и удален');
        
        // Обновляем список эпиков
        await fetchEpics();
        
        // Обновляем проект
        if (refreshProject) {
          await refreshProject();
        }
      } catch (error) {
        handleApiError(error, toast, onUnauthorized);
      } finally {
        setScopedLoading('reject', epicId, false);
      }
    },
    [toast, onUnauthorized, setScopedLoading, fetchEpics, refreshProject]
  );

  return {
    epics: epicsList,
    loading,
    generateEpics,
    updateEpic,
    addStoryToEpic,
    removeStoryFromEpic,
    acceptEpic,
    rejectEpic,
    fetchEpics,
  };
}


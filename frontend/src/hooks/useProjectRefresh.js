import { useCallback, useRef, useState } from 'react';
import api from '../api';
import { handleApiError } from '../utils/handleApiError';

export function useProjectRefresh(projectId, onUpdate, { onUnauthorized, toast } = {}) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const refreshingRef = useRef(false);

  const refreshProject = useCallback(async ({ silent = true } = {}) => {
    if (refreshingRef.current) {
      return null;
    }

    refreshingRef.current = true;
    if (!silent) setIsRefreshing(true);

    try {
      const res = await api.get(`/project/${projectId}`);
      onUpdate(res.data);
      return res.data;
    } catch (error) {
      const errorMsg = handleApiError(error, onUnauthorized);
      if (toast) {
        toast.error(errorMsg);
      } else {
        console.error(errorMsg);
      }
      throw error;
    } finally {
      if (!silent) setIsRefreshing(false);
      refreshingRef.current = false;
    }
  }, [onUnauthorized, onUpdate, projectId, toast]);

  return { refreshProject, isRefreshing };
}

export default useProjectRefresh;


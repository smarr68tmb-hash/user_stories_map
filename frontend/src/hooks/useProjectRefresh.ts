import { useCallback, useRef, useState } from 'react';
import { projects } from '../api';
import { handleApiError } from '../utils/handleApiError';
import type { Project } from '../types';

type UseProjectRefreshOptions = {
  onUnauthorized?: () => void;
  toast?: {
    error: (message: string) => void;
  };
};

type UseProjectRefreshResult = {
  refreshProject: (options?: { silent?: boolean }) => Promise<Project | null>;
  isRefreshing: boolean;
};

export function useProjectRefresh(
  projectId: number | string,
  onUpdate: (project: Project) => void,
  { onUnauthorized, toast }: UseProjectRefreshOptions = {},
): UseProjectRefreshResult {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const refreshingRef = useRef(false);

  const refreshProject = useCallback(
    async ({ silent = true }: { silent?: boolean } = {}) => {
      if (refreshingRef.current) {
        return null;
      }

      refreshingRef.current = true;
      if (!silent) setIsRefreshing(true);

      try {
        const res = await projects.get(projectId);
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
    },
    [onUnauthorized, onUpdate, projectId, toast],
  );

  return { refreshProject, isRefreshing };
}

export default useProjectRefresh;


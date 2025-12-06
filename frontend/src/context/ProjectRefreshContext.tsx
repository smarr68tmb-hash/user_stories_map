import React, { createContext, useContext, useMemo } from 'react';
import useProjectRefresh from '../hooks/useProjectRefresh';
import type { Project } from '../types';

type ToastApi = {
  error: (message: string) => void;
};

type ProjectRefreshContextValue = {
  projectId: number | string;
  refreshProject: (options?: { silent?: boolean }) => Promise<Project | null>;
  isRefreshing: boolean;
};

type ProjectRefreshProviderProps = {
  projectId: number | string;
  onUpdate: (project: Project) => void;
  onUnauthorized?: () => void;
  toast?: ToastApi;
  children: React.ReactNode;
};

const ProjectRefreshContext = createContext<ProjectRefreshContextValue | null>(null);

export function ProjectRefreshProvider({
  projectId,
  onUpdate,
  onUnauthorized,
  toast,
  children,
}: ProjectRefreshProviderProps) {
  const refreshState = useProjectRefresh(projectId, onUpdate, { onUnauthorized, toast });

  const value = useMemo(
    () => ({
      ...refreshState,
      projectId,
    }),
    [refreshState, projectId],
  );

  return <ProjectRefreshContext.Provider value={value}>{children}</ProjectRefreshContext.Provider>;
}

export function useProjectRefreshContext(): ProjectRefreshContextValue {
  const ctx = useContext(ProjectRefreshContext);
  if (!ctx) {
    throw new Error('useProjectRefreshContext must be used within ProjectRefreshProvider');
  }
  return ctx;
}

export default ProjectRefreshContext;


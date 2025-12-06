import { createContext, useContext, useMemo } from 'react';
import useProjectRefresh from '../hooks/useProjectRefresh';

const ProjectRefreshContext = createContext(null);

export function ProjectRefreshProvider({ projectId, onUpdate, onUnauthorized, toast, children }) {
  const refreshState = useProjectRefresh(projectId, onUpdate, { onUnauthorized, toast });

  const value = useMemo(() => ({
    ...refreshState,
    projectId,
  }), [refreshState, projectId]);

  return (
    <ProjectRefreshContext.Provider value={value}>
      {children}
    </ProjectRefreshContext.Provider>
  );
}

export function useProjectRefreshContext() {
  const ctx = useContext(ProjectRefreshContext);
  if (!ctx) {
    throw new Error('useProjectRefreshContext must be used within ProjectRefreshProvider');
  }
  return ctx;
}

export default ProjectRefreshContext;


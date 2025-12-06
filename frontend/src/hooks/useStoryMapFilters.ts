import { useCallback, useEffect, useMemo, useState } from 'react';
import { STATUS_OPTIONS } from '../theme/tokens';
import type { Activity, Project, Release, Status, Task } from '../types';

type UseStoryMapFiltersParams = {
  project: Project;
  taskColumnWidth?: number;
  activityPaddingColumns?: number;
};

type ReleaseProgress = Record<number, { total: number; done: number; percent: number }>;

type AllTasksWithActivity = Array<Task & { activityTitle: string }>;

function useStoryMapFilters({
  project,
  taskColumnWidth = 220,
  activityPaddingColumns = 1,
}: UseStoryMapFiltersParams) {
  const [statusFilter, setStatusFilter] = useState<Status[]>(STATUS_OPTIONS.map((s) => s.value as Status));
  const [releaseFilter, setReleaseFilter] = useState<number[]>(project.releases.map((r) => r.id));
  const [searchQuery, setSearchQuery] = useState<string>('');

  const filterStorageKey = useMemo(() => `storymap_filters_${project.id}`, [project.id]);
  const availableReleaseIds = useMemo(
    () => project.releases.map((release) => release.id),
    [project.releases],
  );

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const statusParam = params.get('status');
    const releaseParam = params.get('release');
    const searchParam = params.get('q');

    let nextStatuses: Status[] = STATUS_OPTIONS.map((s) => s.value as Status);
    let nextReleases: number[] = availableReleaseIds;
    let nextSearch = '';

    const storedRaw = localStorage.getItem(filterStorageKey);
    if (storedRaw) {
      try {
        const stored = JSON.parse(storedRaw) as { status?: Status[]; releases?: (number | string)[]; search?: string };
        if (Array.isArray(stored.status)) {
          const validStatuses = stored.status.filter((s) => STATUS_OPTIONS.some((opt) => opt.value === s));
          if (validStatuses.length) {
            nextStatuses = validStatuses as Status[];
          }
        }
        if (Array.isArray(stored.releases)) {
          const validReleases = stored.releases
            .map((id) => Number(id))
            .filter((id) => availableReleaseIds.includes(id));
          if (validReleases.length) {
            nextReleases = validReleases;
          }
        }
        if (typeof stored.search === 'string') {
          nextSearch = stored.search;
        }
      } catch (e) {
        console.warn('Failed to parse saved filters', e);
      }
    }

    if (statusParam) {
      const parsedStatuses = statusParam
        .split(',')
        .filter((s) => STATUS_OPTIONS.some((opt) => opt.value === s)) as Status[];
      if (parsedStatuses.length) {
        nextStatuses = parsedStatuses;
      }
    }

    if (releaseParam) {
      const parsedReleases = releaseParam
        .split(',')
        .map((id) => Number(id))
        .filter((id) => availableReleaseIds.includes(id));
      if (parsedReleases.length) {
        nextReleases = parsedReleases;
      }
    }

    if (searchParam) {
      nextSearch = searchParam;
    }

    setStatusFilter(nextStatuses);
    setReleaseFilter(nextReleases.length ? nextReleases : availableReleaseIds);
    setSearchQuery(nextSearch);
  }, [availableReleaseIds, filterStorageKey]);

  useEffect(() => {
    setReleaseFilter((prev) => {
      const filtered = prev.filter((id) => availableReleaseIds.includes(id));
      const newOnes = availableReleaseIds.filter((id) => !filtered.includes(id));
      const next = [...filtered, ...newOnes];
      return next.length ? next : availableReleaseIds;
    });
  }, [availableReleaseIds]);

  const persistFilters = useCallback(
    (statuses: Status[], releases: number[], search: string) => {
      const payload = { status: statuses, releases, search };
      localStorage.setItem(filterStorageKey, JSON.stringify(payload));

      const params = new URLSearchParams(window.location.search);
      if (statuses.length && statuses.length !== STATUS_OPTIONS.length) {
        params.set('status', statuses.join(','));
      } else {
        params.delete('status');
      }

      if (releases.length && releases.length !== availableReleaseIds.length) {
        params.set('release', releases.join(','));
      } else {
        params.delete('release');
      }

      if (search && search.trim()) {
        params.set('q', search.trim());
      } else {
        params.delete('q');
      }

      const newSearch = params.toString();
      const newUrl = `${window.location.pathname}${newSearch ? `?${newSearch}` : ''}`;
      window.history.replaceState({}, '', newUrl);
    },
    [availableReleaseIds, filterStorageKey],
  );

  useEffect(() => {
    persistFilters(statusFilter, releaseFilter, searchQuery);
  }, [persistFilters, releaseFilter, searchQuery, statusFilter]);

  const toggleStatus = useCallback((value: Status) => {
    setStatusFilter((prev) => {
      const exists = prev.includes(value);
      const next = exists ? prev.filter((s) => s !== value) : [...prev, value];
      return next.length ? next : (STATUS_OPTIONS.map((s) => s.value) as Status[]);
    });
  }, []);

  const toggleRelease = useCallback(
    (id: number) => {
      setReleaseFilter((prev) => {
        const exists = prev.includes(id);
        const next = exists ? prev.filter((r) => r !== id) : [...prev, id];
        return next.length ? next : availableReleaseIds;
      });
    },
    [availableReleaseIds],
  );

  const handleResetFilters = useCallback(() => {
    setStatusFilter(STATUS_OPTIONS.map((s) => s.value as Status));
    setReleaseFilter(availableReleaseIds);
    setSearchQuery('');
  }, [availableReleaseIds]);

  const normalizedQuery = useMemo(() => searchQuery.trim().toLowerCase(), [searchQuery]);

  const filteredReleases = useMemo<Release[]>(
    () => project.releases.filter((release) => releaseFilter.includes(release.id)),
    [project.releases, releaseFilter],
  );

  const filteredActivities = useMemo<Activity[]>(
    () =>
      project.activities.map((act) => ({
        ...act,
        tasks: act.tasks.map((task) => ({
          ...task,
          stories: task.stories.filter((story) => {
            const status = (story.status as Status | undefined) ?? 'todo';
            const isStatusAllowed = statusFilter.includes(status);
            const isReleaseAllowed = releaseFilter.includes(Number(story.release_id));
            const matchesQuery =
              !normalizedQuery ||
              story.title?.toLowerCase().includes(normalizedQuery) ||
              story.description?.toLowerCase().includes(normalizedQuery);
            return isStatusAllowed && isReleaseAllowed && matchesQuery;
          }),
        })),
      })),
    [normalizedQuery, project.activities, releaseFilter, statusFilter],
  );

  const filteredProject = useMemo<Project>(
    () => ({
      ...project,
      activities: filteredActivities,
      releases: filteredReleases,
    }),
    [filteredActivities, filteredReleases, project],
  );

  const allTasks = useMemo<AllTasksWithActivity>(
    () =>
      filteredProject.activities.flatMap((act) =>
        act.tasks
          .slice()
          .sort((a, b) => (a.position ?? 0) - (b.position ?? 0))
          .map((task) => ({ ...task, activityTitle: act.title })),
      ),
    [filteredProject.activities],
  );

  const activityWidths = useMemo<Record<string, number>>(() => {
    const widths: Record<string, number> = {};
    filteredProject.activities.forEach((act) => {
      widths[String(act.id)] = (act.tasks.length + activityPaddingColumns) * taskColumnWidth;
    });
    return widths;
  }, [activityPaddingColumns, filteredProject.activities, taskColumnWidth]);

  const releaseProgress = useMemo<ReleaseProgress>(() => {
    return filteredProject.releases.reduce<ReleaseProgress>((acc, release) => {
      let total = 0;
      let done = 0;

      allTasks.forEach((task) => {
        task.stories.forEach((story) => {
          if (story.release_id === release.id) {
            total += 1;
            if (story.status === 'done') done += 1;
          }
        });
      });

      acc[release.id] = {
        total,
        done,
        percent: total > 0 ? Math.round((done / total) * 100) : 0,
      };
      return acc;
    }, {});
  }, [allTasks, filteredProject.releases]);

  return {
    statusFilter,
    releaseFilter,
    searchQuery,
    setSearchQuery,
    toggleStatus,
    toggleRelease,
    handleResetFilters,
    filteredProject,
    allTasks,
    activityWidths,
    releaseProgress,
  };
}

export default useStoryMapFilters;


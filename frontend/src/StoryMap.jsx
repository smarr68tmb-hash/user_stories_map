import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  DndContext,
  KeyboardSensor,
  PointerSensor,
  closestCenter,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import ActivityHeader from './components/story-map/ActivityHeader';
import ReleaseRow from './components/story-map/ReleaseRow';
import StoryMapModals from './components/story-map/StoryMapModals';
import StoryMapSkeleton from './components/story-map/StoryMapSkeleton';
import useActivities from './hooks/useActivities';
import useTasks from './hooks/useTasks';
import useStories from './hooks/useStories';
import useDnD from './hooks/useDnD';
import { useToast } from './hooks/useToast';
import { useProjectRefreshContext } from './context/ProjectRefreshContext';
import { STATUS_OPTIONS, getStatusToken } from './theme/tokens';

const TASK_COLUMN_WIDTH = 220;
const ACTIVITY_PADDING_COLUMNS = 1;

function StoryMap({ project, onUpdate, onUnauthorized, isLoading = false }) {
  const toast = useToast();
  const { refreshProject, isRefreshing } = useProjectRefreshContext();
  const {
    createActivity,
    updateActivity,
    deleteActivity,
    activityLoading,
  } = useActivities({ project, onUpdate, refreshProject, onUnauthorized, toast });
  const {
    createTask,
    updateTaskTitle,
    deleteTask,
    moveTask,
    taskLoading,
    taskDrafts,
    updateTaskDraft,
    addingTaskActivityId,
    startAddingTask,
    stopAddingTask,
  } = useTasks({ project, onUpdate, refreshProject, onUnauthorized, toast });
  const {
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
  } = useStories({ project, onUpdate, refreshProject, onUnauthorized, toast });

  const [editingStory, setEditingStory] = useState(null);
  const [aiAssistantOpen, setAiAssistantOpen] = useState(false);
  const [aiAssistantStory, setAiAssistantStory] = useState(null);
  const [aiAssistantTaskId, setAiAssistantTaskId] = useState(null);
  const [aiAssistantReleaseId, setAiAssistantReleaseId] = useState(null);
  const [analysisPanelOpen, setAnalysisPanelOpen] = useState(false);
  const [editingActivityId, setEditingActivityId] = useState(null);
  const [editingActivityTitle, setEditingActivityTitle] = useState('');
  const [addingActivity, setAddingActivity] = useState(false);
  const [newActivityTitle, setNewActivityTitle] = useState('');
  const [editingTaskId, setEditingTaskId] = useState(null);
  const [editingTaskTitle, setEditingTaskTitle] = useState('');
  const [pendingDeleteActivityId, setPendingDeleteActivityId] = useState(null);
  const [pendingDeleteTaskId, setPendingDeleteTaskId] = useState(null);
  const [statusFilter, setStatusFilter] = useState(STATUS_OPTIONS.map((s) => s.value));
  const [releaseFilter, setReleaseFilter] = useState(project.releases.map((r) => r.id));

  const { isTaskDragDisabled, isTaskHandleDisabled, isStoryDragDisabled, isStoryHandleDisabled } = useDnD({
    storyLoading,
    taskLoading,
    editingStoryId: editingStory?.id || null,
    editingTaskId,
    pendingDeleteTaskId,
  });

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

  const filterStorageKey = useMemo(() => `storymap_filters_${project.id}`, [project.id]);
  const availableReleaseIds = useMemo(
    () => project.releases.map((release) => release.id),
    [project.releases],
  );

  // Инициализация фильтров из URL или localStorage
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const statusParam = params.get('status');
    const releaseParam = params.get('release');

    let nextStatuses = STATUS_OPTIONS.map((s) => s.value);
    let nextReleases = availableReleaseIds;

    const storedRaw = localStorage.getItem(filterStorageKey);
    if (storedRaw) {
      try {
        const stored = JSON.parse(storedRaw);
        if (Array.isArray(stored.status)) {
          const validStatuses = stored.status.filter((s) => STATUS_OPTIONS.some((opt) => opt.value === s));
          if (validStatuses.length) {
            nextStatuses = validStatuses;
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
      } catch (e) {
        console.warn('Failed to parse saved filters', e);
      }
    }

    if (statusParam) {
      const parsedStatuses = statusParam.split(',').filter((s) => STATUS_OPTIONS.some((opt) => opt.value === s));
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

    setStatusFilter(nextStatuses);
    setReleaseFilter(nextReleases.length ? nextReleases : availableReleaseIds);
  }, [availableReleaseIds, filterStorageKey]);

  // Поддерживаем актуальность фильтров при появлении новых релизов
  useEffect(() => {
    setReleaseFilter((prev) => {
      const filtered = prev.filter((id) => availableReleaseIds.includes(id));
      const newOnes = availableReleaseIds.filter((id) => !filtered.includes(id));
      const next = [...filtered, ...newOnes];
      return next.length ? next : availableReleaseIds;
    });
  }, [availableReleaseIds]);

  const persistFilters = useCallback(
    (statuses, releases) => {
      const payload = { status: statuses, releases };
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

      const newSearch = params.toString();
      const newUrl = `${window.location.pathname}${newSearch ? `?${newSearch}` : ''}`;
      window.history.replaceState({}, '', newUrl);
    },
    [availableReleaseIds, filterStorageKey],
  );

  useEffect(() => {
    persistFilters(statusFilter, releaseFilter);
  }, [persistFilters, releaseFilter, statusFilter]);

  const toggleStatus = useCallback((value) => {
    setStatusFilter((prev) => {
      const exists = prev.includes(value);
      const next = exists ? prev.filter((s) => s !== value) : [...prev, value];
      return next.length ? next : STATUS_OPTIONS.map((s) => s.value);
    });
  }, []);

  const toggleRelease = useCallback(
    (id) => {
      setReleaseFilter((prev) => {
        const exists = prev.includes(id);
        const next = exists ? prev.filter((r) => r !== id) : [...prev, id];
        return next.length ? next : availableReleaseIds;
      });
    },
    [availableReleaseIds],
  );

  const handleResetFilters = useCallback(() => {
    setStatusFilter(STATUS_OPTIONS.map((s) => s.value));
    setReleaseFilter(availableReleaseIds);
  }, [availableReleaseIds]);

  const filteredReleases = useMemo(
    () => project.releases.filter((release) => releaseFilter.includes(release.id)),
    [project.releases, releaseFilter],
  );

  const filteredActivities = useMemo(
    () =>
      project.activities.map((act) => ({
        ...act,
        tasks: act.tasks.map((task) => ({
          ...task,
          stories: task.stories.filter((story) => {
            const status = story.status || 'todo';
            const isStatusAllowed = statusFilter.includes(status);
            const isReleaseAllowed = releaseFilter.includes(story.release_id);
            return isStatusAllowed && isReleaseAllowed;
          }),
        })),
      })),
    [project.activities, releaseFilter, statusFilter],
  );

  const filteredProject = useMemo(
    () => ({
      ...project,
      activities: filteredActivities,
      releases: filteredReleases,
    }),
    [filteredActivities, filteredReleases, project],
  );

  const allTasks = useMemo(
    () =>
      filteredProject.activities.flatMap((act) =>
        act.tasks.map((task) => ({ ...task, activityTitle: act.title })),
      ),
    [filteredProject.activities],
  );

  const activityWidths = useMemo(() => {
    const widths = {};
    filteredProject.activities.forEach((act) => {
      widths[act.id] = (act.tasks.length + ACTIVITY_PADDING_COLUMNS) * TASK_COLUMN_WIDTH;
    });
    return widths;
  }, [filteredProject.activities]);

  const releaseProgress = useMemo(() => {
    return filteredProject.releases.reduce((acc, release) => {
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

  const findStory = (taskId, releaseId, storyId) => {
    const task = allTasks.find((t) => t.id === taskId);
    if (!task) return null;
    return task.stories.find((s) => s.id === storyId && s.release_id === releaseId);
  };

  const handleDragEnd = async (event) => {
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
      const targetReleaseId = Number(cellParts[1]);
      await moveStory(storyId, targetTaskId, targetReleaseId, 0);
      return;
    }

    const overParts = overId.split('-');
    if (overParts.length === 3) {
      const targetStoryId = Number(overParts[0]);
      const targetTaskId = Number(overParts[1]);
      const targetReleaseId = Number(overParts[2]);

      if (targetStoryId !== storyId) {
        const targetStory = findStory(targetTaskId, targetReleaseId, targetStoryId);
        if (targetStory) {
          await moveStory(storyId, targetTaskId, targetReleaseId, targetStory.position);
        }
      }
    }
  };

  const handleAddStory = async (taskId, releaseId) => {
    const cellId = `cell-${taskId}-${releaseId}`;
    await addStory(taskId, releaseId, cellId);
  };

  const handleUpdateStory = async (updates) => {
    if (!editingStory) return;
    await updateStory(editingStory.id, updates);
    setEditingStory(null);
  };

  const handleDeleteStory = async () => {
    if (!editingStory) return;
    await deleteStory(editingStory.id);
    setEditingStory(null);
  };

  const handleOpenEditModal = (story) => {
    setEditingStory(story);
  };

  const handleOpenAIAssistant = (story, taskId, releaseId) => {
    setAiAssistantStory(story);
    setAiAssistantTaskId(taskId);
    setAiAssistantReleaseId(releaseId);
    setAiAssistantOpen(true);
  };

  const handleCloseAIAssistant = () => {
    setAiAssistantOpen(false);
    setAiAssistantStory(null);
    setAiAssistantTaskId(null);
    setAiAssistantReleaseId(null);
  };

  const handleStoryImproved = async () => {
    await refreshProject({ silent: false });
  };

  const handleStatusChange = async (storyId, newStatus) => {
    await changeStatus(storyId, newStatus);
  };

  const handleAddActivity = async () => {
    if (!newActivityTitle.trim()) {
      setAddingActivity(false);
      setNewActivityTitle('');
      return;
    }

    const ok = await createActivity(newActivityTitle.trim());
    if (ok) {
      setNewActivityTitle('');
      setAddingActivity(false);
    }
  };

  const handleUpdateActivity = async (activityId) => {
    if (!editingActivityTitle.trim()) {
      setEditingActivityId(null);
      setEditingActivityTitle('');
      return;
    }

    const ok = await updateActivity(activityId, editingActivityTitle.trim());
    if (ok) {
      setEditingActivityId(null);
      setEditingActivityTitle('');
    }
  };

  const handleDeleteActivity = async (activityId) => {
    if (pendingDeleteActivityId === activityId) {
      await deleteActivity(activityId);
      setPendingDeleteActivityId(null);
      return;
    }

    setPendingDeleteActivityId(activityId);
    toast.info('Нажмите ещё раз, чтобы удалить активность');
  };

  const startEditingActivity = (activity) => {
    if (!activity) {
      setEditingActivityId(null);
      setEditingActivityTitle('');
      return;
    }
    setEditingActivityId(activity.id);
    setEditingActivityTitle(activity.title);
  };
  
  const handleAddTask = async (activityId) => {
    await createTask(activityId);
  };

  const handleUpdateTask = async (taskId) => {
    const ok = await updateTaskTitle(taskId, editingTaskTitle);
    if (ok) {
      setEditingTaskId(null);
      setEditingTaskTitle('');
    }
  };

  const handleDeleteTask = async (taskId) => {
    if (pendingDeleteTaskId === taskId) {
      await deleteTask(taskId);
      setPendingDeleteTaskId(null);
      return;
    }

    setPendingDeleteTaskId(taskId);
    toast.info('Нажмите ещё раз, чтобы удалить шаг');
  };

  const startEditingTask = (task) => {
    setEditingTaskId(task.id);
    setEditingTaskTitle(task.title);
  };

  if (isLoading) {
    return (
      <StoryMapSkeleton
        activityWidths={activityWidths}
        releases={filteredProject.releases}
        taskColumnWidth={TASK_COLUMN_WIDTH}
      />
    );
  }

  return (
    <DndContext sensors={sensors} collisionDetection={closestCenter} onDragEnd={handleDragEnd}>
      <div className="mb-4 flex flex-col gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold text-gray-700">Статусы:</span>
          {STATUS_OPTIONS.map((option) => {
            const isActive = statusFilter.includes(option.value);
            const token = getStatusToken(option.value);
            return (
              <button
                key={option.value}
                onClick={() => toggleStatus(option.value)}
                className={`px-3 py-1 rounded-full border text-sm transition focus:outline-none ${
                  isActive
                    ? `${token.badge} ring-1 ring-offset-1 ${token.ring}`
                    : 'bg-white border-gray-300 text-gray-600 hover:border-gray-400 focus:ring-2 focus:ring-offset-1'
                }`}
                aria-pressed={isActive}
              >
                {option.label}
              </button>
            );
          })}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-sm font-semibold text-gray-700">Релизы:</span>
          {project.releases.map((release) => {
            const checked = releaseFilter.includes(release.id);
            return (
              <label
                key={release.id}
                className={`flex items-center gap-2 px-2 py-1 rounded border text-sm cursor-pointer transition ${
                  checked ? 'border-blue-300 bg-blue-50 text-blue-800' : 'border-gray-200 bg-white text-gray-700'
                }`}
              >
                <input
                  type="checkbox"
                  className="accent-blue-600"
                  checked={checked}
                  onChange={() => toggleRelease(release.id)}
                />
                <span className="max-w-[160px] truncate" title={release.title}>
                  {release.title}
                </span>
              </label>
            );
          })}
          <button
            onClick={handleResetFilters}
            className="ml-2 text-sm text-gray-600 hover:text-gray-800 px-3 py-1 border border-gray-300 rounded-lg bg-white transition"
          >
            Сбросить фильтры
          </button>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-3">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setAnalysisPanelOpen(true)}
              className="bg-gradient-to-r from-indigo-500 to-purple-500 text-white px-4 py-2 rounded-lg font-medium shadow-lg hover:from-indigo-600 hover:to-purple-600 transition flex items-center gap-2"
            >
              <span>📊</span>
              Анализ карты
            </button>
            {isRefreshing && (
              <span className="text-xs text-gray-500 flex items-center gap-1">
                <span className="animate-pulse">●</span>
                Синхронизация…
              </span>
            )}
          </div>
          <div className="text-xs text-gray-500">
            Показаны статусы: {statusFilter.length}/{STATUS_OPTIONS.length}, релизы: {releaseFilter.length}/{project.releases.length}
          </div>
        </div>
      </div>

      <div className="w-full overflow-x-auto">
        <div className="inline-block min-w-full bg-white rounded-lg shadow-sm border border-gray-200">
          <ActivityHeader
            activities={project.activities}
            editingActivityId={editingActivityId}
            editingActivityTitle={editingActivityTitle}
            setEditingActivityTitle={setEditingActivityTitle}
            onUpdateActivity={handleUpdateActivity}
            onStartEditingActivity={startEditingActivity}
            onDeleteActivity={handleDeleteActivity}
            activityLoading={activityLoading}
            pendingDeleteActivityId={pendingDeleteActivityId}
            addingActivity={addingActivity}
            onStartAddActivity={() => setAddingActivity(true)}
            onCancelAddActivity={() => {
                        setAddingActivity(false);
                        setNewActivityTitle('');
                      }}
            newActivityTitle={newActivityTitle}
            setNewActivityTitle={setNewActivityTitle}
            onAddActivity={handleAddActivity}
            onAddTask={handleAddTask}
            taskLoading={taskLoading}
            editingTaskId={editingTaskId}
                          editingTaskTitle={editingTaskTitle}
                          setEditingTaskTitle={setEditingTaskTitle}
                          onUpdateTask={handleUpdateTask}
            onStartEditingTask={startEditingTask}
            onDeleteTask={handleDeleteTask}
                          setEditingTaskId={setEditingTaskId}
            pendingDeleteTaskId={pendingDeleteTaskId}
            addingTaskActivityId={addingTaskActivityId}
            taskDrafts={taskDrafts}
            updateTaskDraft={updateTaskDraft}
            startAddingTask={startAddingTask}
            stopAddingTask={stopAddingTask}
            isTaskHandleDisabled={isTaskHandleDisabled}
            isTaskDragDisabled={isTaskDragDisabled}
            activityWidths={activityWidths}
            taskColumnWidth={TASK_COLUMN_WIDTH}
          />

        <div>
            {filteredProject.releases.map((release) => (
              <ReleaseRow
                key={release.id}
                release={release}
                activities={filteredProject.activities}
                addingToCell={addingToCell}
                storyDrafts={storyDrafts}
                openAddForm={openAddForm}
                closeAddForm={closeAddForm}
                updateDraft={updateDraft}
                onAddStory={handleAddStory}
                storyLoading={storyLoading}
                onEditStory={handleOpenEditModal}
                onOpenAI={handleOpenAIAssistant}
                                  onStatusChange={handleStatusChange}
                isStoryHandleDisabled={isStoryHandleDisabled}
                isStoryDragDisabled={isStoryDragDisabled}
                progress={releaseProgress[release.id] || { total: 0, done: 0, percent: 0 }}
                activityWidths={activityWidths}
                taskColumnWidth={TASK_COLUMN_WIDTH}
                                />
                              ))}
        </div>
        </div>
      </div>

      <StoryMapModals
        editingStory={editingStory}
        releases={project.releases}
        onCloseEdit={() => setEditingStory(null)}
        onSaveStory={handleUpdateStory}
        onDeleteStory={handleDeleteStory}
        aiAssistantOpen={aiAssistantOpen}
        aiAssistantStory={aiAssistantStory}
        aiAssistantTaskId={aiAssistantTaskId}
        aiAssistantReleaseId={aiAssistantReleaseId}
        onCloseAI={handleCloseAIAssistant}
          onStoryImproved={handleStoryImproved}
        analysisPanelOpen={analysisPanelOpen}
        onCloseAnalysis={() => setAnalysisPanelOpen(false)}
        projectId={project.id}
      />
    </DndContext>
  );
}

export default StoryMap;


import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import StoryMap from './StoryMap';

vi.mock('@dnd-kit/core', () => ({
  DndContext: ({ children }) => <div>{children}</div>,
  closestCenter: vi.fn(),
  useSensor: () => ({}),
  useSensors: () => [],
  PointerSensor: vi.fn(),
  KeyboardSensor: vi.fn(),
}));

vi.mock('@dnd-kit/sortable', () => ({
  sortableKeyboardCoordinates: vi.fn(),
}));

vi.mock('./hooks/useActivities', () => ({
  __esModule: true,
  default: () => ({
    createActivity: vi.fn(),
    updateActivity: vi.fn(),
    deleteActivity: vi.fn(),
    activityLoading: { isUpdating: vi.fn() },
  }),
}));

vi.mock('./hooks/useTasks', () => ({
  __esModule: true,
  default: () => ({
    createTask: vi.fn(),
    updateTaskTitle: vi.fn(),
    deleteTask: vi.fn(),
    moveTask: vi.fn(),
    taskLoading: { isMoving: vi.fn(), isUpdating: vi.fn(), isDeleting: vi.fn() },
    taskDrafts: {},
    updateTaskDraft: vi.fn(),
    addingTaskActivityId: null,
    startAddingTask: vi.fn(),
    stopAddingTask: vi.fn(),
  }),
}));

vi.mock('./hooks/useStories', () => ({
  __esModule: true,
  default: () => ({
    addStory: vi.fn(),
    updateStory: vi.fn(),
    deleteStory: vi.fn(),
    moveStory: vi.fn(),
    changeStatus: vi.fn(),
    storyLoading: { isMoving: vi.fn(), isDeleting: vi.fn(), isUpdating: vi.fn(), isChangingStatus: vi.fn() },
    addingToCell: null,
    openAddForm: vi.fn(),
    closeAddForm: vi.fn(),
    storyDrafts: {},
    updateDraft: vi.fn(),
  }),
}));

vi.mock('./hooks/useDnD', () => ({
  __esModule: true,
  default: () => ({
    isTaskDragDisabled: () => false,
    isTaskHandleDisabled: () => false,
    isStoryDragDisabled: () => false,
    isStoryHandleDisabled: () => false,
  }),
}));

vi.mock('./hooks/useToast', () => ({
  useToast: () => ({ info: vi.fn(), success: vi.fn(), error: vi.fn() }),
}));

vi.mock('./context/ProjectRefreshContext', () => ({
  useProjectRefreshContext: () => ({
    refreshProject: vi.fn(),
    isRefreshing: false,
  }),
}));

// Stub heavy children with simple shells
vi.mock('./components/story-map/ActivityHeader', () => ({
  __esModule: true,
  default: () => <div data-testid="activity-header" />,
}));
vi.mock('./components/story-map/ReleaseRow', () => ({
  __esModule: true,
  default: () => <div data-testid="release-row" />,
}));
vi.mock('./components/story-map/StoryMapSkeleton', () => ({
  __esModule: true,
  default: () => <div data-testid="storymap-skeleton" />,
}));
vi.mock('./components/story-map/StoryMapModals', () => ({
  __esModule: true,
  default: () => <div data-testid="storymap-modals" />,
}));

const baseProject = {
  id: 1,
  releases: [
    { id: 10, title: 'R1' },
    { id: 11, title: 'R2' },
  ],
  activities: [
    {
      id: 20,
      title: 'Act',
      tasks: [
        {
          id: 30,
          title: 'Task',
          position: 0,
          stories: [],
        },
      ],
    },
  ],
};

describe('StoryMap filters', () => {
  beforeEach(() => {
    if (typeof localStorage?.clear === 'function') {
      localStorage.clear();
    } else {
      vi.stubGlobal('localStorage', {
        getItem: vi.fn(),
        setItem: vi.fn(),
        removeItem: vi.fn(),
        clear: vi.fn(),
      });
    }
    vi.spyOn(window.history, 'replaceState').mockImplementation(() => {});
  });

  it('toggles status filters and reset restores all', () => {
    render(
      <StoryMap
        project={baseProject}
        onUpdate={() => {}}
        onUnauthorized={() => {}}
        isLoading={false}
      />,
    );

    const todoBtn = screen.getByRole('button', { name: /todo/i });
    expect(todoBtn).toHaveAttribute('aria-pressed', 'true');

    fireEvent.click(todoBtn);
    expect(todoBtn).toHaveAttribute('aria-pressed', 'false');

    fireEvent.click(screen.getByRole('button', { name: /сбросить фильтры/i }));
    expect(todoBtn).toHaveAttribute('aria-pressed', 'true');
  });

  it('resets release checkboxes', () => {
    render(
      <StoryMap
        project={baseProject}
        onUpdate={() => {}}
        onUnauthorized={() => {}}
        isLoading={false}
      />,
    );

    const releaseCheckbox = screen.getByLabelText('R1');
    expect(releaseCheckbox).toBeChecked();

    fireEvent.click(releaseCheckbox);
    expect(releaseCheckbox).not.toBeChecked();

    fireEvent.click(screen.getByRole('button', { name: /сбросить фильтры/i }));
    expect(releaseCheckbox).toBeChecked();
  });
});


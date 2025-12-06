import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import StoryMap from './StoryMap';

vi.mock('@dnd-kit/core', () => ({
  DndContext: ({ children }) => <div data-testid="dnd-context">{children}</div>,
  closestCenter: vi.fn(),
}));

vi.mock('./hooks/useActivities', () => ({
  __esModule: true,
  default: () => ({
    createActivity: vi.fn(),
    updateActivity: vi.fn(),
    deleteActivity: vi.fn(),
    activityLoading: { isUpdating: vi.fn(), isDeleting: vi.fn() },
  }),
}));

vi.mock('./hooks/useTasks', () => ({
  __esModule: true,
  default: () => ({
    createTask: vi.fn(),
    updateTaskTitle: vi.fn(),
    deleteTask: vi.fn(),
    moveTask: vi.fn(),
    taskLoading: { isMoving: vi.fn(), isUpdating: vi.fn(), isDeleting: vi.fn(), isCreating: vi.fn() },
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

vi.mock('./hooks/useStoryMapDrag', () => ({
  __esModule: true,
  default: () => ({ sensors: [], handleDragEnd: vi.fn() }),
}));

vi.mock('./hooks/useStoryMapInteractions', () => ({
  __esModule: true,
  default: () => ({
    editingStory: null,
    editingTaskId: null,
    pendingDeleteTaskId: null,
    aiAssistantOpen: false,
    aiAssistantStory: null,
    aiAssistantTaskId: null,
    aiAssistantReleaseId: null,
    analysisPanelOpen: false,
    setAnalysisPanelOpen: vi.fn(),
    activityHeaderProps: {},
    baseReleaseRowProps: {},
    modalHandlers: {
      handleUpdateStory: vi.fn(),
      handleDeleteStory: vi.fn(),
      handleCloseAIAssistant: vi.fn(),
      handleStoryImproved: vi.fn(),
    },
    closeEditModal: vi.fn(),
    onOpenEditModal: vi.fn(),
    onOpenAIAssistant: vi.fn(),
    onStatusChange: vi.fn(),
  }),
}));

vi.mock('./components/story-map/StoryMapBoard', () => ({
  __esModule: true,
  default: () => <div data-testid="storymap-board" />,
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

describe('StoryMap filters and search', () => {
  beforeEach(() => {
    vi.stubGlobal('localStorage', {
      getItem: vi.fn(),
      setItem: vi.fn(),
      removeItem: vi.fn(),
      clear: vi.fn(),
    });
    vi.spyOn(window.history, 'replaceState').mockImplementation(() => {});
    window.location.search = '';
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('toggles status filters and reset restores all', () => {
    render(<StoryMap project={baseProject} onUpdate={() => {}} onUnauthorized={() => {}} isLoading={false} />);

    const todoBtn = screen.getByRole('button', { name: /todo/i });
    expect(todoBtn).toHaveAttribute('aria-pressed', 'true');

    fireEvent.click(todoBtn);
    expect(todoBtn).toHaveAttribute('aria-pressed', 'false');

    fireEvent.click(screen.getByRole('button', { name: /сбросить фильтры/i }));
    expect(todoBtn).toHaveAttribute('aria-pressed', 'true');
  });

  it('resets release checkboxes', () => {
    render(<StoryMap project={baseProject} onUpdate={() => {}} onUnauthorized={() => {}} isLoading={false} />);

    const releaseCheckbox = screen.getByLabelText('R1');
    expect(releaseCheckbox).toBeChecked();

    fireEvent.click(releaseCheckbox);
    expect(releaseCheckbox).not.toBeChecked();

    fireEvent.click(screen.getByRole('button', { name: /сбросить фильтры/i }));
    expect(releaseCheckbox).toBeChecked();
  });

  it('updates search query and syncs url/localStorage', async () => {
    render(<StoryMap project={baseProject} onUpdate={() => {}} onUnauthorized={() => {}} isLoading={false} />);

    const input = screen.getByPlaceholderText(/поиск историй/i);
    fireEvent.change(input, { target: { value: 'login' } });
    expect(input).toHaveValue('login');

    await waitFor(() => {
      expect(window.history.replaceState).toHaveBeenCalled();
      expect(localStorage.setItem).toHaveBeenCalledWith(
        'storymap_filters_1',
        expect.stringContaining('"search":"login"'),
      );
    });
  });

  it('shows skeleton when loading', () => {
    render(<StoryMap project={baseProject} onUpdate={() => {}} onUnauthorized={() => {}} isLoading />);
    expect(screen.getByTestId('storymap-skeleton')).toBeInTheDocument();
  });
});


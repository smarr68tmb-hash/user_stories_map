import { renderHook } from '@testing-library/react';
import { useDnD } from './useDnD';

const makeLoadingGuards = (overrides = {}) => ({
  isMoving: vi.fn(() => false),
  isUpdating: vi.fn(() => false),
  isDeleting: vi.fn(() => false),
  isChangingStatus: vi.fn(() => false),
  ...overrides,
});

describe('useDnD', () => {
  it('disables task drag when moving/updating/deleting or editing/pending', () => {
    const taskLoading = makeLoadingGuards({
      isMoving: vi.fn((id) => id === 1),
      isUpdating: vi.fn(() => false),
      isDeleting: vi.fn(() => false),
    });

    const { result } = renderHook(() =>
      useDnD({
        taskLoading,
        storyLoading: makeLoadingGuards(),
        editingTaskId: 2,
        pendingDeleteTaskId: 3,
      }),
    );

    expect(result.current.isTaskHandleDisabled(1)).toBe(true); // moving
    expect(result.current.isTaskHandleDisabled(2)).toBe(true); // editing
    expect(result.current.isTaskHandleDisabled(3)).toBe(true); // pending delete
    expect(result.current.isTaskHandleDisabled(999)).toBe(false);
    expect(result.current.isTaskDragDisabled(1)).toBe(true);
  });

  it('disables story drag when loading or editing', () => {
    const storyLoading = makeLoadingGuards({
      isMoving: vi.fn((id) => id === 10),
      isDeleting: vi.fn((id) => id === 11),
      isUpdating: vi.fn(() => false),
      isChangingStatus: vi.fn((id) => id === 12),
    });

    const { result } = renderHook(() =>
      useDnD({
        storyLoading,
        taskLoading: makeLoadingGuards(),
        editingStoryId: 13,
      }),
    );

    expect(result.current.isStoryHandleDisabled(10)).toBe(true); // moving
    expect(result.current.isStoryHandleDisabled(11)).toBe(true); // deleting
    expect(result.current.isStoryHandleDisabled(12)).toBe(true); // status change
    expect(result.current.isStoryHandleDisabled(13)).toBe(true); // editing
    expect(result.current.isStoryHandleDisabled(999)).toBe(false);
    expect(result.current.isStoryDragDisabled(10)).toBe(true);
  });
});


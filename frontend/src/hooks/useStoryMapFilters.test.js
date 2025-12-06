import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import useStoryMapFilters from './useStoryMapFilters';
import { STATUS_OPTIONS } from '../theme/tokens';

const makeProject = () => ({
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
          title: 'Task A',
          position: 1,
          stories: [
            { id: 1, title: 'Login', description: 'Login story', release_id: 10, status: 'todo' },
            { id: 2, title: 'Logout', description: 'Logout story', release_id: 11, status: 'done' },
          ],
        },
      ],
    },
  ],
});

describe('useStoryMapFilters', () => {
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

  it('initializes with all statuses and releases and toggles/reset correctly', () => {
    const project = makeProject();
    const { result } = renderHook(() => useStoryMapFilters({ project }));

    expect(result.current.statusFilter).toEqual(STATUS_OPTIONS.map((s) => s.value));
    expect(result.current.releaseFilter).toEqual(project.releases.map((r) => r.id));

    act(() => {
      result.current.toggleStatus('todo');
    });
    expect(result.current.statusFilter).not.toContain('todo');

    act(() => {
      result.current.toggleRelease(10);
    });
    expect(result.current.releaseFilter).not.toContain(10);

    act(() => {
      result.current.handleResetFilters();
    });
    expect(result.current.statusFilter).toEqual(STATUS_OPTIONS.map((s) => s.value));
    expect(result.current.releaseFilter).toEqual(project.releases.map((r) => r.id));
  });

  it('filters stories by search query', () => {
    const project = makeProject();
    const { result } = renderHook(() => useStoryMapFilters({ project }));

    act(() => {
      result.current.setSearchQuery('logout');
    });

    const stories =
      result.current.filteredProject.activities[0].tasks[0].stories.map((s) => s.title);
    expect(stories).toEqual(['Logout']);
  });

  it('persists filters to url and localStorage when search changes', () => {
    const project = makeProject();
    const { result } = renderHook(() => useStoryMapFilters({ project }));

    act(() => {
      result.current.setSearchQuery('login');
    });

    expect(localStorage.setItem).toHaveBeenCalledWith(
      'storymap_filters_1',
      expect.stringContaining('"search":"login"'),
    );
    expect(window.history.replaceState).toHaveBeenCalled();
  });

  it('computes release progress with filtered data', () => {
    const project = makeProject();
    const { result } = renderHook(() => useStoryMapFilters({ project }));

    expect(result.current.releaseProgress[10]).toEqual({ total: 1, done: 0, percent: 0 });
    expect(result.current.releaseProgress[11]).toEqual({ total: 1, done: 1, percent: 100 });
  });
});


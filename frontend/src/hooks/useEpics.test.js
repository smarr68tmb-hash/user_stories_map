import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useEpics } from './useEpics';
import { epics } from '../api';
import handleApiError from '../utils/handleApiError';

// Mock API module
vi.mock('../api', () => ({
  epics: {
    generate: vi.fn(),
    getByProject: vi.fn(),
    update: vi.fn(),
    addStory: vi.fn(),
    removeStory: vi.fn(),
    accept: vi.fn(),
    reject: vi.fn(),
  },
}));

// Mock handleApiError
vi.mock('../utils/handleApiError', () => ({
  default: vi.fn(),
}));

describe('useEpics', () => {
  const mockProject = { id: 1, name: 'Test Project' };
  const mockToast = {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  };
  const mockOnUnauthorized = vi.fn();
  const mockRefreshProject = vi.fn().mockResolvedValue({});

  const mockEpics = [
    {
      id: 1,
      title: 'Epic 1',
      description: 'Description 1',
      confidence_score: 0.85,
      stories: [{ id: 1, title: 'Story 1' }],
    },
    {
      id: 2,
      title: 'Epic 2',
      description: 'Description 2',
      confidence_score: 0.75,
      stories: [{ id: 2, title: 'Story 2' }],
    },
  ];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Initial State', () => {
    it('should have correct initial state', async () => {
      epics.getByProject.mockResolvedValue({ data: [] });

      const { result } = renderHook(() =>
        useEpics({
          project: mockProject,
          refreshProject: mockRefreshProject,
          onUnauthorized: mockOnUnauthorized,
          toast: mockToast,
        })
      );

      // Изначально fetch запускается автоматически через useEffect
      await waitFor(() => {
        expect(result.current.loading.fetch).toBe(false);
      });

      expect(result.current.epics).toEqual([]);
      expect(result.current.loading.generate).toBe(false);
      expect(result.current.loading.fetch).toBe(false);
    });
  });

  describe('fetchEpics', () => {
    it('should fetch epics on mount when project exists', async () => {
      epics.getByProject.mockResolvedValue({ data: mockEpics });

      const { result } = renderHook(() =>
        useEpics({
          project: mockProject,
          refreshProject: mockRefreshProject,
          onUnauthorized: mockOnUnauthorized,
          toast: mockToast,
        })
      );

      await waitFor(() => {
        expect(result.current.loading.fetch).toBe(false);
      });

      expect(epics.getByProject).toHaveBeenCalledWith(mockProject.id);
      expect(result.current.epics).toEqual(mockEpics);
    });

    it('should not fetch epics when project does not exist', () => {
      renderHook(() =>
        useEpics({
          project: null,
          refreshProject: mockRefreshProject,
          onUnauthorized: mockOnUnauthorized,
          toast: mockToast,
        })
      );

      expect(epics.getByProject).not.toHaveBeenCalled();
    });

    it('should handle fetch error', async () => {
      const error = new Error('Fetch failed');
      epics.getByProject.mockRejectedValue(error);

      renderHook(() =>
        useEpics({
          project: mockProject,
          refreshProject: mockRefreshProject,
          onUnauthorized: mockOnUnauthorized,
          toast: mockToast,
        })
      );

      await waitFor(() => {
        expect(handleApiError).toHaveBeenCalledWith(error, mockToast, mockOnUnauthorized);
      });
    });
  });

  describe('generateEpics', () => {
    it('should generate epics successfully', async () => {
      const generateResponse = {
        data: {
          success: true,
          message: 'Generated 2 epics',
          epics: mockEpics,
          total_stories_grouped: 2,
          ungrouped_stories_count: 0,
        },
      };

      epics.generate.mockResolvedValue(generateResponse);
      epics.getByProject.mockResolvedValue({ data: mockEpics });

      const { result } = renderHook(() =>
        useEpics({
          project: mockProject,
          refreshProject: mockRefreshProject,
          onUnauthorized: mockOnUnauthorized,
          toast: mockToast,
        })
      );

      // Ждем завершения начального fetch
      await waitFor(() => {
        expect(result.current.loading.fetch).toBe(false);
      });

      let generateResult;
      await act(async () => {
        generateResult = await result.current.generateEpics(3, 7);
      });

      expect(epics.generate).toHaveBeenCalledWith(mockProject.id, { min_epics: 3, max_epics: 7 });
      expect(mockToast.success).toHaveBeenCalledWith('Generated 2 epics');
      expect(mockRefreshProject).toHaveBeenCalled();
      expect(generateResult).toEqual(generateResponse.data);
    });

    it('should not generate when project does not exist', async () => {
      const { result } = renderHook(() =>
        useEpics({
          project: null,
          refreshProject: mockRefreshProject,
          onUnauthorized: mockOnUnauthorized,
          toast: mockToast,
        })
      );

      await act(async () => {
        await result.current.generateEpics();
      });

      expect(epics.generate).not.toHaveBeenCalled();
    });

    it('should handle generate error', async () => {
      const error = new Error('Generate failed');
      epics.generate.mockRejectedValue(error);

      const { result } = renderHook(() =>
        useEpics({
          project: mockProject,
          refreshProject: mockRefreshProject,
          onUnauthorized: mockOnUnauthorized,
          toast: mockToast,
        })
      );

      await act(async () => {
        try {
          await result.current.generateEpics();
        } catch (e) {
          expect(e).toBe(error);
        }
      });

      expect(handleApiError).toHaveBeenCalledWith(error, mockToast, mockOnUnauthorized);
    });
  });

  describe('updateEpic', () => {
    it('should update epic successfully', async () => {
      epics.update.mockResolvedValue({});
      epics.getByProject.mockResolvedValue({ data: mockEpics });

      const { result } = renderHook(() =>
        useEpics({
          project: mockProject,
          refreshProject: mockRefreshProject,
          onUnauthorized: mockOnUnauthorized,
          toast: mockToast,
        })
      );

      const updates = { title: 'Updated Title', description: 'Updated Description' };

      await act(async () => {
        await result.current.updateEpic(1, updates);
      });

      expect(epics.update).toHaveBeenCalledWith(1, updates);
      expect(mockToast.success).toHaveBeenCalledWith('Эпик обновлен');
      expect(epics.getByProject).toHaveBeenCalled();
    });

    it('should handle update error', async () => {
      const error = new Error('Update failed');
      epics.update.mockRejectedValue(error);

      const { result } = renderHook(() =>
        useEpics({
          project: mockProject,
          refreshProject: mockRefreshProject,
          onUnauthorized: mockOnUnauthorized,
          toast: mockToast,
        })
      );

      await act(async () => {
        await result.current.updateEpic(1, { title: 'New Title' });
      });

      expect(handleApiError).toHaveBeenCalledWith(error, mockToast, mockOnUnauthorized);
    });
  });

  describe('addStoryToEpic', () => {
    it('should add story to epic successfully', async () => {
      epics.addStory.mockResolvedValue({});
      epics.getByProject.mockResolvedValue({ data: mockEpics });

      const { result } = renderHook(() =>
        useEpics({
          project: mockProject,
          refreshProject: mockRefreshProject,
          onUnauthorized: mockOnUnauthorized,
          toast: mockToast,
        })
      );

      await act(async () => {
        await result.current.addStoryToEpic(1, 10);
      });

      expect(epics.addStory).toHaveBeenCalledWith(1, 10);
      expect(mockToast.success).toHaveBeenCalledWith('История добавлена в эпик');
      expect(mockRefreshProject).toHaveBeenCalled();
    });

    it('should handle add story error', async () => {
      const error = new Error('Add story failed');
      epics.addStory.mockRejectedValue(error);

      const { result } = renderHook(() =>
        useEpics({
          project: mockProject,
          refreshProject: mockRefreshProject,
          onUnauthorized: mockOnUnauthorized,
          toast: mockToast,
        })
      );

      await act(async () => {
        await result.current.addStoryToEpic(1, 10);
      });

      expect(handleApiError).toHaveBeenCalledWith(error, mockToast, mockOnUnauthorized);
    });
  });

  describe('removeStoryFromEpic', () => {
    it('should remove story from epic successfully', async () => {
      epics.removeStory.mockResolvedValue({});
      epics.getByProject.mockResolvedValue({ data: mockEpics });

      const { result } = renderHook(() =>
        useEpics({
          project: mockProject,
          refreshProject: mockRefreshProject,
          onUnauthorized: mockOnUnauthorized,
          toast: mockToast,
        })
      );

      await act(async () => {
        await result.current.removeStoryFromEpic(1, 10);
      });

      expect(epics.removeStory).toHaveBeenCalledWith(1, 10);
      expect(mockToast.success).toHaveBeenCalledWith('История удалена из эпика');
      expect(mockRefreshProject).toHaveBeenCalled();
    });

    it('should handle remove story error', async () => {
      const error = new Error('Remove story failed');
      epics.removeStory.mockRejectedValue(error);

      const { result } = renderHook(() =>
        useEpics({
          project: mockProject,
          refreshProject: mockRefreshProject,
          onUnauthorized: mockOnUnauthorized,
          toast: mockToast,
        })
      );

      await act(async () => {
        await result.current.removeStoryFromEpic(1, 10);
      });

      expect(handleApiError).toHaveBeenCalledWith(error, mockToast, mockOnUnauthorized);
    });
  });

  describe('acceptEpic', () => {
    it('should accept epic successfully', async () => {
      epics.accept.mockResolvedValue({});

      const { result } = renderHook(() =>
        useEpics({
          project: mockProject,
          refreshProject: mockRefreshProject,
          onUnauthorized: mockOnUnauthorized,
          toast: mockToast,
        })
      );

      await act(async () => {
        await result.current.acceptEpic(1);
      });

      expect(epics.accept).toHaveBeenCalledWith(1);
      expect(mockToast.success).toHaveBeenCalledWith('Эпик принят');
    });

    it('should handle accept error', async () => {
      const error = new Error('Accept failed');
      epics.accept.mockRejectedValue(error);

      const { result } = renderHook(() =>
        useEpics({
          project: mockProject,
          refreshProject: mockRefreshProject,
          onUnauthorized: mockOnUnauthorized,
          toast: mockToast,
        })
      );

      await act(async () => {
        await result.current.acceptEpic(1);
      });

      expect(handleApiError).toHaveBeenCalledWith(error, mockToast, mockOnUnauthorized);
    });
  });

  describe('rejectEpic', () => {
    it('should reject epic successfully', async () => {
      epics.reject.mockResolvedValue({});
      epics.getByProject.mockResolvedValue({ data: [] });

      const { result } = renderHook(() =>
        useEpics({
          project: mockProject,
          refreshProject: mockRefreshProject,
          onUnauthorized: mockOnUnauthorized,
          toast: mockToast,
        })
      );

      await act(async () => {
        await result.current.rejectEpic(1);
      });

      expect(epics.reject).toHaveBeenCalledWith(1);
      expect(mockToast.success).toHaveBeenCalledWith('Эпик отклонен и удален');
      expect(mockRefreshProject).toHaveBeenCalled();
    });

    it('should handle reject error', async () => {
      const error = new Error('Reject failed');
      epics.reject.mockRejectedValue(error);

      const { result } = renderHook(() =>
        useEpics({
          project: mockProject,
          refreshProject: mockRefreshProject,
          onUnauthorized: mockOnUnauthorized,
          toast: mockToast,
        })
      );

      await act(async () => {
        await result.current.rejectEpic(1);
      });

      expect(handleApiError).toHaveBeenCalledWith(error, mockToast, mockOnUnauthorized);
    });
  });

  describe('Loading States', () => {
    it('should set loading state during generate', async () => {
      const generateResponse = {
        data: {
          success: true,
          message: 'Generated epics',
          epics: mockEpics,
          total_stories_grouped: 2,
          ungrouped_stories_count: 0,
        },
      };
      epics.generate.mockImplementation(() => new Promise((resolve) => setTimeout(() => resolve(generateResponse), 100)));
      epics.getByProject.mockResolvedValue({ data: mockEpics });

      const { result } = renderHook(() =>
        useEpics({
          project: mockProject,
          refreshProject: mockRefreshProject,
          onUnauthorized: mockOnUnauthorized,
          toast: mockToast,
        })
      );

      // Ждем завершения начального fetch
      await waitFor(() => {
        expect(result.current.loading.fetch).toBe(false);
      });

      act(() => {
        result.current.generateEpics();
      });

      expect(result.current.loading.generate).toBe(true);

      await waitFor(() => {
        expect(result.current.loading.generate).toBe(false);
      });
    });

    it('should set loading state during update', async () => {
      epics.update.mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 100)));
      epics.getByProject.mockResolvedValue({ data: mockEpics });

      const { result } = renderHook(() =>
        useEpics({
          project: mockProject,
          refreshProject: mockRefreshProject,
          onUnauthorized: mockOnUnauthorized,
          toast: mockToast,
        })
      );

      // Ждем завершения начального fetch
      await waitFor(() => {
        expect(result.current.loading.fetch).toBe(false);
      });

      act(() => {
        result.current.updateEpic(1, { title: 'New Title' });
      });

      expect(result.current.loading.update[1]).toBe(true);

      await waitFor(() => {
        expect(result.current.loading.update[1]).toBe(false);
      });
    });
  });
});


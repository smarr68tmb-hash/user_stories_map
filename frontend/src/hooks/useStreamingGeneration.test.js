/**
 * Тесты для useStreamingGeneration hook
 *
 * Проверяем:
 * 1. Обновление progress при получении SSE событий
 * 2. Сохранение analysisResults
 * 3. Обработку ошибок EventSource
 * 4. Закрытие соединения при complete
 * 5. Ручную отмену streaming
 */

import { renderHook, act, waitFor } from '@testing-library/react';
import { useStreamingGeneration } from './useStreamingGeneration';

// Mock EventSource
class MockEventSource {
  constructor(url) {
    this.url = url;
    this.listeners = {};
    this.readyState = 1; // OPEN

    // Сохраняем экземпляр для доступа в тестах
    MockEventSource.instance = this;
  }

  addEventListener(event, handler) {
    this.listeners[event] = handler;
  }

  close() {
    this.readyState = 2; // CLOSED
    MockEventSource.closed = true;
  }

  // Вспомогательный метод для симуляции события
  simulateMessage(data) {
    if (this.onmessage) {
      this.onmessage({ data: JSON.stringify(data) });
    }
  }

  // Вспомогательный метод для симуляции ошибки
  simulateError(error) {
    if (this.onerror) {
      this.onerror(error);
    }
  }
}

// Сбрасываем флаги перед каждым тестом
MockEventSource.instance = null;
MockEventSource.closed = false;

global.EventSource = MockEventSource;

describe('useStreamingGeneration', () => {
  beforeEach(() => {
    MockEventSource.instance = null;
    MockEventSource.closed = false;
  });

  describe('Initial State', () => {
    it('should have correct initial state', () => {
      const { result } = renderHook(() => useStreamingGeneration());

      expect(result.current.progress).toBe(0);
      expect(result.current.stage).toBe('idle');
      expect(result.current.analysisResults).toBe(null);
      expect(result.current.stats).toBe(null);
      expect(result.current.isStreaming).toBe(false);
      expect(result.current.error).toBe(null);
    });
  });

  describe('Progress Updates', () => {
    it('should update progress on enhancing event', async () => {
      const { result } = renderHook(() => useStreamingGeneration());

      // Запускаем генерацию
      act(() => {
        result.current.generateWithStreaming('Test requirements', true, false);
      });

      // Проверяем, что EventSource создан
      expect(MockEventSource.instance).not.toBe(null);
      expect(result.current.isStreaming).toBe(true);

      // Симулируем SSE событие
      act(() => {
        MockEventSource.instance.simulateMessage({
          type: 'enhancing',
          progress: 10,
          stage: 'enhancement'
        });
      });

      // Проверяем обновление
      expect(result.current.progress).toBe(10);
      expect(result.current.stage).toBe('enhancing');
    });

    it('should update progress on generating event', async () => {
      const { result } = renderHook(() => useStreamingGeneration());

      act(() => {
        result.current.generateWithStreaming('Test', false, false);
      });

      act(() => {
        MockEventSource.instance.simulateMessage({
          type: 'generating',
          progress: 50,
          activities: 3,
          tasks: 8,
          stories: 15
        });
      });

      expect(result.current.progress).toBe(50);
      expect(result.current.stage).toBe('generating');
      expect(result.current.stats).toEqual({
        activities: 3,
        tasks: 8,
        stories: 15
      });
    });

    it('should update progress on validating event', async () => {
      const { result } = renderHook(() => useStreamingGeneration());

      act(() => {
        result.current.generateWithStreaming('Test', false, false);
      });

      act(() => {
        MockEventSource.instance.simulateMessage({
          type: 'validating',
          progress: 80
        });
      });

      expect(result.current.progress).toBe(80);
      expect(result.current.stage).toBe('validating');
    });

    it('should update progress on saving event', async () => {
      const { result } = renderHook(() => useStreamingGeneration());

      act(() => {
        result.current.generateWithStreaming('Test', false, false);
      });

      act(() => {
        MockEventSource.instance.simulateMessage({
          type: 'saving',
          progress: 90
        });
      });

      expect(result.current.progress).toBe(90);
      expect(result.current.stage).toBe('saving');
    });
  });

  describe('Analysis Results', () => {
    it('should store analysis results from analysis event', async () => {
      const { result } = renderHook(() => useStreamingGeneration());

      act(() => {
        result.current.generateWithStreaming('Test', false, false);
      });

      const analysisData = {
        type: 'analysis',
        progress: 85,
        duplicates: 3,
        similar: 2,
        score: 75,
        issues: ['Issue 1', 'Issue 2', 'Issue 3'],
        total_issues: 5
      };

      act(() => {
        MockEventSource.instance.simulateMessage(analysisData);
      });

      expect(result.current.analysisResults).toEqual({
        duplicates: 3,
        similar: 2,
        score: 75,
        issues: ['Issue 1', 'Issue 2', 'Issue 3'],
        totalIssues: 5
      });
      expect(result.current.progress).toBe(85);
    });

    it('should handle analysis event with zero duplicates', async () => {
      const { result } = renderHook(() => useStreamingGeneration());

      act(() => {
        result.current.generateWithStreaming('Test', false, false);
      });

      act(() => {
        MockEventSource.instance.simulateMessage({
          type: 'analysis',
          progress: 85,
          duplicates: 0,
          similar: 0,
          score: 95,
          issues: [],
          total_issues: 0
        });
      });

      expect(result.current.analysisResults).toEqual({
        duplicates: 0,
        similar: 0,
        score: 95,
        issues: [],
        totalIssues: 0
      });
    });
  });

  describe('Complete Event', () => {
    it('should resolve promise with project data on complete', async () => {
      const { result } = renderHook(() => useStreamingGeneration());

      let resolvedValue;
      act(() => {
        result.current.generateWithStreaming('Test', false, false).then(value => {
          resolvedValue = value;
        });
      });

      act(() => {
        MockEventSource.instance.simulateMessage({
          type: 'complete',
          progress: 100,
          project_id: 42,
          project_name: 'Test Project',
          stats: {
            activities: 5,
            tasks: 12,
            stories: 25,
            score: 88,
            duplicates: 1
          }
        });
      });

      await waitFor(() => {
        expect(resolvedValue).toEqual({
          projectId: 42,
          projectName: 'Test Project',
          stats: {
            activities: 5,
            tasks: 12,
            stories: 25,
            score: 88,
            duplicates: 1
          }
        });
      });

      expect(result.current.progress).toBe(100);
      expect(result.current.stage).toBe('complete');
      expect(result.current.isStreaming).toBe(false);
      expect(MockEventSource.closed).toBe(true);
    });

    it('should store final stats from complete event', async () => {
      const { result } = renderHook(() => useStreamingGeneration());

      act(() => {
        result.current.generateWithStreaming('Test', false, false);
      });

      const finalStats = {
        activities: 10,
        tasks: 30,
        stories: 60,
        score: 92,
        duplicates: 0
      };

      act(() => {
        MockEventSource.instance.simulateMessage({
          type: 'complete',
          progress: 100,
          project_id: 1,
          project_name: 'Test',
          stats: finalStats
        });
      });

      expect(result.current.stats).toEqual(finalStats);
    });
  });

  describe('Error Handling', () => {
    it('should handle error event from server', async () => {
      const { result } = renderHook(() => useStreamingGeneration());

      let rejectedError;
      act(() => {
        result.current.generateWithStreaming('Test', false, false).catch(err => {
          rejectedError = err;
        });
      });

      act(() => {
        MockEventSource.instance.simulateMessage({
          type: 'error',
          message: 'AI service unavailable'
        });
      });

      await waitFor(() => {
        expect(rejectedError).toBeInstanceOf(Error);
        expect(rejectedError.message).toBe('AI service unavailable');
      });

      expect(result.current.stage).toBe('error');
      expect(result.current.error).toBe('AI service unavailable');
      expect(result.current.isStreaming).toBe(false);
      expect(MockEventSource.closed).toBe(true);
    });

    it('should handle EventSource connection error', async () => {
      const { result } = renderHook(() => useStreamingGeneration());

      let rejectedError;
      act(() => {
        result.current.generateWithStreaming('Test', false, false).catch(err => {
          rejectedError = err;
        });
      });

      act(() => {
        MockEventSource.instance.simulateError(new Error('Connection failed'));
      });

      await waitFor(() => {
        expect(rejectedError).toBeInstanceOf(Error);
        expect(rejectedError.message).toBe('SSE connection failed');
      });

      expect(result.current.stage).toBe('error');
      expect(result.current.error).toBe('Connection lost. Please try again.');
      expect(result.current.isStreaming).toBe(false);
      expect(MockEventSource.closed).toBe(true);
    });

    it('should handle malformed JSON in event', async () => {
      const { result } = renderHook(() => useStreamingGeneration());

      // Подавляем console.error для этого теста
      const originalError = console.error;
      console.error = jest.fn();

      act(() => {
        result.current.generateWithStreaming('Test', false, false);
      });

      act(() => {
        if (MockEventSource.instance.onmessage) {
          MockEventSource.instance.onmessage({ data: 'invalid json{' });
        }
      });

      // Проверяем, что ошибка залогирована
      expect(console.error).toHaveBeenCalled();

      // Восстанавливаем console.error
      console.error = originalError;
    });
  });

  describe('Manual Cancellation', () => {
    it('should cancel streaming when cancelStreaming is called', async () => {
      const { result } = renderHook(() => useStreamingGeneration());

      act(() => {
        result.current.generateWithStreaming('Test', false, false);
      });

      expect(result.current.isStreaming).toBe(true);

      act(() => {
        result.current.cancelStreaming();
      });

      expect(result.current.isStreaming).toBe(false);
      expect(result.current.stage).toBe('idle');
      expect(MockEventSource.closed).toBe(true);
    });

    it('should handle cancelStreaming when no stream is active', () => {
      const { result } = renderHook(() => useStreamingGeneration());

      // Не должно быть ошибки
      act(() => {
        result.current.cancelStreaming();
      });

      expect(result.current.isStreaming).toBe(false);
    });
  });

  describe('Query Parameters', () => {
    it('should build correct URL with enhancement enabled', async () => {
      const { result } = renderHook(() => useStreamingGeneration());

      act(() => {
        result.current.generateWithStreaming('My requirements', true, false);
      });

      const url = MockEventSource.instance.url;
      expect(url).toContain('/api/generate-map/stream');
      expect(url).toContain('text=My%20requirements');
      expect(url).toContain('skip_enhancement=false');
      expect(url).toContain('use_agent=false');
    });

    it('should build correct URL with agent enabled', async () => {
      const { result } = renderHook(() => useStreamingGeneration());

      act(() => {
        result.current.generateWithStreaming('Test', false, true);
      });

      const url = MockEventSource.instance.url;
      expect(url).toContain('use_agent=true');
    });

    it('should build correct URL with enhancement disabled', async () => {
      const { result } = renderHook(() => useStreamingGeneration());

      act(() => {
        result.current.generateWithStreaming('Test', false, false);
      });

      const url = MockEventSource.instance.url;
      expect(url).toContain('skip_enhancement=true');
    });
  });

  describe('State Reset on New Generation', () => {
    it('should reset state when starting new generation', async () => {
      const { result } = renderHook(() => useStreamingGeneration());

      // Первая генерация
      act(() => {
        result.current.generateWithStreaming('Test 1', false, false);
      });

      act(() => {
        MockEventSource.instance.simulateMessage({
          type: 'generating',
          progress: 50
        });
      });

      act(() => {
        MockEventSource.instance.simulateMessage({
          type: 'analysis',
          progress: 85,
          duplicates: 5,
          score: 60,
          issues: [],
          total_issues: 0
        });
      });

      expect(result.current.progress).toBe(85);
      expect(result.current.analysisResults.duplicates).toBe(5);

      // Вторая генерация - должен сбросить state
      act(() => {
        result.current.generateWithStreaming('Test 2', false, false);
      });

      expect(result.current.progress).toBe(0);
      expect(result.current.stage).toBe('idle');
      expect(result.current.analysisResults).toBe(null);
      expect(result.current.stats).toBe(null);
      expect(result.current.error).toBe(null);
    });
  });

  describe('Unknown Event Types', () => {
    it('should log warning for unknown event types', async () => {
      const { result } = renderHook(() => useStreamingGeneration());

      // Подавляем console.warn
      const originalWarn = console.warn;
      console.warn = jest.fn();

      act(() => {
        result.current.generateWithStreaming('Test', false, false);
      });

      act(() => {
        MockEventSource.instance.simulateMessage({
          type: 'unknown_event_type',
          data: 'something'
        });
      });

      // Проверяем, что warning залогирован
      expect(console.warn).toHaveBeenCalledWith(
        '[SSE] Unknown event type:',
        'unknown_event_type'
      );

      console.warn = originalWarn;
    });
  });
});

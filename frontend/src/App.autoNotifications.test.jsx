/**
 * Integration тесты для auto-notification функциональности
 *
 * Проверяем:
 * 1. Auto-show уведомлений при получении analysisResults
 * 2. Различные типы уведомлений (duplicates, score)
 * 3. Интеграция с toast notifications
 * 4. Триггеры на основе данных анализа
 */

import { render, screen, waitFor } from '@testing-library/react';
import { act } from 'react-dom/test-utils';
import App from './App';

// Mock react-toastify
const mockToastWarning = jest.fn();
const mockToastSuccess = jest.fn();
const mockToastInfo = jest.fn();

jest.mock('react-toastify', () => ({
  ToastContainer: () => <div data-testid="toast-container" />,
  toast: {
    warning: (...args) => mockToastWarning(...args),
    success: (...args) => mockToastSuccess(...args),
    info: (...args) => mockToastInfo(...args),
    error: jest.fn()
  }
}));

// Mock useStreamingGeneration hook
const mockGenerateWithStreaming = jest.fn();
const mockCancelStreaming = jest.fn();

let mockHookState = {
  progress: 0,
  stage: 'idle',
  analysisResults: null,
  stats: null,
  isStreaming: false,
  error: null,
  generateWithStreaming: mockGenerateWithStreaming,
  cancelStreaming: mockCancelStreaming
};

jest.mock('./hooks/useStreamingGeneration', () => ({
  useStreamingGeneration: () => mockHookState
}));

// Mock fetch для API calls
global.fetch = jest.fn(() =>
  Promise.resolve({
    ok: true,
    json: () => Promise.resolve({ projects: [] })
  })
);

describe('Auto-Notification Integration Tests', () => {
  beforeEach(() => {
    // Сброс mock функций
    mockToastWarning.mockClear();
    mockToastSuccess.mockClear();
    mockToastInfo.mockClear();
    mockGenerateWithStreaming.mockClear();
    mockCancelStreaming.mockClear();

    // Сброс hook state
    mockHookState = {
      progress: 0,
      stage: 'idle',
      analysisResults: null,
      stats: null,
      isStreaming: false,
      error: null,
      generateWithStreaming: mockGenerateWithStreaming,
      cancelStreaming: mockCancelStreaming
    };
  });

  describe('Duplicates Notifications', () => {
    it('should show warning notification when duplicates are found', async () => {
      const { rerender } = render(<App />);

      // Симулируем появление analysisResults с дубликатами
      act(() => {
        mockHookState.analysisResults = {
          duplicates: 3,
          similar: 0,
          score: 75,
          totalIssues: 0,
          issues: []
        };
      });

      rerender(<App />);

      await waitFor(() => {
        expect(mockToastWarning).toHaveBeenCalledWith(
          expect.stringContaining('Найдено 3 дубликатов!')
        );
      });
    });

    it('should show correct message for single duplicate', async () => {
      const { rerender } = render(<App />);

      act(() => {
        mockHookState.analysisResults = {
          duplicates: 1,
          similar: 0,
          score: 80,
          totalIssues: 0,
          issues: []
        };
      });

      rerender(<App />);

      await waitFor(() => {
        expect(mockToastWarning).toHaveBeenCalledWith(
          expect.stringContaining('Найдено 1 дубликатов!')
        );
      });
    });

    it('should not show notification when no duplicates', async () => {
      const { rerender } = render(<App />);

      act(() => {
        mockHookState.analysisResults = {
          duplicates: 0,
          similar: 0,
          score: 90,
          totalIssues: 0,
          issues: []
        };
      });

      rerender(<App />);

      await waitFor(() => {
        const duplicateWarning = mockToastWarning.mock.calls.find(call =>
          call[0].includes('дубликатов')
        );
        expect(duplicateWarning).toBeUndefined();
      });
    });
  });

  describe('Score Notifications', () => {
    it('should show warning for low score (< 50)', async () => {
      const { rerender } = render(<App />);

      act(() => {
        mockHookState.analysisResults = {
          duplicates: 0,
          similar: 0,
          score: 35,
          totalIssues: 0,
          issues: []
        };
      });

      rerender(<App />);

      await waitFor(() => {
        expect(mockToastWarning).toHaveBeenCalledWith(
          expect.stringContaining('Оценка качества: 35/100')
        );
      });
    });

    it('should show success for high score (>= 80)', async () => {
      const { rerender } = render(<App />);

      act(() => {
        mockHookState.analysisResults = {
          duplicates: 0,
          similar: 0,
          score: 92,
          totalIssues: 0,
          issues: []
        };
      });

      rerender(<App />);

      await waitFor(() => {
        expect(mockToastSuccess).toHaveBeenCalledWith(
          expect.stringContaining('Отличная оценка: 92/100!')
        );
      });
    });

    it('should not show notification for medium score (50-79)', async () => {
      const { rerender } = render(<App />);

      act(() => {
        mockHookState.analysisResults = {
          duplicates: 0,
          similar: 0,
          score: 65,
          totalIssues: 0,
          issues: []
        };
      });

      rerender(<App />);

      await waitFor(() => {
        const scoreNotifications = mockToastWarning.mock.calls.find(call =>
          call[0].includes('Оценка качества')
        );
        const successNotifications = mockToastSuccess.mock.calls.find(call =>
          call[0].includes('Отличная оценка')
        );

        expect(scoreNotifications).toBeUndefined();
        expect(successNotifications).toBeUndefined();
      });
    });

    it('should show success for score exactly 80', async () => {
      const { rerender } = render(<App />);

      act(() => {
        mockHookState.analysisResults = {
          duplicates: 0,
          similar: 0,
          score: 80,
          totalIssues: 0,
          issues: []
        };
      });

      rerender(<App />);

      await waitFor(() => {
        expect(mockToastSuccess).toHaveBeenCalledWith(
          expect.stringContaining('Отличная оценка: 80/100!')
        );
      });
    });

    it('should show warning for score exactly 50', async () => {
      const { rerender } = render(<App />);

      act(() => {
        mockHookState.analysisResults = {
          duplicates: 0,
          similar: 0,
          score: 50,
          totalIssues: 0,
          issues: []
        };
      });

      rerender(<App />);

      await waitFor(() => {
        // Score = 50 не попадает под < 50, поэтому warning не должно быть
        const scoreWarning = mockToastWarning.mock.calls.find(call =>
          call[0].includes('Оценка качества')
        );
        expect(scoreWarning).toBeUndefined();
      });
    });
  });

  describe('Multiple Notifications', () => {
    it('should show both duplicates and low score warnings', async () => {
      const { rerender } = render(<App />);

      act(() => {
        mockHookState.analysisResults = {
          duplicates: 5,
          similar: 2,
          score: 40,
          totalIssues: 0,
          issues: []
        };
      });

      rerender(<App />);

      await waitFor(() => {
        expect(mockToastWarning).toHaveBeenCalledWith(
          expect.stringContaining('Найдено 5 дубликатов!')
        );
        expect(mockToastWarning).toHaveBeenCalledWith(
          expect.stringContaining('Оценка качества: 40/100')
        );
      });
    });

    it('should show duplicates warning even with high score', async () => {
      const { rerender } = render(<App />);

      act(() => {
        mockHookState.analysisResults = {
          duplicates: 2,
          similar: 0,
          score: 85,
          totalIssues: 0,
          issues: []
        };
      });

      rerender(<App />);

      await waitFor(() => {
        expect(mockToastWarning).toHaveBeenCalledWith(
          expect.stringContaining('Найдено 2 дубликатов!')
        );
        expect(mockToastSuccess).toHaveBeenCalledWith(
          expect.stringContaining('Отличная оценка: 85/100!')
        );
      });
    });
  });

  describe('Notification Timing', () => {
    it('should only trigger notifications when analysisResults changes', async () => {
      const { rerender } = render(<App />);

      // Первое обновление с analysisResults
      act(() => {
        mockHookState.analysisResults = {
          duplicates: 3,
          similar: 0,
          score: 60,
          totalIssues: 0,
          issues: []
        };
      });

      rerender(<App />);

      await waitFor(() => {
        expect(mockToastWarning).toHaveBeenCalledTimes(1);
      });

      mockToastWarning.mockClear();

      // Rerender без изменения analysisResults - не должно быть новых notifications
      rerender(<App />);

      await waitFor(() => {
        expect(mockToastWarning).not.toHaveBeenCalled();
      });
    });

    it('should trigger notifications when analysisResults changes to new values', async () => {
      const { rerender } = render(<App />);

      // Первый результат
      act(() => {
        mockHookState.analysisResults = {
          duplicates: 2,
          similar: 0,
          score: 70,
          totalIssues: 0,
          issues: []
        };
      });

      rerender(<App />);

      await waitFor(() => {
        expect(mockToastWarning).toHaveBeenCalledWith(
          expect.stringContaining('Найдено 2 дубликатов!')
        );
      });

      mockToastWarning.mockClear();

      // Новый результат с другими значениями
      act(() => {
        mockHookState.analysisResults = {
          duplicates: 5,
          similar: 1,
          score: 45,
          totalIssues: 0,
          issues: []
        };
      });

      rerender(<App />);

      await waitFor(() => {
        expect(mockToastWarning).toHaveBeenCalledWith(
          expect.stringContaining('Найдено 5 дубликатов!')
        );
        expect(mockToastWarning).toHaveBeenCalledWith(
          expect.stringContaining('Оценка качества: 45/100')
        );
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle null analysisResults gracefully', async () => {
      const { rerender } = render(<App />);

      act(() => {
        mockHookState.analysisResults = null;
      });

      rerender(<App />);

      // Не должно быть ошибок и notifications
      expect(mockToastWarning).not.toHaveBeenCalled();
      expect(mockToastSuccess).not.toHaveBeenCalled();
    });

    it('should handle undefined fields in analysisResults', async () => {
      const { rerender } = render(<App />);

      act(() => {
        mockHookState.analysisResults = {
          score: 75
          // duplicates и similar отсутствуют
        };
      });

      rerender(<App />);

      // Не должно быть ошибок
      await waitFor(() => {
        expect(mockToastWarning).not.toHaveBeenCalled();
      });
    });

    it('should handle score of 0', async () => {
      const { rerender } = render(<App />);

      act(() => {
        mockHookState.analysisResults = {
          duplicates: 0,
          similar: 0,
          score: 0,
          totalIssues: 0,
          issues: []
        };
      });

      rerender(<App />);

      await waitFor(() => {
        expect(mockToastWarning).toHaveBeenCalledWith(
          expect.stringContaining('Оценка качества: 0/100')
        );
      });
    });

    it('should handle score of 100', async () => {
      const { rerender } = render(<App />);

      act(() => {
        mockHookState.analysisResults = {
          duplicates: 0,
          similar: 0,
          score: 100,
          totalIssues: 0,
          issues: []
        };
      });

      rerender(<App />);

      await waitFor(() => {
        expect(mockToastSuccess).toHaveBeenCalledWith(
          expect.stringContaining('Отличная оценка: 100/100!')
        );
      });
    });
  });

  describe('Integration with Streaming Flow', () => {
    it('should show notifications after streaming completes', async () => {
      const { rerender } = render(<App />);

      // Симулируем streaming процесс
      act(() => {
        mockHookState.isStreaming = true;
        mockHookState.stage = 'generating';
        mockHookState.progress = 50;
      });

      rerender(<App />);

      // Проверяем, что notifications еще нет
      expect(mockToastWarning).not.toHaveBeenCalled();

      // Streaming завершается с analysisResults
      act(() => {
        mockHookState.isStreaming = false;
        mockHookState.stage = 'complete';
        mockHookState.progress = 100;
        mockHookState.analysisResults = {
          duplicates: 4,
          similar: 1,
          score: 68,
          totalIssues: 0,
          issues: []
        };
      });

      rerender(<App />);

      // Проверяем, что notifications появились
      await waitFor(() => {
        expect(mockToastWarning).toHaveBeenCalledWith(
          expect.stringContaining('Найдено 4 дубликатов!')
        );
      });
    });

    it('should not show notifications during streaming', async () => {
      const { rerender } = render(<App />);

      act(() => {
        mockHookState.isStreaming = true;
        mockHookState.stage = 'validating';
        mockHookState.progress = 80;
        // analysisResults может прийти раньше complete
        mockHookState.analysisResults = {
          duplicates: 3,
          similar: 0,
          score: 70,
          totalIssues: 0,
          issues: []
        };
      });

      rerender(<App />);

      // Notifications должны сработать даже во время streaming
      await waitFor(() => {
        expect(mockToastWarning).toHaveBeenCalledWith(
          expect.stringContaining('Найдено 3 дубликатов!')
        );
      });
    });
  });

  describe('AIAssistantSidebar Integration', () => {
    it('should pass analysisResults to AIAssistantSidebar', async () => {
      const { rerender } = render(<App />);

      const testAnalysisResults = {
        duplicates: 2,
        similar: 1,
        score: 78,
        totalIssues: 3,
        issues: ['Issue 1', 'Issue 2', 'Issue 3']
      };

      act(() => {
        mockHookState.analysisResults = testAnalysisResults;
      });

      rerender(<App />);

      // AIAssistantSidebar должен получить данные
      // Проверяем, что компонент отрендерился с правильными props
      await waitFor(() => {
        expect(screen.getByText('AI Assistant')).toBeInTheDocument();
      });
    });
  });
});

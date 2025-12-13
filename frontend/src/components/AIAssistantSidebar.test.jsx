/**
 * Тесты для AIAssistantSidebar component
 *
 * Проверяем:
 * 1. Отображение score badge с правильным цветом
 * 2. Отображение warnings для дубликатов
 * 3. Collapse/expand функциональность
 * 4. Quick actions кнопки
 * 5. Рекомендации на основе analysisResults
 */

import { render, screen, fireEvent } from '@testing-library/react';
import { AIAssistantSidebar } from './AIAssistantSidebar';

describe('AIAssistantSidebar', () => {
  describe('Rendering', () => {
    it('should render null when no project and no analysisResults', () => {
      const { container } = render(
        <AIAssistantSidebar project={null} analysisResults={null} />
      );

      expect(container.firstChild).toBeNull();
    });

    it('should render when project is provided', () => {
      const mockProject = { id: 1, name: 'Test Project' };

      render(<AIAssistantSidebar project={mockProject} analysisResults={null} />);

      expect(screen.getByText('AI Assistant')).toBeInTheDocument();
      expect(screen.getByText('Анализ и рекомендации')).toBeInTheDocument();
    });

    it('should render when analysisResults are provided', () => {
      const mockAnalysis = {
        score: 75,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      expect(screen.getByText('AI Assistant')).toBeInTheDocument();
    });
  });

  describe('Score Badge', () => {
    it('should display score with green badge for score >= 80', () => {
      const mockAnalysis = {
        score: 85,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      const badge = screen.getByText('85/100');
      expect(badge).toHaveClass('bg-green-100');
      expect(badge).toHaveClass('text-green-800');
      expect(badge).toHaveClass('border-green-300');

      expect(screen.getByText('Отлично')).toBeInTheDocument();
    });

    it('should display score with yellow badge for 50 <= score < 80', () => {
      const mockAnalysis = {
        score: 65,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      const badge = screen.getByText('65/100');
      expect(badge).toHaveClass('bg-yellow-100');
      expect(badge).toHaveClass('text-yellow-800');
      expect(badge).toHaveClass('border-yellow-300');

      expect(screen.getByText('Хорошо')).toBeInTheDocument();
    });

    it('should display score with red badge for score < 50', () => {
      const mockAnalysis = {
        score: 35,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      const badge = screen.getByText('35/100');
      expect(badge).toHaveClass('bg-red-100');
      expect(badge).toHaveClass('text-red-800');
      expect(badge).toHaveClass('border-red-300');

      expect(screen.getByText('Требует улучшения')).toBeInTheDocument();
    });
  });

  describe('Duplicates Warning', () => {
    it('should display duplicates warning when duplicates > 0', () => {
      const mockAnalysis = {
        score: 75,
        duplicates: 3,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      expect(screen.getByText('Найдено дубликатов: 3')).toBeInTheDocument();
      expect(
        screen.getByText('Рекомендуется объединить или удалить похожие истории')
      ).toBeInTheDocument();
    });

    it('should not display duplicates warning when duplicates = 0', () => {
      const mockAnalysis = {
        score: 90,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      expect(screen.queryByText(/Найдено дубликатов/)).not.toBeInTheDocument();
    });
  });

  describe('Similar Stories Warning', () => {
    it('should display similar stories warning when similar > 0', () => {
      const mockAnalysis = {
        score: 75,
        duplicates: 0,
        similar: 2,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      expect(screen.getByText('Похожих историй: 2')).toBeInTheDocument();
      expect(screen.getByText('Проверьте на возможное дублирование')).toBeInTheDocument();
    });

    it('should not display similar stories warning when similar = 0', () => {
      const mockAnalysis = {
        score: 90,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      expect(screen.queryByText(/Похожих историй/)).not.toBeInTheDocument();
    });
  });

  describe('Issues Warning', () => {
    it('should display issues warning when totalIssues > 0', () => {
      const mockAnalysis = {
        score: 65,
        duplicates: 0,
        similar: 0,
        totalIssues: 5,
        issues: ['Issue 1', 'Issue 2', 'Issue 3', 'Issue 4', 'Issue 5']
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      expect(screen.getByText('Проблем найдено: 5')).toBeInTheDocument();
      expect(screen.getByText('Issue 1')).toBeInTheDocument();
      expect(screen.getByText('Issue 2')).toBeInTheDocument();
      expect(screen.getByText('Issue 3')).toBeInTheDocument();
    });

    it('should display only first 3 issues and show count', () => {
      const mockAnalysis = {
        score: 60,
        duplicates: 0,
        similar: 0,
        totalIssues: 8,
        issues: [
          'Issue 1',
          'Issue 2',
          'Issue 3',
          'Issue 4',
          'Issue 5',
          'Issue 6',
          'Issue 7',
          'Issue 8'
        ]
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      expect(screen.getByText('Issue 1')).toBeInTheDocument();
      expect(screen.getByText('Issue 2')).toBeInTheDocument();
      expect(screen.getByText('Issue 3')).toBeInTheDocument();
      expect(screen.getByText('+5 еще...')).toBeInTheDocument();

      expect(screen.queryByText('Issue 4')).not.toBeInTheDocument();
    });

    it('should not display issues warning when totalIssues = 0', () => {
      const mockAnalysis = {
        score: 95,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      expect(screen.queryByText(/Проблем найдено/)).not.toBeInTheDocument();
    });
  });

  describe('Perfect Score Message', () => {
    it('should display success message for perfect score', () => {
      const mockAnalysis = {
        score: 95,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      expect(screen.getByText('Отличная работа!')).toBeInTheDocument();
      expect(screen.getByText('Карта готова к использованию')).toBeInTheDocument();
    });

    it('should not display success message if score is high but duplicates exist', () => {
      const mockAnalysis = {
        score: 85,
        duplicates: 2,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      expect(screen.queryByText('Отличная работа!')).not.toBeInTheDocument();
    });

    it('should not display success message if score is high but issues exist', () => {
      const mockAnalysis = {
        score: 85,
        duplicates: 0,
        similar: 0,
        totalIssues: 3,
        issues: ['Issue 1', 'Issue 2', 'Issue 3']
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      expect(screen.queryByText('Отличная работа!')).not.toBeInTheDocument();
    });
  });

  describe('Recommendations', () => {
    it('should show recommendation to add acceptance criteria when score < 80', () => {
      const mockAnalysis = {
        score: 65,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      expect(
        screen.getByText(/Добавьте детальные критерии приемки к историям/)
      ).toBeInTheDocument();
    });

    it('should show recommendation to merge duplicates when duplicates > 0', () => {
      const mockAnalysis = {
        score: 90,
        duplicates: 3,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      expect(
        screen.getByText(/Объедините дублирующиеся истории в одну/)
      ).toBeInTheDocument();
    });

    it('should show MVP balance recommendation when project exists', () => {
      const mockProject = { id: 1, name: 'Test' };
      const mockAnalysis = {
        score: 80,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={mockProject} analysisResults={mockAnalysis} />);

      expect(screen.getByText(/Проверьте баланс между MVP и Release 1/)).toBeInTheDocument();
    });

    it('should always show drag-and-drop recommendation', () => {
      const mockAnalysis = {
        score: 100,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      expect(
        screen.getByText(/Используйте drag-and-drop для приоритизации/)
      ).toBeInTheDocument();
    });
  });

  describe('Collapse/Expand', () => {
    it('should be expanded by default', () => {
      const mockAnalysis = {
        score: 80,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      const { container } = render(
        <AIAssistantSidebar project={null} analysisResults={mockAnalysis} />
      );

      const sidebar = container.querySelector('.fixed');
      expect(sidebar).toHaveClass('w-80');
    });

    it('should collapse when toggle button is clicked', () => {
      const mockAnalysis = {
        score: 80,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      const { container } = render(
        <AIAssistantSidebar project={null} analysisResults={mockAnalysis} />
      );

      const toggleButton = screen.getByLabelText('Скрыть панель');
      fireEvent.click(toggleButton);

      const sidebar = container.querySelector('.fixed');
      expect(sidebar).toHaveClass('w-12');
    });

    it('should expand when toggle button is clicked again', () => {
      const mockAnalysis = {
        score: 80,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      const { container } = render(
        <AIAssistantSidebar project={null} analysisResults={mockAnalysis} />
      );

      const toggleButton = screen.getByLabelText('Скрыть панель');

      // Collapse
      fireEvent.click(toggleButton);
      expect(container.querySelector('.fixed')).toHaveClass('w-12');

      // Expand
      const expandButton = screen.getByLabelText('Показать панель');
      fireEvent.click(expandButton);
      expect(container.querySelector('.fixed')).toHaveClass('w-80');
    });

    it('should hide content when collapsed', () => {
      const mockAnalysis = {
        score: 80,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      const toggleButton = screen.getByLabelText('Скрыть панель');
      fireEvent.click(toggleButton);

      // Основной контент скрыт
      expect(screen.queryByText('Результаты анализа')).not.toBeInTheDocument();
      expect(screen.queryByText('Рекомендации')).not.toBeInTheDocument();
      expect(screen.queryByText('Быстрые действия')).not.toBeInTheDocument();
    });
  });

  describe('Quick Actions', () => {
    it('should render "Полный анализ" button when onRunFullAnalysis is provided', () => {
      const mockOnRunFullAnalysis = jest.fn();
      const mockAnalysis = {
        score: 80,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(
        <AIAssistantSidebar
          project={null}
          analysisResults={mockAnalysis}
          onRunFullAnalysis={mockOnRunFullAnalysis}
        />
      );

      const button = screen.getByText('Полный анализ');
      expect(button).toBeInTheDocument();
      expect(button).not.toBeDisabled();
    });

    it('should call onRunFullAnalysis when button is clicked', () => {
      const mockOnRunFullAnalysis = jest.fn();
      const mockAnalysis = {
        score: 80,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(
        <AIAssistantSidebar
          project={null}
          analysisResults={mockAnalysis}
          onRunFullAnalysis={mockOnRunFullAnalysis}
        />
      );

      const button = screen.getByText('Полный анализ');
      fireEvent.click(button);

      expect(mockOnRunFullAnalysis).toHaveBeenCalledTimes(1);
    });

    it('should not render "Полный анализ" button when onRunFullAnalysis is not provided', () => {
      const mockAnalysis = {
        score: 80,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      expect(screen.queryByText('Полный анализ')).not.toBeInTheDocument();
    });

    it('should render disabled export buttons', () => {
      const mockAnalysis = {
        score: 80,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      const jiraButton = screen.getByText('Экспорт в Jira (скоро)');
      const figjamButton = screen.getByText('Экспорт в FigJam (скоро)');

      expect(jiraButton).toBeDisabled();
      expect(figjamButton).toBeDisabled();
    });
  });

  describe('Footer', () => {
    it('should display auto-update notice', () => {
      const mockAnalysis = {
        score: 80,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      expect(
        screen.getByText('Анализ обновляется автоматически при изменении карты')
      ).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle missing issues array in analysisResults', () => {
      const mockAnalysis = {
        score: 70,
        duplicates: 0,
        similar: 0,
        totalIssues: 3
        // issues array отсутствует
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      expect(screen.getByText('Проблем найдено: 3')).toBeInTheDocument();
    });

    it('should handle score exactly equal to 80', () => {
      const mockAnalysis = {
        score: 80,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      const badge = screen.getByText('80/100');
      expect(badge).toHaveClass('bg-green-100');
      expect(screen.getByText('Отлично')).toBeInTheDocument();
    });

    it('should handle score exactly equal to 50', () => {
      const mockAnalysis = {
        score: 50,
        duplicates: 0,
        similar: 0,
        totalIssues: 0,
        issues: []
      };

      render(<AIAssistantSidebar project={null} analysisResults={mockAnalysis} />);

      const badge = screen.getByText('50/100');
      expect(badge).toHaveClass('bg-yellow-100');
      expect(screen.getByText('Хорошо')).toBeInTheDocument();
    });
  });
});

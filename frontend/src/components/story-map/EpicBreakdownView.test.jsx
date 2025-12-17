import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import EpicBreakdownView from './EpicBreakdownView';

// Mock useToast hook
vi.mock('../../hooks/useToast', () => ({
  useToast: () => ({
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
    warning: vi.fn(),
  }),
}));

describe('EpicBreakdownView', () => {
  const mockProject = { id: 1, name: 'Test Project' };
  const mockEpics = [
    {
      id: 1,
      title: 'Checkout Flow',
      description: 'User checkout process',
      confidence_score: 0.85,
      position: 0,
      stories: [
        { id: 1, title: 'Add to cart', status: 'done', description: 'Add items' },
        { id: 2, title: 'Payment', status: 'done', description: 'Process payment' },
        { id: 3, title: 'Order review', status: 'todo', description: 'Review order' },
        { id: 4, title: 'Confirmation', status: 'todo', description: 'Confirm order' },
      ],
    },
    {
      id: 2,
      title: 'User Authentication',
      description: 'Login and registration',
      confidence_score: 0.95,
      position: 1,
      stories: [
        { id: 5, title: 'Login', status: 'done', description: 'User login' },
        { id: 6, title: 'Register', status: 'done', description: 'User registration' },
        { id: 7, title: 'Password reset', status: 'done', description: 'Reset password' },
      ],
    },
    {
      id: 3,
      title: 'Low Confidence Epic',
      description: 'Epic with low confidence',
      confidence_score: 0.65,
      position: 2,
      stories: [
        { id: 8, title: 'Story 1', status: 'todo', description: 'Test story' },
      ],
    },
  ];

  const defaultProps = {
    epics: [],
    project: mockProject,
    onGenerateEpics: vi.fn(),
    onUpdateEpic: vi.fn(),
    onAddStoryToEpic: vi.fn(),
    onRemoveStoryFromEpic: vi.fn(),
    onAcceptEpic: vi.fn(),
    onRejectEpic: vi.fn(),
    loading: {},
    generatingEpics: false,
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Empty State', () => {
    it('should render empty state when no epics', () => {
      render(<EpicBreakdownView {...defaultProps} />);

      expect(screen.getByText('Эпики еще не созданы')).toBeInTheDocument();
      expect(screen.getByText(/Создайте эпики для группировки историй/)).toBeInTheDocument();
      expect(screen.getByText('Сгенерировать эпики')).toBeInTheDocument();
    });

    it('should call onGenerateEpics when clicking generate button', () => {
      const onGenerateEpics = vi.fn();
      render(<EpicBreakdownView {...defaultProps} onGenerateEpics={onGenerateEpics} />);

      const button = screen.getByText('Сгенерировать эпики');
      fireEvent.click(button);

      expect(onGenerateEpics).toHaveBeenCalledTimes(1);
    });

    it('should disable generate button when generating', () => {
      render(<EpicBreakdownView {...defaultProps} generatingEpics={true} />);

      const button = screen.getByText('Генерация эпиков...');
      expect(button).toBeDisabled();
    });
  });

  describe('Epic List Rendering', () => {
    it('should render list of epics', () => {
      render(<EpicBreakdownView {...defaultProps} epics={mockEpics} />);

      expect(screen.getByText('Checkout Flow')).toBeInTheDocument();
      expect(screen.getByText('User Authentication')).toBeInTheDocument();
      expect(screen.getByText('Low Confidence Epic')).toBeInTheDocument();
    });

    it('should display epic description', () => {
      render(<EpicBreakdownView {...defaultProps} epics={[mockEpics[0]]} />);

      expect(screen.getByText('User checkout process')).toBeInTheDocument();
    });

    it('should display epic stats (stories count, progress, confidence)', () => {
      render(<EpicBreakdownView {...defaultProps} epics={[mockEpics[0]]} />);

      expect(screen.getByText(/Истории: 4/)).toBeInTheDocument();
      expect(screen.getByText(/Прогресс: 50%/)).toBeInTheDocument();
      expect(screen.getByText(/Уверенность: 85%/)).toBeInTheDocument();
    });

    it('should show warning for low confidence epic (<70%)', () => {
      render(<EpicBreakdownView {...defaultProps} epics={[mockEpics[2]]} />);

      expect(screen.getByText('Низкая уверенность')).toBeInTheDocument();
    });

    it('should not show warning for high confidence epic (>=70%)', () => {
      render(<EpicBreakdownView {...defaultProps} epics={[mockEpics[0]]} />);

      expect(screen.queryByText('Низкая уверенность')).not.toBeInTheDocument();
    });
  });

  describe('Progress Calculation', () => {
    it('should calculate progress correctly (50% for 2 done out of 4)', () => {
      render(<EpicBreakdownView {...defaultProps} epics={[mockEpics[0]]} />);

      expect(screen.getByText(/Прогресс: 50%/)).toBeInTheDocument();
    });

    it('should calculate progress correctly (100% for all done)', () => {
      render(<EpicBreakdownView {...defaultProps} epics={[mockEpics[1]]} />);

      expect(screen.getByText(/Прогресс: 100%/)).toBeInTheDocument();
    });

    it('should calculate progress correctly (0% for no done)', () => {
      const epicWithNoDone = {
        ...mockEpics[2],
        stories: [
          { id: 1, title: 'Story 1', status: 'todo' },
          { id: 2, title: 'Story 2', status: 'in_progress' },
        ],
      };

      render(<EpicBreakdownView {...defaultProps} epics={[epicWithNoDone]} />);

      expect(screen.getByText(/Прогресс: 0%/)).toBeInTheDocument();
    });
  });

  describe('Story List', () => {
    it('should render stories in epic', () => {
      render(<EpicBreakdownView {...defaultProps} epics={[mockEpics[0]]} />);

      expect(screen.getByText('Add to cart')).toBeInTheDocument();
      expect(screen.getByText('Payment')).toBeInTheDocument();
      expect(screen.getByText('Order review')).toBeInTheDocument();
      expect(screen.getByText('Confirmation')).toBeInTheDocument();
    });

    it('should show checkmark for done stories', () => {
      render(<EpicBreakdownView {...defaultProps} epics={[mockEpics[0]]} />);

      // Проверяем наличие иконок для done stories
      const checkmarks = screen.getAllByTitle(/Выполнено/i);
      expect(checkmarks.length).toBeGreaterThan(0);
    });

    it('should show empty circle for todo stories', () => {
      render(<EpicBreakdownView {...defaultProps} epics={[mockEpics[0]]} />);

      // Проверяем наличие иконок для todo stories
      const circles = screen.getAllByTitle(/Не выполнено/i);
      expect(circles.length).toBeGreaterThan(0);
    });

    it('should show empty message when epic has no stories', () => {
      const epicWithoutStories = {
        ...mockEpics[0],
        stories: [],
      };

      render(<EpicBreakdownView {...defaultProps} epics={[epicWithoutStories]} />);

      expect(screen.getByText('Нет историй в этом эпике')).toBeInTheDocument();
    });
  });

  describe('Epic Actions', () => {
    it('should show edit, accept, and reject buttons', () => {
      render(<EpicBreakdownView {...defaultProps} epics={[mockEpics[0]]} />);

      // Ищем кнопки по их title или aria-label
      const editButton = screen.getByTitle('Редактировать');
      const acceptButton = screen.getByTitle('Принять эпик');
      const rejectButton = screen.getByTitle('Отклонить эпик');

      expect(editButton).toBeInTheDocument();
      expect(acceptButton).toBeInTheDocument();
      expect(rejectButton).toBeInTheDocument();
    });

    it('should enter edit mode when clicking edit button', () => {
      render(<EpicBreakdownView {...defaultProps} epics={[mockEpics[0]]} />);

      const editButton = screen.getByTitle('Редактировать');
      fireEvent.click(editButton);

      // Проверяем, что появилось поле ввода
      const input = screen.getByPlaceholderText('Название эпика');
      expect(input).toBeInTheDocument();
      expect(input.value).toBe('Checkout Flow');
    });

    it('should save epic changes when clicking save', async () => {
      const onUpdateEpic = vi.fn().mockResolvedValue({});
      render(<EpicBreakdownView {...defaultProps} epics={[mockEpics[0]]} onUpdateEpic={onUpdateEpic} />);

      // Входим в режим редактирования
      const editButton = screen.getByTitle('Редактировать');
      fireEvent.click(editButton);

      // Изменяем название
      const input = screen.getByPlaceholderText('Название эпика');
      fireEvent.change(input, { target: { value: 'Updated Title' } });

      // Сохраняем
      const saveButton = screen.getByText('Сохранить');
      fireEvent.click(saveButton);

      await waitFor(() => {
        expect(onUpdateEpic).toHaveBeenCalledWith(1, {
          title: 'Updated Title',
          description: 'User checkout process',
        });
      });
    });

    it('should cancel edit mode when clicking cancel', () => {
      render(<EpicBreakdownView {...defaultProps} epics={[mockEpics[0]]} />);

      const editButton = screen.getByTitle('Редактировать');
      fireEvent.click(editButton);

      const cancelButton = screen.getByText('Отмена');
      fireEvent.click(cancelButton);

      // Проверяем, что вернулись к обычному виду
      expect(screen.getByText('Checkout Flow')).toBeInTheDocument();
      expect(screen.queryByPlaceholderText('Название эпика')).not.toBeInTheDocument();
    });

    it('should call onAcceptEpic when clicking accept button', () => {
      const onAcceptEpic = vi.fn();
      render(<EpicBreakdownView {...defaultProps} epics={[mockEpics[0]]} onAcceptEpic={onAcceptEpic} />);

      const acceptButton = screen.getByTitle('Принять эпик');
      fireEvent.click(acceptButton);

      expect(onAcceptEpic).toHaveBeenCalledWith(1);
    });

    it('should call onRejectEpic when clicking reject button', () => {
      // Mock window.confirm
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true);
      const onRejectEpic = vi.fn();
      render(<EpicBreakdownView {...defaultProps} epics={[mockEpics[0]]} onRejectEpic={onRejectEpic} />);

      const rejectButton = screen.getByTitle('Отклонить эпик');
      fireEvent.click(rejectButton);

      expect(confirmSpy).toHaveBeenCalled();
      expect(onRejectEpic).toHaveBeenCalledWith(1);

      confirmSpy.mockRestore();
    });

    it('should not call onRejectEpic if user cancels confirmation', () => {
      const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false);
      const onRejectEpic = vi.fn();
      render(<EpicBreakdownView {...defaultProps} epics={[mockEpics[0]]} onRejectEpic={onRejectEpic} />);

      const rejectButton = screen.getByTitle('Отклонить эпик');
      fireEvent.click(rejectButton);

      expect(confirmSpy).toHaveBeenCalled();
      expect(onRejectEpic).not.toHaveBeenCalled();

      confirmSpy.mockRestore();
    });
  });

  describe('Remove Story from Epic', () => {
    it('should call onRemoveStoryFromEpic when clicking remove button on story', () => {
      const onRemoveStoryFromEpic = vi.fn();
      render(
        <EpicBreakdownView {...defaultProps} epics={[mockEpics[0]]} onRemoveStoryFromEpic={onRemoveStoryFromEpic} />
      );

      // Hover over story to show remove button
      const storyCard = screen.getByText('Add to cart').closest('.group');
      fireEvent.mouseEnter(storyCard);

      // Find remove button (it appears on hover)
      const removeButtons = screen.getAllByTitle('Удалить из эпика');
      fireEvent.click(removeButtons[0]);

      expect(onRemoveStoryFromEpic).toHaveBeenCalledWith(1, 1);
    });
  });

  describe('Generate New Epics', () => {
    it('should show generate button when epics exist', () => {
      render(<EpicBreakdownView {...defaultProps} epics={[mockEpics[0]]} />);

      expect(screen.getByText('Сгенерировать новые')).toBeInTheDocument();
    });

    it('should call onGenerateEpics when clicking generate new button', () => {
      const onGenerateEpics = vi.fn();
      render(<EpicBreakdownView {...defaultProps} epics={[mockEpics[0]]} onGenerateEpics={onGenerateEpics} />);

      const button = screen.getByText('Сгенерировать новые');
      fireEvent.click(button);

      expect(onGenerateEpics).toHaveBeenCalledTimes(1);
    });
  });
});


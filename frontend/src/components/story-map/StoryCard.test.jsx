import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import StoryCard from './StoryCard';

vi.mock('@dnd-kit/sortable', () => ({
  useSortable: () => ({
    attributes: {},
    listeners: {},
    setNodeRef: vi.fn(),
    transform: null,
    transition: null,
    isDragging: false,
  }),
}));

vi.mock('@dnd-kit/utilities', () => ({
  CSS: { Transform: { toString: () => '' } },
}));

describe('StoryCard', () => {
  const baseStory = {
    id: 1,
    title: 'Test story',
    description: 'Desc',
    status: 'todo',
    priority: 'Later',
    acceptance_criteria: ['a'],
  };

  it('cycles status using STATUS_FLOW and calls onStatusChange', () => {
    const onStatusChange = vi.fn();
    render(
      <StoryCard
        story={baseStory}
        taskId={1}
        releaseId={1}
        onEdit={() => {}}
        onOpenAI={() => {}}
        onStatusChange={onStatusChange}
      />,
    );

    const statusButton = screen.getByRole('button', { name: /начать/i });
    fireEvent.click(statusButton);

    expect(onStatusChange).toHaveBeenCalledWith(baseStory.id, 'in_progress');
  });

  it('falls back for unknown status and still advances flow', () => {
    const onStatusChange = vi.fn();
    render(
      <StoryCard
        story={{ ...baseStory, status: 'mystery' }}
        taskId={1}
        releaseId={1}
        onEdit={() => {}}
        onOpenAI={() => {}}
        onStatusChange={onStatusChange}
      />,
    );

    const statusButton = screen.getByTitle(/работу/i);
    fireEvent.click(statusButton);

    expect(onStatusChange).toHaveBeenCalledWith(baseStory.id, 'in_progress');
  });
});


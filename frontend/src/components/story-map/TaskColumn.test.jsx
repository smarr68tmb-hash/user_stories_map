import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import TaskColumn from './TaskColumn';

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

describe('TaskColumn', () => {
  const baseTask = { id: 7, title: 'Task' };
  const noop = () => {};

  it('shows confirm tone when pendingDelete is true', () => {
    render(
      <TaskColumn
        task={baseTask}
        isEditing={false}
        editingTaskTitle=""
        setEditingTaskTitle={noop}
        onUpdateTask={noop}
        onStartEditing={noop}
        onDelete={noop}
        setEditingTaskId={noop}
        isUpdating={false}
        isDeleting={false}
        pendingDelete
      />,
    );

    const deleteBtn = screen.getByTitle(/удалить/i);
    expect(deleteBtn.className).toMatch(/border/);
  });

  it('uses danger tone when pendingDelete is false', () => {
    render(
      <TaskColumn
        task={baseTask}
        isEditing={false}
        editingTaskTitle=""
        setEditingTaskTitle={noop}
        onUpdateTask={noop}
        onStartEditing={noop}
        onDelete={noop}
        setEditingTaskId={noop}
        isUpdating={false}
        isDeleting={false}
        pendingDelete={false}
      />,
    );

    const deleteBtn = screen.getByTitle(/удалить/i);
    expect(deleteBtn.className).toMatch(/text-orange-600|text-rose-600|text-amber-600/);
  });
});


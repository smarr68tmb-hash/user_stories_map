import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import ViewToggle from './ViewToggle';

describe('ViewToggle', () => {
  it('should render both view buttons', () => {
    const onViewChange = vi.fn();
    render(<ViewToggle viewMode="storyMap" onViewChange={onViewChange} />);

    expect(screen.getByText('Story Map View')).toBeInTheDocument();
    expect(screen.getByText('Epic View')).toBeInTheDocument();
  });

  it('should highlight active view (storyMap)', () => {
    const onViewChange = vi.fn();
    render(<ViewToggle viewMode="storyMap" onViewChange={onViewChange} />);

    const storyMapButton = screen.getByText('Story Map View').closest('button');
    const epicButton = screen.getByText('Epic View').closest('button');

    expect(storyMapButton).toHaveClass('bg-white', 'text-blue-600', 'font-medium');
    expect(epicButton).not.toHaveClass('bg-white', 'text-blue-600', 'font-medium');
  });

  it('should highlight active view (epic)', () => {
    const onViewChange = vi.fn();
    render(<ViewToggle viewMode="epic" onViewChange={onViewChange} />);

    const storyMapButton = screen.getByText('Story Map View').closest('button');
    const epicButton = screen.getByText('Epic View').closest('button');

    expect(epicButton).toHaveClass('bg-white', 'text-blue-600', 'font-medium');
    expect(storyMapButton).not.toHaveClass('bg-white', 'text-blue-600', 'font-medium');
  });

  it('should call onViewChange when clicking Story Map View button', () => {
    const onViewChange = vi.fn();
    render(<ViewToggle viewMode="epic" onViewChange={onViewChange} />);

    const storyMapButton = screen.getByText('Story Map View').closest('button');
    fireEvent.click(storyMapButton);

    expect(onViewChange).toHaveBeenCalledWith('storyMap');
    expect(onViewChange).toHaveBeenCalledTimes(1);
  });

  it('should call onViewChange when clicking Epic View button', () => {
    const onViewChange = vi.fn();
    render(<ViewToggle viewMode="storyMap" onViewChange={onViewChange} />);

    const epicButton = screen.getByText('Epic View').closest('button');
    fireEvent.click(epicButton);

    expect(onViewChange).toHaveBeenCalledWith('epic');
    expect(onViewChange).toHaveBeenCalledTimes(1);
  });
});


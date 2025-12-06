import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import Button from './Button';

describe('Button', () => {
  it('renders children and keeps type="button" by default', () => {
    render(<Button>Click me</Button>);
    const btn = screen.getByRole('button', { name: /click me/i });
    expect(btn).toBeInTheDocument();
    expect(btn).toHaveAttribute('type', 'button');
  });

  it('shows spinner and becomes disabled when loading', () => {
    render(<Button loading>Saving</Button>);
    const btn = screen.getByRole('button', { name: /saving/i });
    expect(btn).toBeDisabled();
    expect(btn).toHaveAttribute('aria-busy', 'true');
    expect(btn.querySelector('.animate-spin')).toBeTruthy();
  });

  it('respects custom type and clicks fire when not disabled', async () => {
    const onClick = vi.fn();
    render(
      <Button type="submit" onClick={onClick}>
        Submit
      </Button>,
    );
    const btn = screen.getByRole('button', { name: /submit/i });
    expect(btn).toHaveAttribute('type', 'submit');
    await userEvent.click(btn);
    expect(onClick).toHaveBeenCalledTimes(1);
  });
});


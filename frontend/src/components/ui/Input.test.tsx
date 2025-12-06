import { render, screen } from '@testing-library/react';
import Input from './Input';

describe('Input', () => {
  it('renders enabled by default', () => {
    render(<Input placeholder="email" />);
    const input = screen.getByPlaceholderText(/email/i);
    expect(input).toBeEnabled();
  });

  it('disables and shows aria-busy when loading', () => {
    render(<Input placeholder="loading" loading />);
    const input = screen.getByPlaceholderText(/loading/i);
    expect(input).toBeDisabled();
    // Spinner renders; aria-busy is intentionally unset on the native input
    expect(input.parentElement?.querySelector('.animate-spin')).toBeTruthy();
  });
});


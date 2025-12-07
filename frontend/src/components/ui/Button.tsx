import React from 'react';
import { cn } from './utils';

type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger' | 'success';
type ButtonSize = 'sm' | 'md' | 'lg' | 'xs';

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
};

const variantStyles: Record<ButtonVariant, string> = {
  primary: 'bg-primary-600 text-white hover:bg-primary-700 focus-visible:ring-primary-600',
  secondary:
    'bg-surface-subtle text-content border border-surface-border hover:bg-surface-muted focus-visible:ring-primary-600',
  ghost: 'bg-transparent text-content hover:bg-surface-subtle focus-visible:ring-primary-600',
  danger: 'bg-rose-600 text-white hover:bg-rose-700 focus-visible:ring-rose-600',
  success: 'bg-emerald-600 text-white hover:bg-emerald-700 focus-visible:ring-emerald-600',
};

const sizeStyles: Record<ButtonSize, string> = {
  xs: 'h-7 px-2 text-xs',
  sm: 'h-9 px-3 text-sm',
  md: 'h-10 px-4 text-sm',
  lg: 'h-11 px-5 text-base',
};

const Spinner: React.FC<{ className?: string }> = ({ className }) => (
  <span
    className={cn(
      'inline-flex h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent',
      className,
    )}
    aria-hidden="true"
  />
);

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      children,
      variant = 'primary',
      size = 'md',
      loading = false,
      disabled = false,
      className,
      leftIcon,
      rightIcon,
      type = 'button',
      ...buttonProps
    },
    ref,
  ) => {
    const isDisabled = disabled || loading;

    return (
      <button
        ref={ref}
        type={type}
        className={cn(
          'inline-flex items-center justify-center gap-2 rounded-button font-medium transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-60',
          variantStyles[variant] ?? variantStyles.primary,
          sizeStyles[size] ?? sizeStyles.md,
          isDisabled && 'cursor-not-allowed',
          className,
        )}
        disabled={isDisabled}
        aria-busy={loading || undefined}
        {...buttonProps}
      >
        {loading && <Spinner />}
        {leftIcon}
        <span>{children}</span>
        {rightIcon}
      </button>
    );
  },
);

Button.displayName = 'Button';

export default Button;


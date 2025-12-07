import React from 'react';
import { cn } from './utils';

type BadgeVariant = 'primary' | 'secondary' | 'ghost' | 'success' | 'warning' | 'danger' | 'info' | 'mvp' | 'release1' | 'later';
type BadgeSize = 'xs' | 'sm' | 'md' | 'lg';

type BadgeProps = React.HTMLAttributes<HTMLSpanElement> & {
  variant?: BadgeVariant;
  size?: BadgeSize;
  loading?: boolean;
  disabled?: boolean;
  leftIcon?: React.ReactNode;
  rightIcon?: React.ReactNode;
};

const variantStyles: Record<BadgeVariant, string> = {
  primary: 'bg-primary-50 text-primary-700 border border-primary-100',
  secondary: 'bg-surface-subtle text-content-secondary border border-surface-border',
  ghost: 'bg-transparent text-content-muted border border-surface-border border-dashed',
  success: 'bg-emerald-50 text-emerald-700 border border-emerald-200',
  warning: 'bg-amber-50 text-amber-700 border border-amber-200',
  danger: 'bg-rose-50 text-rose-700 border border-rose-200',
  info: 'bg-blue-50 text-blue-700 border border-blue-200',
  // Priority variants
  mvp: 'bg-rose-100 text-rose-800 border border-rose-300',
  release1: 'bg-amber-100 text-amber-800 border border-amber-300',
  later: 'bg-gray-100 text-gray-700 border border-gray-300',
};

const sizeStyles: Record<BadgeSize, string> = {
  xs: 'text-[10px] px-1.5 py-0.5',
  sm: 'text-xs px-2 py-0.5',
  md: 'text-sm px-3 py-1',
  lg: 'text-sm px-3.5 py-1.5',
};

const Spinner: React.FC<{ className?: string }> = ({ className }) => (
  <span
    className={cn(
      'inline-flex h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent',
      className,
    )}
    aria-hidden="true"
  />
);

const Badge = React.forwardRef<HTMLSpanElement, BadgeProps>(
  (
    {
      children,
      variant = 'secondary',
      size = 'md',
      loading = false,
      disabled = false,
      className,
      leftIcon,
      rightIcon,
      ...props
    },
    ref,
  ) => {
    const isDisabled = disabled || loading;

    return (
      <span
        ref={ref}
        className={cn(
          'inline-flex items-center gap-1 rounded-badge font-medium align-middle select-none transition-colors duration-fast',
          variantStyles[variant] ?? variantStyles.secondary,
          sizeStyles[size] ?? sizeStyles.md,
          isDisabled && 'cursor-not-allowed opacity-60',
          className,
        )}
        aria-disabled={isDisabled || undefined}
        {...props}
      >
        {loading && <Spinner className="text-primary-600" />}
        {leftIcon}
        <span>{children}</span>
        {rightIcon}
      </span>
    );
  },
);

Badge.displayName = 'Badge';

export default Badge;


import React from 'react';
import { cn } from './utils';

type InputVariant = 'primary' | 'secondary' | 'ghost';
type InputSize = 'xs' | 'sm' | 'md' | 'lg';
type InputValidation = 'default' | 'error' | 'warning' | 'success';

type InputProps = React.InputHTMLAttributes<HTMLInputElement> & {
  variant?: InputVariant;
  size?: InputSize;
  loading?: boolean;
  validation?: InputValidation;
  wrapperClassName?: string;
};

const variantStyles: Record<InputVariant, string> = {
  primary: 'bg-surface border border-surface-border focus-visible:ring-offset-0',
  secondary: 'bg-surface-subtle border border-surface-border focus-visible:ring-offset-0',
  ghost: 'bg-transparent border border-surface-border/70 focus-visible:ring-offset-0',
};

const sizeStyles: Record<InputSize, string> = {
  xs: 'h-7 px-2 text-xs',
  sm: 'h-9 px-3 text-sm',
  md: 'h-10 px-3 text-sm',
  lg: 'h-11 px-4 text-base',
};

const validationStyles: Record<InputValidation, string> = {
  default: '',
  error: 'border-rose-400 bg-rose-50 focus-visible:ring-rose-400',
  warning: 'border-amber-400 bg-amber-50 focus-visible:ring-amber-400',
  success: 'border-emerald-400 focus-visible:ring-emerald-400',
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

const Input = React.forwardRef<HTMLInputElement, InputProps>(
  (
    {
      variant = 'primary',
      size = 'md',
      loading = false,
      disabled = false,
      validation = 'default',
      className,
      wrapperClassName,
      ...props
    },
    ref,
  ) => {
    const isDisabled = disabled || loading;

    return (
      <div className={cn('relative w-full', wrapperClassName)}>
        <input
          ref={ref}
          disabled={isDisabled}
          className={cn(
            'w-full rounded-input border text-content placeholder-content-subtle transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-content-muted disabled:placeholder-content-subtle',
            variantStyles[variant] ?? variantStyles.primary,
            sizeStyles[size] ?? sizeStyles.md,
            validationStyles[validation] ?? validationStyles.default,
            loading && 'pr-10',
            className,
          )}
          {...props}
        />
        {loading && (
          <Spinner className="absolute right-3 top-1/2 -translate-y-1/2 text-content-muted" />
        )}
      </div>
    );
  },
);

Input.displayName = 'Input';

export default Input;


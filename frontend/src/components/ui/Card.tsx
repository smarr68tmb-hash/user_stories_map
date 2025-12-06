import React from 'react';
import { cn } from './utils';

type CardVariant = 'primary' | 'secondary' | 'ghost';
type CardSize = 'sm' | 'md' | 'lg';

type CardProps = React.HTMLAttributes<HTMLDivElement> & {
  variant?: CardVariant;
  size?: CardSize;
  loading?: boolean;
  disabled?: boolean;
};

const variantStyles: Record<CardVariant, string> = {
  primary: 'bg-surface shadow-card border border-surface-border',
  secondary: 'bg-surface-subtle border border-surface-border',
  ghost: 'bg-transparent border border-dashed border-surface-border',
};

const sizeStyles: Record<CardSize, string> = {
  sm: 'p-4',
  md: 'p-5',
  lg: 'p-6',
};

const Spinner: React.FC<{ className?: string }> = ({ className }) => (
  <span
    className={cn(
      'inline-flex h-5 w-5 animate-spin rounded-full border-2 border-current border-t-transparent',
      className,
    )}
    aria-hidden="true"
  />
);

const Card = React.forwardRef<HTMLDivElement, CardProps>(
  ({ children, variant = 'primary', size = 'md', loading = false, disabled = false, className, ...props }, ref) => {
    return (
      <div
        ref={ref}
        className={cn(
          'relative rounded-card text-content transition-shadow duration-fast',
          variantStyles[variant] ?? variantStyles.primary,
          sizeStyles[size] ?? sizeStyles.md,
          !disabled && 'hover:shadow-card-hover',
          disabled && 'opacity-70',
          className,
        )}
        aria-busy={loading || undefined}
        aria-disabled={disabled || undefined}
        {...props}
      >
        {loading && (
          <div className="absolute inset-0 flex items-center justify-center rounded-card bg-surface/70 backdrop-blur-[1px]">
            <Spinner className="text-primary-600" />
          </div>
        )}
        <div className={loading ? 'opacity-70' : undefined}>{children}</div>
      </div>
    );
  },
);

Card.displayName = 'Card';

export default Card;


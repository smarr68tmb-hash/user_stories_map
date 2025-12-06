import React from "react";
import { cn } from "./utils";

const variantStyles = {
  primary: "bg-primary-50 text-primary-700 border border-primary-100",
  secondary: "bg-surface-subtle text-content-secondary border border-surface-border",
  ghost:
    "bg-transparent text-content-muted border border-surface-border border-dashed",
};

const sizeStyles = {
  sm: "text-xs px-2 py-0.5",
  md: "text-sm px-3 py-1",
  lg: "text-sm px-3.5 py-1.5",
};

const Spinner = ({ className }) => (
  <span
    className={cn(
      "inline-flex h-3.5 w-3.5 animate-spin rounded-full border-2 border-current border-t-transparent",
      className
    )}
    aria-hidden="true"
  />
);

const Badge = React.forwardRef(
  (
    {
      children,
      variant = "secondary",
      size = "md",
      loading = false,
      disabled = false,
      className,
      leftIcon,
      rightIcon,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    return (
      <span
        ref={ref}
        className={cn(
          "inline-flex items-center gap-1 rounded-badge font-medium align-middle select-none transition-colors duration-fast",
          variantStyles[variant] ?? variantStyles.secondary,
          sizeStyles[size] ?? sizeStyles.md,
          isDisabled && "cursor-not-allowed opacity-60",
          className
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
  }
);

Badge.displayName = "Badge";

export default Badge;


import React from "react";
import { cn } from "./utils";

const variantStyles = {
  primary:
    "bg-surface border border-surface-border focus-visible:ring-offset-0",
  secondary:
    "bg-surface-subtle border border-surface-border focus-visible:ring-offset-0",
  ghost:
    "bg-transparent border border-surface-border/70 focus-visible:ring-offset-0",
};

const sizeStyles = {
  sm: "h-9 px-3 text-sm",
  md: "h-10 px-3 text-sm",
  lg: "h-11 px-4 text-base",
};

const Spinner = ({ className }) => (
  <span
    className={cn(
      "inline-flex h-4 w-4 animate-spin rounded-full border-2 border-current border-t-transparent",
      className
    )}
    aria-hidden="true"
  />
);

const Input = React.forwardRef(
  (
    {
      variant = "primary",
      size = "md",
      loading = false,
      disabled = false,
      className,
      wrapperClassName,
      ...props
    },
    ref
  ) => {
    const isDisabled = disabled || loading;

    return (
      <div className={cn("relative w-full", wrapperClassName)}>
        <input
          ref={ref}
          disabled={isDisabled}
          className={cn(
            "w-full rounded-input border text-content placeholder-content-subtle transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 disabled:cursor-not-allowed disabled:bg-surface-muted disabled:text-content-muted disabled:placeholder-content-subtle",
            variantStyles[variant] ?? variantStyles.primary,
            sizeStyles[size] ?? sizeStyles.md,
            loading && "pr-10",
            className
          )}
          {...props}
        />
        {loading && (
          <Spinner className="absolute right-3 top-1/2 -translate-y-1/2 text-content-muted" />
        )}
      </div>
    );
  }
);

Input.displayName = "Input";

export default Input;


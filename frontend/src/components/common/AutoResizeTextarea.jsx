import { useEffect, useRef } from 'react';

/**
 * Auto-resizing textarea component
 * Automatically adjusts height based on content
 */
function AutoResizeTextarea({
  value,
  onChange,
  minHeight = 160,
  maxHeight = 600,
  className = '',
  ...props
}) {
  const textareaRef = useRef(null);

  useEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    // Reset height to auto to get the correct scrollHeight
    textarea.style.height = 'auto';

    // Calculate new height
    const newHeight = Math.min(
      Math.max(minHeight, textarea.scrollHeight),
      maxHeight
    );

    // Set new height
    textarea.style.height = `${newHeight}px`;
  }, [value, minHeight, maxHeight]);

  return (
    <textarea
      ref={textareaRef}
      value={value}
      onChange={onChange}
      className={`resize-none overflow-y-auto ${className}`}
      style={{
        minHeight: `${minHeight}px`,
        maxHeight: `${maxHeight}px`,
      }}
      {...props}
    />
  );
}

export default AutoResizeTextarea;

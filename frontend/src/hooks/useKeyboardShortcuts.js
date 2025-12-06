import { useEffect, useCallback } from 'react';

/**
 * Hook for handling keyboard shortcuts
 * @param {Array} shortcuts - Array of shortcut definitions
 * @param {boolean} enabled - Whether shortcuts are active
 *
 * Shortcut definition:
 * {
 *   key: 's',           // Key to listen for (case-insensitive)
 *   ctrl: true,         // Require Ctrl/Cmd key
 *   shift: false,       // Require Shift key
 *   alt: false,         // Require Alt key
 *   handler: () => {},  // Function to call
 *   preventDefault: true // Prevent default browser behavior
 * }
 */
export function useKeyboardShortcuts(shortcuts, enabled = true) {
  const handleKeyDown = useCallback((event) => {
    if (!enabled) return;

    // Don't trigger shortcuts when typing in input/textarea (unless Escape)
    const target = event.target;
    const isInput = target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable;

    const key = event.key.toLowerCase();
    const ctrl = event.ctrlKey || event.metaKey;
    const shift = event.shiftKey;
    const alt = event.altKey;

    for (const shortcut of shortcuts) {
      const keyMatch = shortcut.key.toLowerCase() === key;
      const ctrlMatch = !!shortcut.ctrl === ctrl;
      const shiftMatch = !!shortcut.shift === shift;
      const altMatch = !!shortcut.alt === alt;

      // Special case: Escape should work even in inputs
      const isEscape = key === 'escape';

      // For non-Escape keys, skip if user is typing in an input (unless ctrl/cmd is pressed)
      if (!isEscape && isInput && !ctrl) {
        continue;
      }

      if (keyMatch && ctrlMatch && shiftMatch && altMatch) {
        if (shortcut.preventDefault !== false) {
          event.preventDefault();
        }
        shortcut.handler(event);
        break;
      }
    }
  }, [shortcuts, enabled]);

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);
}

export default useKeyboardShortcuts;

import { useEffect } from 'react';

const FOCUSABLE_SELECTOR = [
  'a[href]',
  'area[href]',
  'input:not([disabled])',
  'select:not([disabled])',
  'textarea:not([disabled])',
  'button:not([disabled])',
  'iframe',
  '[tabindex]:not([tabindex="-1"])',
  '[contentEditable=true]',
].join(',');

export default function useFocusTrap(ref, isActive) {
  useEffect(() => {
    if (!isActive || !ref?.current) return undefined;

    const node = ref.current;
    const focusable = node.querySelectorAll(FOCUSABLE_SELECTOR);
    const first = focusable[0];
    const last = focusable[focusable.length - 1];

    if (first) {
      first.focus();
    } else {
      node.focus();
    }

    const handleKeyDown = (event) => {
      if (event.key !== 'Tab' || focusable.length === 0) return;

      if (event.shiftKey) {
        if (document.activeElement === first) {
          event.preventDefault();
          last.focus();
        }
      } else if (document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };

    node.addEventListener('keydown', handleKeyDown);
    return () => node.removeEventListener('keydown', handleKeyDown);
  }, [isActive, ref]);
}


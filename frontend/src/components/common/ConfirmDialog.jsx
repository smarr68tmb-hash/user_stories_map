import { useEffect, useRef } from 'react';
import useFocusTrap from '../../hooks/useFocusTrap';

function ConfirmDialog({
  isOpen,
  title,
  description,
  confirmText = 'Подтвердить',
  cancelText = 'Отмена',
  onConfirm,
  onCancel,
  loading = false,
}) {
  const dialogRef = useRef(null);
  useFocusTrap(dialogRef, isOpen);

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape' && isOpen) {
        onCancel?.();
      }
    };

    if (isOpen) {
      document.addEventListener('keydown', handleKeyDown);
    }

    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, onCancel]);

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="confirm-dialog-title"
      aria-describedby={description ? 'confirm-dialog-description' : undefined}
      onClick={(e) => {
        if (e.target === e.currentTarget) {
          onCancel?.();
        }
      }}
    >
      <div
        ref={dialogRef}
        className="bg-white rounded-lg shadow-xl max-w-md w-full p-6"
        tabIndex={-1}
      >
        <div className="flex items-start gap-3 mb-4">
          <div className="flex-shrink-0 w-10 h-10 bg-red-100 rounded-full flex items-center justify-center text-red-600">
            ⚠️
          </div>
          <div className="flex-1">
            <h3 id="confirm-dialog-title" className="text-lg font-semibold text-gray-900">
              {title}
            </h3>
            {description && (
              <p id="confirm-dialog-description" className="text-sm text-gray-600 mt-1">
                {description}
              </p>
            )}
          </div>
          <button
            onClick={onCancel}
            className="text-gray-400 hover:text-gray-600"
            aria-label="Закрыть диалог"
          >
            ✕
          </button>
        </div>

        <div className="flex justify-end gap-3">
          <button
            onClick={onCancel}
            disabled={loading}
            className="px-4 py-2 text-gray-700 bg-gray-100 rounded-lg hover:bg-gray-200 transition font-medium disabled:opacity-50"
          >
            {cancelText}
          </button>
          <button
            onClick={onConfirm}
            disabled={loading}
            aria-busy={loading}
            className="px-4 py-2 text-white bg-red-600 rounded-lg hover:bg-red-700 transition font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading && (
              <svg className="animate-spin h-4 w-4" fill="none" viewBox="0 0 24 24" aria-hidden="true">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
            )}
            {confirmText}
          </button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmDialog;


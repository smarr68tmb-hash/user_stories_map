import { useEffect, useRef } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import useFocusTrap from '../../hooks/useFocusTrap';
import { getSeverityToken, TEXT_TOKENS } from '../../theme/tokens';
import { Button } from '../ui';

// Dialog tokens
const DIALOG_TOKENS = {
  overlay: 'bg-black/50',
  content: 'bg-white rounded-lg shadow-xl',
  closeButton: 'text-gray-400 hover:text-gray-600 hover:bg-gray-100',
};

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
      className={`fixed inset-0 ${DIALOG_TOKENS.overlay} flex items-center justify-center z-50 p-4 animate-fade-in`}
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
        className={`${DIALOG_TOKENS.content} max-w-md w-full p-6 animate-scale-in`}
        tabIndex={-1}
      >
        <div className="flex items-start gap-3 mb-4">
          <div className={`flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center ${getSeverityToken('critical').badge}`}>
            <AlertTriangle className="w-5 h-5" />
          </div>
          <div className="flex-1">
            <h3 id="confirm-dialog-title" className={`text-lg font-semibold ${TEXT_TOKENS.primary}`}>
              {title}
            </h3>
            {description && (
              <p id="confirm-dialog-description" className={`text-sm mt-1 ${TEXT_TOKENS.secondary}`}>
                {description}
              </p>
            )}
          </div>
          <button
            onClick={onCancel}
            className={`min-w-[32px] min-h-[32px] flex items-center justify-center rounded transition ${DIALOG_TOKENS.closeButton}`}
            aria-label="Закрыть диалог"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex justify-end gap-3">
          <Button
            variant="secondary"
            onClick={onCancel}
            disabled={loading}
          >
            {cancelText}
          </Button>
          <Button
            variant="danger"
            onClick={onConfirm}
            loading={loading}
          >
            {confirmText}
          </Button>
        </div>
      </div>
    </div>
  );
}

export default ConfirmDialog;


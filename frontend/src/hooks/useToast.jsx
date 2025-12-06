import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { CheckCircle, AlertCircle, Info, AlertTriangle, X } from 'lucide-react';

const ToastContext = createContext(null);

const DEFAULT_DURATION = 4000;
const UNDO_DURATION = 8000;

let toastCounter = 0;

const IconComponents = {
  success: CheckCircle,
  error: AlertCircle,
  info: Info,
  warning: AlertTriangle,
};

function ToastItem({ toast, onDismiss }) {
  const { id, type, message, action } = toast;
  const colorMap = {
    success: 'bg-green-600',
    error: 'bg-red-600',
    info: 'bg-blue-600',
    warning: 'bg-amber-500',
  };

  const tone = colorMap[type] || colorMap.info;
  const IconComponent = IconComponents[type] || IconComponents.info;

  return (
    <div className={`flex items-start gap-3 text-white px-4 py-3 rounded-lg shadow-lg animate-slide-in ${tone}`}>
      <IconComponent className="w-5 h-5 flex-shrink-0 mt-0.5" />
      <div className="text-sm leading-snug flex-1">
        {message}
        {action && (
          <button
            onClick={() => {
              action.handler();
              onDismiss(id);
            }}
            className="ml-2 underline hover:no-underline font-medium"
          >
            {action.label}
          </button>
        )}
      </div>
      <button
        onClick={() => onDismiss(id)}
        className="text-white/80 hover:text-white min-w-[24px] min-h-[24px] flex items-center justify-center"
        aria-label="Закрыть уведомление"
      >
        <X className="w-4 h-4" />
      </button>
    </div>
  );
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback((message, type = 'info', duration = DEFAULT_DURATION, action = null) => {
    const id = ++toastCounter;
    setToasts((prev) => [...prev, { id, type, message, action }]);
    if (duration > 0) {
      setTimeout(() => dismiss(id), duration);
    }
    return id;
  }, [dismiss]);

  // Show toast with undo action
  const showWithUndo = useCallback((message, undoHandler, duration = UNDO_DURATION) => {
    return addToast(message, 'info', duration, {
      label: 'Отменить',
      handler: undoHandler,
    });
  }, [addToast]);

  const api = useMemo(() => ({
    show: addToast,
    success: (msg, duration) => addToast(msg, 'success', duration),
    error: (msg, duration) => addToast(msg, 'error', duration),
    info: (msg, duration) => addToast(msg, 'info', duration),
    warning: (msg, duration) => addToast(msg, 'warning', duration),
    showWithUndo,
    dismiss,
  }), [addToast, showWithUndo, dismiss]);

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onDismiss={dismiss} />
        ))}
      </div>
    </ToastContext.Provider>
  );
}

export function useToast() {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used within a ToastProvider');
  }
  return ctx;
}

export default useToast;


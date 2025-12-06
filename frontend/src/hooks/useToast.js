import { createContext, useCallback, useContext, useMemo, useState } from 'react';

const ToastContext = createContext(null);

const DEFAULT_DURATION = 4000;

let toastCounter = 0;

function ToastItem({ toast, onDismiss }) {
  const { id, type, message } = toast;
  const colorMap = {
    success: 'bg-green-600',
    error: 'bg-red-600',
    info: 'bg-blue-600',
    warning: 'bg-amber-500',
  };

  const iconMap = {
    success: '✓',
    error: '⚠️',
    info: 'ℹ️',
    warning: '!',
  };

  const tone = colorMap[type] || colorMap.info;
  const icon = iconMap[type] || iconMap.info;

  return (
    <div className={`flex items-start gap-3 text-white px-4 py-3 rounded-lg shadow-lg ${tone}`}>
      <div className="text-lg leading-none">{icon}</div>
      <div className="text-sm leading-snug flex-1">{message}</div>
      <button
        onClick={() => onDismiss(id)}
        className="text-white/80 hover:text-white text-xs font-semibold"
        aria-label="Закрыть уведомление"
      >
        ×
      </button>
    </div>
  );
}

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((toast) => toast.id !== id));
  }, []);

  const addToast = useCallback((message, type = 'info', duration = DEFAULT_DURATION) => {
    const id = ++toastCounter;
    setToasts((prev) => [...prev, { id, type, message }]);
    if (duration > 0) {
      setTimeout(() => dismiss(id), duration);
    }
    return id;
  }, [dismiss]);

  const api = useMemo(() => ({
    show: addToast,
    success: (msg, duration) => addToast(msg, 'success', duration),
    error: (msg, duration) => addToast(msg, 'error', duration),
    info: (msg, duration) => addToast(msg, 'info', duration),
    warning: (msg, duration) => addToast(msg, 'warning', duration),
    dismiss,
  }), [addToast, dismiss]);

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


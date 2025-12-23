import { useEffect, useMemo, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { wireframes } from '../../api';

const STATUS_BADGE = {
  success: { label: 'Готово', className: 'bg-green-100 text-green-700 border-green-200' },
  pending: { label: 'В процессе', className: 'bg-amber-100 text-amber-800 border-amber-200' },
  error: { label: 'Ошибка', className: 'bg-rose-100 text-rose-700 border-rose-200' },
  idle: { label: 'Нет данных', className: 'bg-gray-100 text-gray-600 border-gray-200' },
};

function WireframePanel({ project, refreshProject, toast }) {
  const [loading, setLoading] = useState(false);
  const [jobId, setJobId] = useState(null);
  const [status, setStatus] = useState(project.wireframe_status || 'idle');
  const [error, setError] = useState(project.wireframe_error || null);

  useEffect(() => {
    setStatus(project.wireframe_status || 'idle');
    setError(project.wireframe_error || null);
  }, [project.wireframe_status, project.wireframe_error]);

  useEffect(() => {
    let active = true;
    if (status !== 'pending') return;

    let pollCount = 0;
    const MAX_POLLS = 120; // Максимум 3 минуты (120 * 1.5 сек)
    let pollTimer = null;

    const poll = async () => {
      try {
        pollCount++;
        
        // Проверяем таймаут
        if (pollCount > MAX_POLLS) {
          if (!active) return;
          setLoading(false);
          setStatus('error');
          setError('Таймаут генерации wireframe. Возможно, очередь задач недоступна.');
          toast?.error?.('Таймаут генерации wireframe');
          await refreshProject({ silent: true });
          return;
        }

        const { data } = await wireframes.status(project.id, jobId || undefined);
        if (!active) return;
        
        // Обрабатываем статус из API
        const apiStatus = data.status || 'idle';
        const jobStatus = data.job_status; // Может быть "queued", "started", "finished", "failed"
        
        // Если задача в очереди слишком долго (более 30 секунд), считаем это ошибкой
        if (jobStatus === 'queued' && pollCount > 20) {
          setLoading(false);
          setStatus('error');
          setError('Задача не обрабатывается. Возможно, RQ worker не запущен.');
          toast?.error?.('Задача не обрабатывается. Используется синхронная генерация.');
          await refreshProject({ silent: true });
          return;
        }
        
        setStatus(apiStatus);
        setError(data.error || null);
        
        // Если статус изменился на success или error, останавливаем polling
        if (apiStatus !== 'pending' && apiStatus !== 'queued') {
          await refreshProject({ silent: true });
          setLoading(false);
        } else {
          // Продолжаем polling
          pollTimer = setTimeout(poll, 1500);
        }
      } catch (err) {
        if (!active) return;
        setLoading(false);
        setStatus('error');
        setError('Не удалось получить статус wireframe');
        toast?.error?.('Не удалось получить статус wireframe');
      }
    };

    const timer = setTimeout(poll, 1200);
    return () => {
      active = false;
      clearTimeout(timer);
      if (pollTimer) clearTimeout(pollTimer);
    };
  }, [status, jobId, project.id, refreshProject, toast]);

  const handleGenerate = async () => {
    setLoading(true);
    setStatus('pending');
    setError(null);
    try {
      const { data } = await wireframes.generate(project.id);
      
      // Если генерация завершена синхронно (production mode)
      if (data.status === 'completed') {
        setLoading(false);
        setStatus('success');
        await refreshProject({ silent: true });
        toast?.success?.('Wireframe успешно сгенерирован');
      } else {
        // Асинхронная генерация (development mode с RQ)
        setJobId(data.job_id);
      }
    } catch (err) {
      setLoading(false);
      setStatus(project.wireframe_status || 'idle');
      setError(project.wireframe_error || null);
      const detail = err?.response?.data?.detail || 'Не удалось поставить задачу на генерацию';
      toast?.error?.(detail);
    }
  };

  const statusBadge = useMemo(() => STATUS_BADGE[status] || STATUS_BADGE.idle, [status]);

  return (
    <div className="rounded-xl border border-gray-200 bg-white shadow-sm p-4 md:p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-2">
          <div className={`text-xs font-semibold px-3 py-1 rounded-full border ${statusBadge.className}`}>
            {statusBadge.label}
          </div>
          {project.wireframe_generated_at && status === 'success' && (
            <span className="text-xs text-gray-500">
              Обновлено: {new Date(project.wireframe_generated_at).toLocaleString()}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={handleGenerate}
            disabled={loading}
            className="px-3 py-2 rounded-lg text-sm font-semibold text-white bg-blue-600 hover:bg-blue-700 transition disabled:opacity-60 disabled:cursor-not-allowed"
          >
            {loading || status === 'pending' ? 'Генерация...' : 'Сгенерировать Wireframe'}
          </button>
        </div>
      </div>

      {error && (
        <div className="text-sm text-rose-700 bg-rose-50 border border-rose-200 rounded-lg px-3 py-2">
          {error}
        </div>
      )}

      <div className="border border-gray-200 rounded-lg p-3 bg-gray-50 max-h-[480px] overflow-auto prose prose-sm">
        {project.wireframe_markdown ? (
          <ReactMarkdown remarkPlugins={[remarkGfm]}>{project.wireframe_markdown}</ReactMarkdown>
        ) : (
          <p className="text-sm text-gray-500">Wireframe ещё не сгенерирован.</p>
        )}
      </div>
    </div>
  );
}

export default WireframePanel;


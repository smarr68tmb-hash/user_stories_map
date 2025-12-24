import { useMemo } from 'react';
import { Share2 } from 'lucide-react';

function SearchPanel({
  searchQuery,
  onSearchChange,
  onOpenAnalysis,
  onOpenShare,
  isRefreshing = false,
  statusSummary,
  releaseSummary,
}) {
  const counters = useMemo(
    () =>
      `Показаны статусы: ${statusSummary.shown}/${statusSummary.total}, релизы: ${releaseSummary.shown}/${releaseSummary.total}`,
    [releaseSummary.shown, releaseSummary.total, statusSummary.shown, statusSummary.total],
  );

  return (
    <div className="flex flex-wrap items-center justify-between gap-3">
      <div className="flex items-center gap-2 flex-1 min-w-[260px]">
        <input
          type="search"
          placeholder="Поиск историй и описаний..."
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          className="flex-1 min-w-[220px] rounded-lg border border-gray-300 px-3 py-2 text-sm shadow-sm focus:border-blue-400 focus:ring-2 focus:ring-blue-100"
        />
        <button
          onClick={onOpenAnalysis}
          className="bg-gradient-to-r from-indigo-500 to-purple-500 text-white px-4 py-2 rounded-lg font-medium shadow-lg hover:from-indigo-600 hover:to-purple-600 transition flex items-center gap-2"
        >
          <span>📊</span>
          Анализ карты
        </button>
        {onOpenShare && (
          <button
            onClick={onOpenShare}
            className="bg-blue-600 text-white px-4 py-2 rounded-lg font-medium shadow-lg hover:bg-blue-700 transition flex items-center gap-2"
          >
            <Share2 className="w-4 h-4" />
            Поделиться
          </button>
        )}
      </div>
      <div className="flex items-center gap-3 text-xs text-gray-500">
        {isRefreshing && (
          <span className="flex items-center gap-1">
            <span className="animate-pulse">●</span>
            Синхронизация…
          </span>
        )}
        <span>{counters}</span>
      </div>
    </div>
  );
}

export default SearchPanel;


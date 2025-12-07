import { STATUS_OPTIONS, getStatusToken, TEXT_TOKENS, ACTION_TOKENS, getStatusToken as getReleaseToken } from '../../theme/tokens';

// Token for release filter (uses in_progress style as neutral selection color)
const RELEASE_TOKENS = {
  active: 'border-blue-300 bg-blue-50 text-blue-800',
  inactive: 'border-gray-200 bg-white text-gray-700 hover:border-gray-300',
};

const FILTER_BUTTON_INACTIVE = 'bg-white border-gray-300 text-gray-600 hover:border-gray-400 focus:ring-2 focus:ring-offset-1';

function FilterPanel({ statusFilter, releaseFilter, releases, onToggleStatus, onToggleRelease, onReset }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-wrap items-center gap-2">
        <span className={`text-sm font-semibold ${TEXT_TOKENS.secondary}`}>Статусы:</span>
        {STATUS_OPTIONS.map((option) => {
          const isActive = statusFilter.includes(option.value);
          const token = getStatusToken(option.value);
          return (
            <button
              key={option.value}
              onClick={() => onToggleStatus(option.value)}
              className={`px-3 py-1 rounded-full border text-sm transition focus:outline-none ${
                isActive
                  ? `${token.badge} ring-1 ring-offset-1 ${token.ring}`
                  : FILTER_BUTTON_INACTIVE
              }`}
              aria-pressed={isActive}
            >
              {option.label}
            </button>
          );
        })}
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <span className={`text-sm font-semibold ${TEXT_TOKENS.secondary}`}>Релизы:</span>
        {releases.map((release) => {
          const checked = releaseFilter.includes(release.id);
          return (
            <label
              key={release.id}
              className={`flex items-center gap-2 px-2 py-1 rounded border text-sm cursor-pointer transition ${
                checked ? RELEASE_TOKENS.active : RELEASE_TOKENS.inactive
              }`}
            >
              <input
                type="checkbox"
                className="accent-blue-600"
                checked={checked}
                onChange={() => onToggleRelease(release.id)}
              />
              <span className="max-w-[160px] truncate" title={release.title}>
                {release.title}
              </span>
            </label>
          );
        })}
        <button
          onClick={onReset}
          className={`ml-2 text-sm px-3 py-1 rounded-lg transition ${ACTION_TOKENS.cancel.button}`}
        >
          Сбросить фильтры
        </button>
      </div>
    </div>
  );
}

export default FilterPanel;


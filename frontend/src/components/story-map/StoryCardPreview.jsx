import { Circle, Clock, Check } from 'lucide-react';
import { getStatusToken, TEXT_TOKENS } from '../../theme/tokens';
import { Badge } from '../ui';

const priorityVariantMap = {
  'MVP': 'mvp',
  'Release 1': 'release1',
  'Later': 'later',
};

const statusLabels = {
  'todo': 'К выполнению',
  'in_progress': 'В работе',
  'done': 'Готово',
  'blocked': 'Заблокировано',
};

const statusIcons = {
  'todo': <Circle className="w-4 h-4" />,
  'in_progress': <Clock className="w-4 h-4" />,
  'done': <Check className="w-4 h-4" />,
  'blocked': (
    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
      <circle cx="12" cy="12" r="10" strokeWidth="2" />
      <line x1="4.93" y1="4.93" x2="19.07" y2="19.07" strokeWidth="2" />
    </svg>
  ),
};

function StoryCardPreview({ story, position }) {
  if (!story) return null;

  const currentStatus = story.status || 'todo';
  const statusToken = getStatusToken(currentStatus);
  const priorityVariant = priorityVariantMap[story.priority] || 'secondary';

  const acceptanceCriteria = story.acceptance_criteria || [];
  const hasContent = story.description || acceptanceCriteria.length > 0;

  // Позиционирование preview относительно карточки
  const positionStyles = position ? {
    position: 'fixed',
    left: `${position.x}px`,
    top: `${position.y}px`,
    zIndex: 9999,
  } : {};

  return (
    <div
      style={positionStyles}
      className="bg-white rounded-xl shadow-2xl border-2 border-gray-300 p-5 w-96 max-h-[32rem] overflow-y-auto pointer-events-none animate-fade-in scrollbar-thin scrollbar-thumb-gray-300 scrollbar-track-gray-100"
    >
      {/* Заголовок */}
      <div className="flex items-start gap-3 mb-4">
        <div className={`flex-shrink-0 w-7 h-7 rounded-full border-2 flex items-center justify-center ${
          currentStatus === 'todo' ? statusToken.control.idle : statusToken.control.active
        }`}>
          {statusIcons[currentStatus]}
        </div>
        <h3 className={`font-bold text-base leading-snug ${currentStatus === 'done' ? TEXT_TOKENS.done : TEXT_TOKENS.primary}`}>
          {story.title}
        </h3>
      </div>

      {/* Описание */}
      {story.description && (
        <div className="mb-4">
          <p className={`text-sm leading-relaxed ${currentStatus === 'done' ? TEXT_TOKENS.muted : TEXT_TOKENS.secondary}`}>
            {story.description}
          </p>
        </div>
      )}

      {/* Критерии приёмки */}
      {acceptanceCriteria.length > 0 && (
        <div className="mb-4">
          <h4 className={`text-sm font-bold mb-2 ${TEXT_TOKENS.primary}`}>
            Критерии приёмки ({acceptanceCriteria.length}):
          </h4>
          <ul className="space-y-2">
            {acceptanceCriteria.slice(0, 8).map((criterion, idx) => (
              <li key={idx} className={`text-sm flex items-start gap-2 ${TEXT_TOKENS.secondary}`}>
                <span className="text-blue-500 flex-shrink-0 mt-0.5 text-base">•</span>
                <span className="flex-1 leading-relaxed">{criterion}</span>
              </li>
            ))}
            {acceptanceCriteria.length > 8 && (
              <li className="text-sm text-gray-500 italic font-medium pl-5">
                + ещё {acceptanceCriteria.length - 8} критериев...
              </li>
            )}
          </ul>
        </div>
      )}

      {/* Информация */}
      <div className="pt-4 border-t border-gray-200 flex flex-wrap gap-3 items-center">
        {story.priority && (
          <div className="flex items-center gap-2">
            <span className={`text-sm font-semibold ${TEXT_TOKENS.secondary}`}>Релиз:</span>
            <Badge variant={priorityVariant} size="sm" className="uppercase font-bold">
              {story.priority}
            </Badge>
          </div>
        )}
        <div className="flex items-center gap-2">
          <span className={`text-sm font-semibold ${TEXT_TOKENS.secondary}`}>Статус:</span>
          <Badge
            variant={currentStatus === 'done' ? 'success' : currentStatus === 'in_progress' ? 'info' : currentStatus === 'blocked' ? 'danger' : 'secondary'}
            size="sm"
          >
            {statusLabels[currentStatus]}
          </Badge>
        </div>
      </div>

      {/* Подсказка, если нет контента */}
      {!hasContent && (
        <p className="text-sm text-gray-500 italic mt-3 text-center py-2">
          Нажмите на карточку для редактирования
        </p>
      )}

      {/* Индикатор прокрутки */}
      {(story.description?.length > 200 || acceptanceCriteria.length > 5) && (
        <div className="absolute bottom-0 left-0 right-0 h-8 bg-gradient-to-t from-white to-transparent pointer-events-none" />
      )}
    </div>
  );
}

export default StoryCardPreview;

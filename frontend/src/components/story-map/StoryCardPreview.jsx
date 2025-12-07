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
  'blocked': <Circle className="w-4 h-4" />,
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
      className="bg-white rounded-lg shadow-2xl border-2 border-gray-200 p-4 w-80 max-h-96 overflow-y-auto pointer-events-none animate-fade-in"
    >
      {/* Заголовок */}
      <div className="flex items-start gap-2 mb-3">
        <div className={`flex-shrink-0 w-6 h-6 rounded-full border-2 flex items-center justify-center ${
          currentStatus === 'todo' ? statusToken.control.idle : statusToken.control.active
        }`}>
          {statusIcons[currentStatus]}
        </div>
        <h3 className={`font-semibold text-sm leading-snug ${currentStatus === 'done' ? TEXT_TOKENS.done : TEXT_TOKENS.primary}`}>
          {story.title}
        </h3>
      </div>

      {/* Описание */}
      {story.description && (
        <div className="mb-3">
          <p className={`text-xs leading-relaxed ${currentStatus === 'done' ? TEXT_TOKENS.muted : TEXT_TOKENS.secondary}`}>
            {story.description}
          </p>
        </div>
      )}

      {/* Критерии приёмки */}
      {acceptanceCriteria.length > 0 && (
        <div className="mb-3">
          <h4 className={`text-xs font-semibold mb-1.5 ${TEXT_TOKENS.secondary}`}>
            Критерии приёмки ({acceptanceCriteria.length}):
          </h4>
          <ul className="space-y-1">
            {acceptanceCriteria.slice(0, 5).map((criterion, idx) => (
              <li key={idx} className={`text-xs flex items-start gap-1.5 ${TEXT_TOKENS.secondary}`}>
                <span className="text-blue-500 flex-shrink-0 mt-0.5">•</span>
                <span className="flex-1">{criterion}</span>
              </li>
            ))}
            {acceptanceCriteria.length > 5 && (
              <li className="text-xs text-gray-400 italic">
                и ещё {acceptanceCriteria.length - 5}...
              </li>
            )}
          </ul>
        </div>
      )}

      {/* Информация */}
      <div className="pt-3 border-t border-gray-100 flex flex-wrap gap-2 items-center">
        {story.priority && (
          <div className="flex items-center gap-1.5">
            <span className={`text-xs font-medium ${TEXT_TOKENS.muted}`}>Релиз:</span>
            <Badge variant={priorityVariant} size="xs" className="uppercase font-semibold">
              {story.priority}
            </Badge>
          </div>
        )}
        <div className="flex items-center gap-1.5">
          <span className={`text-xs font-medium ${TEXT_TOKENS.muted}`}>Статус:</span>
          <Badge
            variant={currentStatus === 'done' ? 'success' : currentStatus === 'in_progress' ? 'info' : 'secondary'}
            size="xs"
          >
            {statusLabels[currentStatus]}
          </Badge>
        </div>
      </div>

      {/* Подсказка, если нет контента */}
      {!hasContent && (
        <p className="text-xs text-gray-400 italic mt-2">
          Нажмите на карточку для редактирования
        </p>
      )}
    </div>
  );
}

export default StoryCardPreview;

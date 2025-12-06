import {
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Circle, Clock, Check, Sparkles, GripVertical } from 'lucide-react';

function StoryCard({
  story,
  taskId,
  releaseId,
  onEdit,
  onOpenAI,
  onStatusChange,
  dragDisabled = false,
  handleDisabled = false,
  statusLoading,
  containerStyle = {},
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: `${story.id}-${taskId}-${releaseId}`,
  });

  const style = {
    ...containerStyle,
    transform: CSS.Transform.toString(transform),
    transition: transition || 'transform 250ms cubic-bezier(0.4, 0, 0.2, 1), box-shadow 200ms ease',
    opacity: dragDisabled ? 0.5 : 1,
    zIndex: isDragging ? 1000 : 'auto',
    boxShadow: isDragging ? '0 20px 40px rgba(0,0,0,0.25), 0 8px 16px rgba(0,0,0,0.15)' : undefined,
    cursor: isDragging ? 'grabbing' : undefined,
    scale: isDragging ? '1.05' : undefined,
  };

  // Цвет приоритета (WCAG AA compliant - минимум 4.5:1 контраст)
  const priorityColors = {
    'MVP': 'bg-red-100 text-red-800 border-red-300',
    'Release 1': 'bg-orange-100 text-orange-800 border-orange-300',
    'Later': 'bg-gray-100 text-gray-700 border-gray-300',
  };

  // Цвета статуса для левой полоски
  const statusColors = {
    'todo': 'bg-gray-300',
    'in_progress': 'bg-blue-500',
    'done': 'bg-green-500',
  };

  // Иконки статуса
  const statusIcons = {
    'todo': <Circle className="w-4 h-4" />,
    'in_progress': <Clock className="w-4 h-4" />,
    'done': <Check className="w-4 h-4" />,
  };

  const currentStatus = story.status || 'todo';
  
  // Следующий статус при клике
  const getNextStatus = (current) => {
    const cycle = ['todo', 'in_progress', 'done'];
    const idx = cycle.indexOf(current);
    return cycle[(idx + 1) % cycle.length];
  };

  const handleStatusClick = (e) => {
    e.stopPropagation();
    const nextStatus = getNextStatus(currentStatus);
    onStatusChange(story.id, nextStatus);
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`relative p-3 rounded-lg shadow-sm hover:shadow-lg transition-all duration-200 text-sm border group cursor-pointer overflow-hidden ${
        currentStatus === 'done'
          ? 'bg-green-50 border-green-200 hover:border-green-300'
          : currentStatus === 'in_progress'
          ? 'bg-blue-50 border-blue-200 hover:border-blue-300'
          : 'bg-yellow-100 border-yellow-300 hover:border-yellow-400'
      }`}
      onClick={onEdit}
    >
      {/* Status indicator bar (left side) */}
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${statusColors[currentStatus]}`} />

      {/* Drag Handle - min 44x44px touch target */}
      <div
        {...(!handleDisabled ? attributes : {})}
        {...(!handleDisabled ? listeners : {})}
        onClick={(e) => e.stopPropagation()}
        aria-disabled={handleDisabled}
        aria-label="Перетащить карточку"
        className="absolute top-0 right-0 cursor-grab active:cursor-grabbing min-w-[44px] min-h-[44px] flex items-center justify-center hover:bg-white/50 rounded-md opacity-40 hover:opacity-100 transition z-10"
        title="Перетащить"
      >
        <GripVertical className="h-5 w-5 text-gray-500" />
      </div>

      {/* Title with status toggle */}
      <div className="flex items-start gap-2 pr-7">
        <button
          onClick={handleStatusClick}
          disabled={statusLoading}
          className={`flex-shrink-0 w-7 h-7 min-w-[28px] min-h-[28px] rounded-full border-2 flex items-center justify-center text-sm font-bold transition-all hover:scale-110 ${
            currentStatus === 'done'
              ? 'bg-green-500 border-green-500 text-white'
              : currentStatus === 'in_progress'
              ? 'bg-blue-500 border-blue-500 text-white'
              : 'bg-white border-gray-300 text-gray-400 hover:border-gray-400'
          }`}
          title={currentStatus === 'todo' ? 'Начать' : currentStatus === 'in_progress' ? 'Завершить' : 'Вернуть в работу'}
        >
          {statusLoading ? '…' : statusIcons[currentStatus]}
        </button>
        <div className={`font-medium leading-snug mb-1.5 line-clamp-2 ${currentStatus === 'done' ? 'text-gray-500 line-through' : 'text-gray-800'}`}>
          {story.title}
        </div>
      </div>

      {/* Description */}
      {story.description && (
        <div className={`text-xs line-clamp-2 mb-2 ml-7 ${currentStatus === 'done' ? 'text-gray-500' : 'text-gray-700'}`}>
          {story.description}
        </div>
      )}

      {/* Footer: Priority + AC count */}
      <div className="flex items-center gap-2 mt-auto pt-1 ml-7">
        {story.priority && (
          <span className={`text-[10px] uppercase px-2 py-0.5 rounded border font-semibold ${priorityColors[story.priority] || priorityColors['Later']}`}>
            {story.priority}
          </span>
        )}
        {story.acceptance_criteria && story.acceptance_criteria.length > 0 && (
          <span className="text-[10px] text-gray-700 bg-white/80 px-1.5 py-0.5 rounded border border-gray-200">
            {story.acceptance_criteria.length} КП
          </span>
        )}
        
        {/* AI Button - показывается при hover, min 44px touch target */}
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onOpenAI();
          }}
          className="ml-auto text-xs bg-gradient-to-r from-purple-500 to-blue-500 text-white px-3 py-1.5 min-h-[32px] rounded hover:from-purple-600 hover:to-blue-600 transition opacity-0 group-hover:opacity-100 flex items-center gap-1"
          type="button"
          title="AI Ассистент"
          aria-label={`Улучшить историю "${story.title}" с помощью AI`}
        >
          <Sparkles className="w-3 h-3" />
          AI
        </button>
      </div>
    </div>
  );
}

export default StoryCard;


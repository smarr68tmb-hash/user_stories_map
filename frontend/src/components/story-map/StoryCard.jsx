import {
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Circle, Clock, Check, Sparkles, GripVertical } from 'lucide-react';
import { getStatusToken, STATUS_FLOW, TEXT_TOKENS, ACTION_TOKENS } from '../../theme/tokens';
import { Badge } from '../ui';
import useHoverPreview from '../../hooks/useHoverPreview';
import StoryCardPreview from './StoryCardPreview';

// Map priority to Badge variant
const priorityVariantMap = {
  'MVP': 'mvp',
  'Release 1': 'release1',
  'Later': 'later',
};

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

  // Preview при hover
  const { isShowing, position, handleMouseEnter, handleMouseLeave } = useHoverPreview(400);

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

  // Иконки статуса
  const statusIcons = {
    'todo': <Circle className="w-4 h-4" />,
    'in_progress': <Clock className="w-4 h-4" />,
    'done': <Check className="w-4 h-4" />,
    'blocked': <Circle className="w-4 h-4" />,
  };

  const currentStatus = story.status || 'todo';
  const statusToken = getStatusToken(currentStatus);
  const priorityVariant = priorityVariantMap[story.priority] || 'secondary';
  
  // Следующий статус при клике
  const getNextStatus = (current) => {
    const idx = STATUS_FLOW.indexOf(current);
    const safeIndex = idx === -1 ? 0 : idx;
    return STATUS_FLOW[(safeIndex + 1) % STATUS_FLOW.length];
  };

  const handleStatusClick = (e) => {
    e.stopPropagation();
    const nextStatus = getNextStatus(currentStatus);
    onStatusChange(story.id, nextStatus);
  };

  return (
    <>
      <div
        ref={setNodeRef}
        style={style}
        className={`relative p-3 rounded-lg shadow-sm hover:shadow-lg transition-all duration-200 text-sm border group cursor-pointer overflow-hidden ${statusToken.surface}`}
        onClick={onEdit}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
      {/* Status indicator bar (left side) */}
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${statusToken.indicator}`} />

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
        <GripVertical className={`h-5 w-5 ${TEXT_TOKENS.muted}`} />
      </div>

      {/* Title with status toggle */}
      <div className="flex items-start gap-2 pr-7">
        <button
          onClick={handleStatusClick}
          disabled={statusLoading}
          className={`flex-shrink-0 w-7 h-7 min-w-[28px] min-h-[28px] rounded-full border-2 flex items-center justify-center text-sm font-bold transition-all hover:scale-110 ${
            currentStatus === 'todo' ? statusToken.control.idle : statusToken.control.active
          }`}
          title={currentStatus === 'todo' ? 'Начать' : currentStatus === 'in_progress' ? 'Завершить' : 'Вернуть в работу'}
        >
          {statusLoading ? '…' : statusIcons[currentStatus]}
        </button>
        <div className={`font-medium leading-snug mb-1.5 line-clamp-2 ${currentStatus === 'done' ? TEXT_TOKENS.done : TEXT_TOKENS.primary}`}>
          {story.title}
        </div>
      </div>

      {/* Description */}
      {story.description && (
        <div className={`text-xs line-clamp-2 mb-2 ml-7 ${currentStatus === 'done' ? TEXT_TOKENS.muted : TEXT_TOKENS.secondary}`}>
          {story.description}
        </div>
      )}

      {/* Footer: Priority + AC count */}
      <div className="flex items-center gap-2 mt-auto pt-1 ml-7">
        {story.priority && (
          <Badge variant={priorityVariant} size="xs" className="uppercase font-semibold">
            {story.priority}
          </Badge>
        )}
        {story.acceptance_criteria && story.acceptance_criteria.length > 0 && (
          <Badge variant="ghost" size="xs">
            {story.acceptance_criteria.length} КП
          </Badge>
        )}
        
        {/* AI Button - показывается при hover, min 44px touch target */}
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onOpenAI();
          }}
          className={`ml-auto text-xs ${ACTION_TOKENS.ai.buttonSmall} transition opacity-0 group-hover:opacity-100 flex items-center gap-1`}
          type="button"
          title="AI Ассистент"
          aria-label={`Улучшить историю "${story.title}" с помощью AI`}
        >
          <Sparkles className="w-3 h-3" />
          AI
        </button>
      </div>
      </div>

      {/* Preview при наведении */}
      {isShowing && !isDragging && (
        <StoryCardPreview story={story} position={position} />
      )}
    </>
  );
}

export default StoryCard;


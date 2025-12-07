import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { Sparkles, GripVertical } from 'lucide-react';
import { getStatusToken, STATUS_FLOW, TEXT_TOKENS, ACTION_TOKENS } from '../../theme/tokens';
import { Badge } from '../ui';
import useHoverPreview from '../../hooks/useHoverPreview';
import StoryCardPreview from './StoryCardPreview';
import { statusIcons, getPriorityVariant } from './storyMeta';

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

  const currentStatus = story.status || 'todo';
  const statusToken = getStatusToken(currentStatus);
  const priorityVariant = getPriorityVariant(story.priority);
  
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
        className={`relative p-4 rounded-xl shadow-md hover:shadow-xl transition-all duration-200 text-sm border-2 group cursor-pointer overflow-hidden ${statusToken.surface}`}
        onClick={onEdit}
        onMouseEnter={handleMouseEnter}
        onMouseLeave={handleMouseLeave}
      >
      {/* Status indicator bar (left side) */}
      <div className={`absolute left-0 top-0 bottom-0 w-1.5 ${statusToken.indicator}`} />

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
      <div className="flex items-start gap-3 pr-10">
        <button
          onClick={handleStatusClick}
          disabled={statusLoading}
          className={`flex-shrink-0 w-8 h-8 min-w-[32px] min-h-[32px] rounded-full border-2 flex items-center justify-center text-sm font-bold transition-all hover:scale-110 shadow-sm ${
            currentStatus === 'todo' ? statusToken.control.idle : statusToken.control.active
          }`}
          title={currentStatus === 'todo' ? 'Начать' : currentStatus === 'in_progress' ? 'Завершить' : 'Вернуть в работу'}
        >
          {statusLoading ? '…' : statusIcons[currentStatus]}
        </button>
        <div className={`font-semibold text-base leading-snug mb-2 line-clamp-3 ${currentStatus === 'done' ? TEXT_TOKENS.done : TEXT_TOKENS.primary}`}>
          {story.title}
        </div>
      </div>

      {/* Description */}
      {story.description && (
        <div className={`text-sm line-clamp-3 mb-3 ml-11 leading-relaxed ${currentStatus === 'done' ? TEXT_TOKENS.muted : TEXT_TOKENS.secondary}`}>
          {story.description}
        </div>
      )}

      {/* Footer: Priority + AC count */}
      <div className="flex items-center justify-between gap-2 mt-auto pt-2">
        <div className="flex items-center gap-2 ml-11 flex-wrap">
          {story.priority && (
            <Badge variant={priorityVariant} size="xs" className="uppercase font-semibold text-[10px]">
              {story.priority}
            </Badge>
          )}
          {story.acceptance_criteria && story.acceptance_criteria.length > 0 && (
            <Badge variant="ghost" size="xs" className="font-medium">
              {story.acceptance_criteria.length} КП
            </Badge>
          )}
        </div>

        {/* AI Button - показывается при hover, min 44px touch target */}
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onOpenAI();
          }}
          className={`text-xs ${ACTION_TOKENS.ai.buttonSmall} transition opacity-0 group-hover:opacity-100 flex items-center gap-1 px-2 py-1 min-h-[28px]`}
          type="button"
          title="AI Ассистент"
          aria-label={`Улучшить историю "${story.title}" с помощью AI`}
        >
          <Sparkles className="w-3.5 h-3.5" />
          <span className="font-medium text-[10px]">AI</span>
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


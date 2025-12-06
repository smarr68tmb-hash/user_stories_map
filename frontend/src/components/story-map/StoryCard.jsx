import {
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

function StoryCard({ story, taskId, releaseId, onEdit, onOpenAI, onStatusChange, isMoving, statusLoading }) {
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
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging || isMoving ? 0.5 : 1,
  };

  // Цвет приоритета
  const priorityColors = {
    'MVP': 'bg-red-100 text-red-700 border-red-200',
    'Release 1': 'bg-orange-100 text-orange-700 border-orange-200',
    'Later': 'bg-gray-100 text-gray-600 border-gray-200',
  };

  // Цвета статуса для левой полоски
  const statusColors = {
    'todo': 'bg-gray-300',
    'in_progress': 'bg-blue-500',
    'done': 'bg-green-500',
  };

  // Иконки статуса
  const statusIcons = {
    'todo': '○',
    'in_progress': '◐',
    'done': '✓',
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
      className={`relative p-3 rounded-lg shadow-sm hover:shadow-md transition-all text-sm border group cursor-pointer overflow-hidden ${
        currentStatus === 'done' 
          ? 'bg-green-50 border-green-200' 
          : currentStatus === 'in_progress'
          ? 'bg-blue-50 border-blue-200'
          : 'bg-yellow-100 border-yellow-300'
      }`}
      onClick={onEdit}
    >
      {/* Status indicator bar (left side) */}
      <div className={`absolute left-0 top-0 bottom-0 w-1 ${statusColors[currentStatus]}`} />

      {/* Drag Handle */}
      <div
        {...(!isMoving ? attributes : {})}
        {...(!isMoving ? listeners : {})}
        onClick={(e) => e.stopPropagation()}
        className="absolute top-2 right-2 cursor-grab active:cursor-grabbing p-1.5 hover:bg-white/50 rounded-md opacity-40 hover:opacity-100 transition z-10"
        title="Перетащить"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 text-gray-500" viewBox="0 0 20 20" fill="currentColor">
          <path d="M7 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 2zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 14zm6-8a2 2 0 1 0-.001-4.001A2 2 0 0 0 13 6zm0 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 14z" />
        </svg>
      </div>

      {/* Title with status toggle */}
      <div className="flex items-start gap-2 pr-7">
        <button
          onClick={handleStatusClick}
          disabled={statusLoading}
          className={`flex-shrink-0 w-5 h-5 rounded-full border-2 flex items-center justify-center text-xs font-bold transition-all hover:scale-110 ${
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
        <div className={`text-xs line-clamp-2 mb-2 ml-7 ${currentStatus === 'done' ? 'text-gray-400' : 'text-gray-600'}`}>
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
          <span className="text-[10px] text-gray-500 bg-white/60 px-1.5 py-0.5 rounded">
            {story.acceptance_criteria.length} AC
          </span>
        )}
        
        {/* AI Button - показывается при hover */}
        <button
          onClick={(e) => {
            e.preventDefault();
            e.stopPropagation();
            onOpenAI();
          }}
          className="ml-auto text-[10px] bg-gradient-to-r from-purple-500 to-blue-500 text-white px-2 py-1 rounded hover:from-purple-600 hover:to-blue-600 transition opacity-0 group-hover:opacity-100"
          type="button"
          title="AI Assistant"
        >
          ✨ AI
        </button>
      </div>
    </div>
  );
}

export default StoryCard;


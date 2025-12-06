import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';

function TaskColumn({ 
  task, 
  isEditing, 
  editingTaskTitle, 
  setEditingTaskTitle, 
  onUpdateTask, 
  onStartEditing, 
  onDelete,
  setEditingTaskId,
  dragDisabled = false,
  handleDisabled = false,
  isUpdating,
  isDeleting,
  pendingDelete,
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({
    id: `task-${task.id}`,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging || dragDisabled ? 0.5 : 1,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="w-[220px] flex-shrink-0 bg-blue-50 border-r border-gray-200 p-3 text-sm font-semibold text-center text-gray-700 min-h-[60px] flex items-center justify-center group relative"
    >
      {isEditing ? (
        <div className="flex items-center gap-2 w-full">
          <input
            type="text"
            value={editingTaskTitle}
            onChange={(e) => setEditingTaskTitle(e.target.value)}
            onBlur={() => onUpdateTask(task.id)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') {
                onUpdateTask(task.id);
              } else if (e.key === 'Escape') {
                setEditingTaskId(null);
                setEditingTaskTitle('');
              }
            }}
            className="flex-1 px-2 py-1 text-xs border rounded bg-white text-gray-800"
            autoFocus
            disabled={isUpdating}
          />
        </div>
      ) : (
        <>
          {/* Drag Handle */}
          <div
            {...(!handleDisabled ? attributes : {})}
            {...(!handleDisabled ? listeners : {})}
            aria-disabled={handleDisabled}
            className="absolute top-2 left-2 cursor-grab active:cursor-grabbing p-1 opacity-40 hover:opacity-100 transition z-10"
            title="Перетащить для изменения порядка"
          >
            <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 text-gray-500" viewBox="0 0 20 20" fill="currentColor">
              <path d="M7 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 2zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 14zm6-8a2 2 0 1 0-.001-4.001A2 2 0 0 0 13 6zm0 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 14z" />
            </svg>
          </div>
          <span 
            className="leading-tight cursor-pointer hover:underline"
            onDoubleClick={() => onStartEditing(task)}
            title="Двойной клик для редактирования"
          >
            {task.title}
          </span>
          <div className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
            <button
              onClick={() => onStartEditing(task)}
              className="p-1 text-blue-600 hover:text-blue-800 hover:bg-blue-200 rounded text-xs disabled:opacity-60"
              disabled={isUpdating || isDeleting}
              title="Редактировать"
            >
              ✏️
            </button>
            <button
              onClick={() => onDelete(task.id)}
              className={`p-1 text-red-600 hover:text-red-800 hover:bg-red-200 rounded text-xs ${pendingDelete ? 'bg-red-100 border border-red-300' : ''}`}
              disabled={isDeleting || isUpdating}
              title="Удалить"
            >
              {isDeleting ? '…' : pendingDelete ? 'Подтвердить' : '🗑️'}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export default TaskColumn;


import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { GripVertical, Pencil, Trash2, Check } from 'lucide-react';
import { getSeverityToken, TEXT_TOKENS, ACTION_TOKENS, SURFACE_TOKENS } from '../../theme/tokens';

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

  const confirmTone = getSeverityToken('critical');

  // Surface token for task column header
  const TASK_COLUMN_SURFACE = 'bg-blue-50 border-r border-gray-200';

  const style = {
    transform: CSS.Transform.toString(transform),
    transition: transition || 'transform 200ms ease',
    opacity: dragDisabled ? 0.5 : 1,
    zIndex: isDragging ? 1000 : 'auto',
    boxShadow: isDragging ? '0 8px 20px rgba(0,0,0,0.15)' : undefined,
    cursor: isDragging ? 'grabbing' : undefined,
  };

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={`w-[220px] flex-shrink-0 ${TASK_COLUMN_SURFACE} p-3 text-sm font-semibold text-center ${TEXT_TOKENS.secondary} min-h-[60px] flex items-center justify-center group relative`}
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
            className={`flex-1 px-2 py-1 text-xs border rounded bg-white ${TEXT_TOKENS.primary}`}
            autoFocus
            disabled={isUpdating}
          />
        </div>
      ) : (
        <>
          {/* Drag Handle - min 44x44px touch target */}
          <div
            {...(!handleDisabled ? attributes : {})}
            {...(!handleDisabled ? listeners : {})}
            aria-disabled={handleDisabled}
            className="absolute top-0 left-0 cursor-grab active:cursor-grabbing min-w-[44px] min-h-[44px] flex items-center justify-center opacity-40 hover:opacity-100 hover:bg-blue-100/50 rounded transition z-10"
            title="Перетащить для изменения порядка"
          >
            <GripVertical className={`w-5 h-5 ${TEXT_TOKENS.muted}`} />
          </div>
          <span 
            className="leading-tight cursor-pointer hover:underline"
            onDoubleClick={() => onStartEditing(task)}
            title="Двойной клик для редактирования"
          >
            {task.title}
          </span>
          <div className="absolute top-0 right-0 opacity-0 group-hover:opacity-100 transition-opacity flex">
            <button
              onClick={() => onStartEditing(task)}
              className={`min-w-[36px] min-h-[36px] flex items-center justify-center rounded disabled:opacity-60 ${ACTION_TOKENS.edit.iconButton}`}
              disabled={isUpdating || isDeleting}
              title="Редактировать"
            >
              <Pencil className="w-4 h-4" />
            </button>
            <button
              onClick={() => onDelete(task.id)}
              className={`min-w-[36px] min-h-[36px] flex items-center justify-center rounded ${
                pendingDelete
                  ? `${confirmTone.badgeStrong} border`
                  : ACTION_TOKENS.delete.iconButton
              }`}
              disabled={isDeleting || isUpdating}
              title="Удалить"
            >
              {isDeleting ? (
                <span className="animate-pulse">…</span>
              ) : pendingDelete ? (
                <Check className="w-4 h-4" />
              ) : (
                <Trash2 className="w-4 h-4" />
              )}
            </button>
          </div>
        </>
      )}
    </div>
  );
}

export default TaskColumn;


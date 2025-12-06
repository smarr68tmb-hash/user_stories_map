import {
  SortableContext,
  horizontalListSortingStrategy,
} from '@dnd-kit/sortable';
import { useDroppable } from '@dnd-kit/core';
import TaskColumn from './TaskColumn';

function ActivityHeader({
  activities,
  editingActivityId,
  editingActivityTitle,
  setEditingActivityTitle,
  onUpdateActivity,
  onStartEditingActivity,
  onDeleteActivity,
  activityLoading,
  pendingDeleteActivityId,
  addingActivity,
  onStartAddActivity,
  onCancelAddActivity,
  newActivityTitle,
  setNewActivityTitle,
  onAddActivity,
  onAddTask,
  taskLoading,
  editingTaskId,
  editingTaskTitle,
  setEditingTaskTitle,
  onUpdateTask,
  onStartEditingTask,
  onDeleteTask,
  setEditingTaskId,
  pendingDeleteTaskId,
  addingTaskActivityId,
  taskDrafts,
  updateTaskDraft,
  startAddingTask,
  stopAddingTask,
  isTaskHandleDisabled,
  isTaskDragDisabled,
}) {
  return (
    <div className="sticky top-0 z-10 bg-gray-50 border-b-2 border-gray-300">
      <div className="flex border-b border-gray-200">
        <div className="w-32 flex-shrink-0 bg-gray-100 border-r-2 border-gray-300 p-2 flex items-center justify-center">
          <span className="text-xs font-bold text-gray-600 uppercase">Releases</span>
        </div>
        {activities.map((act) => {
          const taskCount = act.tasks.length;
          const activityWidth = (taskCount + 1) * 220;
          const isEditing = editingActivityId === act.id;
          const isDeleting = activityLoading.isDeleting(act.id);
          const isUpdating = activityLoading.isUpdating(act.id);
          const pendingDelete = pendingDeleteActivityId === act.id;

          return (
            <div
              key={act.id}
              className="bg-blue-100 border-r border-gray-200 p-3 text-center font-bold text-blue-800 flex items-center justify-center group relative"
              style={{ width: `${activityWidth}px`, minWidth: '220px' }}
            >
              {isEditing ? (
                <div className="flex items-center gap-2 w-full">
                  <input
                    type="text"
                    value={editingActivityTitle}
                    onChange={(e) => setEditingActivityTitle(e.target.value)}
                    onBlur={() => onUpdateActivity(act.id)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter') {
                        onUpdateActivity(act.id);
                      } else if (e.key === 'Escape') {
                        onStartEditingActivity(null);
                        setEditingActivityTitle('');
                      }
                    }}
                    className="flex-1 px-2 py-1 text-sm border rounded bg-white text-gray-800"
                    autoFocus
                    disabled={isUpdating}
                  />
                </div>
              ) : (
                <>
                  <span
                    className="text-sm cursor-pointer hover:underline"
                    onDoubleClick={() => onStartEditingActivity(act)}
                    title="Двойной клик для редактирования"
                  >
                    {act.title}
                  </span>
                  <div className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                    <button
                      onClick={() => onStartEditingActivity(act)}
                      className="p-1 text-blue-600 hover:text-blue-800 hover:bg-blue-200 rounded disabled:opacity-50"
                      disabled={isDeleting || isUpdating}
                      title="Редактировать"
                    >
                      ✏️
                    </button>
                    <button
                      onClick={() => onDeleteActivity(act.id)}
                      className={`p-1 text-red-600 hover:text-red-800 hover:bg-red-200 rounded ${pendingDelete ? 'bg-red-100 border border-red-300' : ''}`}
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
        })}
        <div className="flex-shrink-0 border-r border-gray-200">
          {addingActivity ? (
            <div className="p-3 bg-green-50 border border-green-300">
              <input
                type="text"
                placeholder="Название активности"
                value={newActivityTitle}
                onChange={(e) => setNewActivityTitle(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    onAddActivity();
                  } else if (e.key === 'Escape') {
                    onCancelAddActivity();
                  }
                }}
                className="w-full px-2 py-1 text-sm border rounded"
                autoFocus
              />
              <div className="flex gap-2 mt-2">
                <button
                  onClick={onAddActivity}
                  disabled={activityLoading.isCreating}
                  aria-busy={activityLoading.isCreating}
                  className={`flex-1 bg-green-600 text-white text-xs py-1 px-2 rounded hover:bg-green-700 ${activityLoading.isCreating ? 'opacity-60 cursor-not-allowed' : ''}`}
                >
                  {activityLoading.isCreating ? 'Добавление...' : 'Добавить'}
                </button>
                <button
                  onClick={onCancelAddActivity}
                  className="flex-1 bg-gray-300 text-gray-700 text-xs py-1 px-2 rounded hover:bg-gray-400"
                >
                  Отмена
                </button>
              </div>
            </div>
          ) : (
            <button
              onClick={onStartAddActivity}
              className="p-3 text-gray-400 hover:text-gray-600 hover:bg-gray-100 border-2 border-dashed border-gray-300 rounded transition"
              title="Добавить активность"
            >
              + Activity
            </button>
          )}
        </div>
      </div>

      <div className="flex">
        <div className="w-32 flex-shrink-0 bg-gray-100 border-r-2 border-gray-300"></div>
        {activities.map((act) => {
          const taskCount = act.tasks.length;
          const activityWidth = (taskCount + 1) * 220;
          return (
            <SortableContext
              key={`activity-tasks-${act.id}`}
              items={act.tasks.map((t) => `task-${t.id}`)}
              strategy={horizontalListSortingStrategy}
            >
              <DroppableTaskZone
                activityId={act.id}
                className="flex"
                style={{ width: `${activityWidth}px`, flexShrink: 0 }}
                id={`activity-tasks-${act.id}`}
              >
                {act.tasks.map((task) => {
                  const isEditing = editingTaskId === task.id;
                  return (
                    <TaskColumn
                      key={task.id}
                      task={task}
                      isEditing={isEditing}
                      editingTaskTitle={editingTaskTitle}
                      setEditingTaskTitle={setEditingTaskTitle}
                      onUpdateTask={onUpdateTask}
                      onStartEditing={onStartEditingTask}
                      onDelete={onDeleteTask}
                      setEditingTaskId={setEditingTaskId}
                      dragDisabled={isTaskDragDisabled(task.id)}
                      handleDisabled={isTaskHandleDisabled(task.id)}
                      isUpdating={taskLoading.isUpdating(task.id)}
                      isDeleting={taskLoading.isDeleting(task.id)}
                      pendingDelete={pendingDeleteTaskId === task.id}
                    />
                  );
                })}
                <div className="flex-shrink-0 border-r border-gray-200 w-[220px]">
                  {addingTaskActivityId === act.id ? (
                    <div className="p-3 bg-green-50 border border-green-300 min-h-[60px]">
                      <input
                        type="text"
                        placeholder="Название задачи"
                        value={taskDrafts[act.id]?.title || ''}
                        onChange={(e) => updateTaskDraft(act.id, { title: e.target.value, error: null })}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            onAddTask(act.id);
                          } else if (e.key === 'Escape') {
                            stopAddingTask();
                          }
                        }}
                        className="w-full px-2 py-1 text-xs border rounded"
                        autoFocus
                      />
                      {taskDrafts[act.id]?.error && (
                        <p className="text-[11px] text-red-600 mt-1">{taskDrafts[act.id]?.error}</p>
                      )}
                      <div className="flex gap-2 mt-2">
                        <button
                          onClick={() => onAddTask(act.id)}
                          disabled={taskLoading.isCreating(act.id)}
                          aria-busy={taskLoading.isCreating(act.id)}
                          className={`flex-1 bg-green-600 text-white text-xs py-1 px-2 rounded hover:bg-green-700 ${taskLoading.isCreating(act.id) ? 'opacity-60 cursor-not-allowed' : ''}`}
                        >
                          {taskLoading.isCreating(act.id) ? 'Добавление...' : 'Добавить'}
                        </button>
                        <button
                          onClick={stopAddingTask}
                          className="flex-1 bg-gray-300 text-gray-700 text-xs py-1 px-2 rounded hover:bg-gray-400"
                        >
                          Отмена
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => startAddingTask(act.id)}
                      className="w-full h-[60px] text-gray-400 hover:text-gray-600 hover:bg-gray-100 border-2 border-dashed border-gray-300 rounded transition text-xs flex items-center justify-center"
                      title="Добавить задачу"
                    >
                      + Task
                    </button>
                  )}
                </div>
              </DroppableTaskZone>
            </SortableContext>
          );
        })}
      </div>
    </div>
  );
}

function DroppableTaskZone({ activityId, children, className = '', style, id }) {
  const { setNodeRef, isOver } = useDroppable({
    id: `activity-tasks-${activityId}`,
    data: {
      type: 'activity-tasks',
      activityId,
    },
  });

  const zoneClassName = `${className} ${isOver ? 'bg-blue-50' : ''}`.trim();

  return (
    <div
      ref={setNodeRef}
      className={zoneClassName}
      style={style}
      id={id}
    >
      {children}
    </div>
  );
}

export default ActivityHeader;


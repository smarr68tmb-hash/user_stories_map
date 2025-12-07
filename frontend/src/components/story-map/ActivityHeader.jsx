import {
  SortableContext,
  horizontalListSortingStrategy,
} from '@dnd-kit/sortable';
import { useDroppable } from '@dnd-kit/core';
import { Pencil, Trash2, Check } from 'lucide-react';
import TaskColumn from './TaskColumn';
import { TEXT_TOKENS, ACTION_TOKENS, getSeverityToken } from '../../theme/tokens';
import { Button, Input } from '../ui';

// Local surface tokens for activity header
const ACTIVITY_HEADER_TOKENS = {
  surface: 'bg-blue-100 border-r border-gray-200',
  surfaceHover: 'hover:bg-blue-200',
  title: 'text-blue-900',
  input: 'bg-white text-gray-800',
};

const ADD_FORM_TOKENS = {
  surface: 'bg-green-50 border border-green-300',
};

const ADD_PLACEHOLDER_TOKENS = {
  button: 'text-gray-400 hover:text-gray-600 hover:bg-gray-100 border-2 border-dashed border-gray-300',
};

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
  activityWidths,
  taskColumnWidth = 220,
}) {
  return (
    <div className="sticky top-0 z-10 bg-gray-50 border-b-2 border-gray-300">
      <div className="flex border-b border-gray-200">
        <div className="w-32 flex-shrink-0 bg-gray-100 border-r-2 border-gray-300 p-2 flex items-center justify-center">
          <span className="text-xs font-bold text-gray-600 uppercase">Релизы</span>
        </div>
        {activities.map((act) => {
          const activityWidth = activityWidths?.[act.id] ?? (act.tasks.length + 1) * taskColumnWidth;
          const isEditing = editingActivityId === act.id;
          const isDeleting = activityLoading.isDeleting(act.id);
          const isUpdating = activityLoading.isUpdating(act.id);
          const pendingDelete = pendingDeleteActivityId === act.id;

          return (
            <div
              key={act.id}
              className={`${ACTIVITY_HEADER_TOKENS.surface} p-3 text-center font-bold ${ACTIVITY_HEADER_TOKENS.title} flex items-center justify-center group relative transition-colors duration-200 ${ACTIVITY_HEADER_TOKENS.surfaceHover}`}
              style={{ width: activityWidth, minWidth: taskColumnWidth }}
            >
              {isEditing ? (
                <div className="flex items-center gap-2 w-full">
                  <Input
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
                    size="sm"
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
                  <div className="absolute top-0 right-0 opacity-0 group-hover:opacity-100 transition-opacity duration-200 flex">
                    <button
                      onClick={() => onStartEditingActivity(act)}
                      className={`min-w-[40px] min-h-[40px] flex items-center justify-center rounded disabled:opacity-50 transition-colors duration-150 ${ACTION_TOKENS.edit.iconButton}`}
                      disabled={isDeleting || isUpdating}
                      title="Редактировать"
                      aria-label={`Редактировать активность ${act.title}`}
                    >
                      <Pencil className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => onDeleteActivity(act.id)}
                      className={`min-w-[40px] min-h-[40px] flex items-center justify-center rounded transition-all duration-150 ${pendingDelete ? getSeverityToken('critical').surface : ACTION_TOKENS.delete.iconButton}`}
                      disabled={isDeleting || isUpdating}
                      title="Удалить"
                      aria-label={`Удалить активность ${act.title}`}
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
        })}
        <div className="flex-shrink-0 border-r border-gray-200">
          {addingActivity ? (
            <div className={`p-3 ${ADD_FORM_TOKENS.surface}`}>
              <Input
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
                size="sm"
                autoFocus
              />
              <div className="flex gap-2 mt-2">
                <Button
                  variant="success"
                  size="xs"
                  onClick={onAddActivity}
                  loading={activityLoading.isCreating}
                  className="flex-1"
                >
                  Добавить
                </Button>
                <Button
                  variant="secondary"
                  size="xs"
                  onClick={onCancelAddActivity}
                  className="flex-1"
                >
                  Отмена
                </Button>
              </div>
            </div>
          ) : (
            <button
              onClick={onStartAddActivity}
              className={`p-3 rounded transition ${ADD_PLACEHOLDER_TOKENS.button}`}
              title="Добавить активность"
            >
              + Активность
            </button>
          )}
        </div>
      </div>

      <div className="flex">
        <div className="w-32 flex-shrink-0 bg-gray-100 border-r-2 border-gray-300"></div>
        {activities.map((act) => {
          const activityWidth = activityWidths?.[act.id] ?? (act.tasks.length + 1) * taskColumnWidth;
          return (
            <SortableContext
              key={`activity-tasks-${act.id}`}
              items={act.tasks.map((t) => `task-${t.id}`)}
              strategy={horizontalListSortingStrategy}
            >
              <DroppableTaskZone
                activityId={act.id}
                className="flex"
                style={{ width: activityWidth, flexShrink: 0 }}
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
                <div className="flex-shrink-0 border-r border-gray-200 w-[280px]">
                  {addingTaskActivityId === act.id ? (
                    <div className={`p-3 min-h-[60px] ${ADD_FORM_TOKENS.surface}`}>
                      <Input
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
                        size="xs"
                        validation={taskDrafts[act.id]?.error ? 'error' : 'default'}
                        autoFocus
                      />
                      {taskDrafts[act.id]?.error && (
                        <p className={`text-[11px] mt-1 ${getSeverityToken('critical').textButton.split(' ')[0]}`}>{taskDrafts[act.id]?.error}</p>
                      )}
                      <div className="flex gap-2 mt-2">
                        <Button
                          variant="success"
                          size="xs"
                          onClick={() => onAddTask(act.id)}
                          loading={taskLoading.isCreating(act.id)}
                          className="flex-1"
                        >
                          Добавить
                        </Button>
                        <Button
                          variant="secondary"
                          size="xs"
                          onClick={stopAddingTask}
                          className="flex-1"
                        >
                          Отмена
                        </Button>
                      </div>
                    </div>
                  ) : (
                    <button
                      onClick={() => startAddingTask(act.id)}
                      className={`w-full h-[60px] rounded transition text-xs flex items-center justify-center ${ADD_PLACEHOLDER_TOKENS.button}`}
                      title="Добавить задачу"
                    >
                      + Задача
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
  const { setNodeRef, isOver, active } = useDroppable({
    id: `activity-tasks-${activityId}`,
    data: {
      type: 'activity-tasks',
      activityId,
    },
  });

  const showDropIndicator = isOver && active;
  const zoneClassName = `${className} transition-all duration-200 ${
    showDropIndicator ? 'bg-blue-100 ring-2 ring-blue-400 ring-inset rounded' : ''
  }`.trim();

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


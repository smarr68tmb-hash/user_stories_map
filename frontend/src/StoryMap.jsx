import { useState } from 'react';
import api, { activities, tasks } from './api';
import AIAssistant from './AIAssistant';
import EditStoryModal from './EditStoryModal';
import AnalysisPanel from './AnalysisPanel';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  useSortable,
  verticalListSortingStrategy,
  horizontalListSortingStrategy,
} from '@dnd-kit/sortable';
import { useDroppable } from '@dnd-kit/core';
import { CSS } from '@dnd-kit/utilities';

// Функция для обработки ошибок (упрощенная, так как api.js уже обрабатывает 401)
const handleApiError = (error, onUnauthorized) => {
  // api.js уже обработал 401 и попытался обновить токен
  // Если мы здесь, значит токен не удалось обновить или другая ошибка
  if (error.response?.status === 401) {
    if (onUnauthorized) {
      onUnauthorized();
    }
    return 'Сессия истекла. Пожалуйста, войдите снова.';
  }

  if (error.response?.data?.detail) {
    return error.response.data.detail;
  }

  if (error.response) {
    return `Ошибка сервера: ${error.response.status}`;
  }

  if (error.request) {
    return 'Не удалось подключиться к серверу';
  }

  return 'Произошла неизвестная ошибка';
};

// Вспомогательная функция для обновления истории в проекте (локально)
const updateStoryInProject = (project, storyId, updatedStory) => {
  return {
    ...project,
    activities: project.activities.map(activity => ({
      ...activity,
      tasks: activity.tasks.map(task => ({
        ...task,
        stories: task.stories.map(story =>
          story.id === storyId ? { ...story, ...updatedStory } : story
        )
      }))
    }))
  };
};

// Вспомогательная функция для добавления новой истории в проект (локально)
const addStoryToProject = (project, taskId, releaseId, newStory) => {
  return {
    ...project,
    activities: project.activities.map(activity => ({
      ...activity,
      tasks: activity.tasks.map(task => {
        if (task.id === taskId) {
          return {
            ...task,
            stories: [...task.stories, newStory]
          };
        }
        return task;
      })
    }))
  };
};

// Вспомогательная функция для удаления истории из проекта (локально)
const removeStoryFromProject = (project, storyId) => {
  return {
    ...project,
    activities: project.activities.map(activity => ({
      ...activity,
      tasks: activity.tasks.map(task => ({
        ...task,
        stories: task.stories.filter(story => story.id !== storyId)
      }))
    }))
  };
};

function StoryMap({ project, onUpdate, onUnauthorized }) {
  const [editingStory, setEditingStory] = useState(null);
  const [addingToCell, setAddingToCell] = useState(null);
  const [newStoryTitle, setNewStoryTitle] = useState('');
  const [newStoryDescription, setNewStoryDescription] = useState('');
  const [newStoryPriority, setNewStoryPriority] = useState('MVP');
  const [aiAssistantOpen, setAiAssistantOpen] = useState(false);
  const [aiAssistantStory, setAiAssistantStory] = useState(null);
  const [aiAssistantTaskId, setAiAssistantTaskId] = useState(null);
  const [aiAssistantReleaseId, setAiAssistantReleaseId] = useState(null);
  const [analysisPanelOpen, setAnalysisPanelOpen] = useState(false);
  
  // States for Activities and Tasks editing
  const [editingActivityId, setEditingActivityId] = useState(null);
  const [editingActivityTitle, setEditingActivityTitle] = useState('');
  const [addingActivity, setAddingActivity] = useState(false);
  const [newActivityTitle, setNewActivityTitle] = useState('');
  const [editingTaskId, setEditingTaskId] = useState(null);
  const [editingTaskTitle, setEditingTaskTitle] = useState('');
  const [addingTaskActivityId, setAddingTaskActivityId] = useState(null);
  const [newTaskTitle, setNewTaskTitle] = useState('');

  const sensors = useSensors(
    useSensor(PointerSensor, {
      activationConstraint: {
        distance: 3, // Минимальное расстояние для активации (уменьшено для быстрого отклика)
      },
    }),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const allTasks = project.activities.flatMap(act => 
    act.tasks.map(task => ({ ...task, activityTitle: act.title }))
  );

  const handleDragEnd = async (event) => {
    const { active, over } = event;
    
    if (!over || active.id === over.id) return;

    const activeId = String(active.id);
    const overId = String(over.id);

    // Проверяем, является ли это перетаскиванием Task (шага)
    if (activeId.startsWith('task-')) {
      const taskId = Number(activeId.replace('task-', ''));
      const activity = project.activities.find(a => a.tasks.some(t => t.id === taskId));
      
      if (!activity) return;

      // Если бросаем на другую задачу в той же активности
      if (overId.startsWith('task-')) {
        const targetTaskId = Number(overId.replace('task-', ''));
        const targetTask = activity.tasks.find(t => t.id === targetTaskId);
        
        if (targetTask && targetTask.id !== taskId) {
          await moveTask(taskId, targetTask.position);
        }
      }
      // Если бросаем на droppable зону активности
      else if (overId.startsWith('activity-tasks-')) {
        const activityId = Number(overId.replace('activity-tasks-', ''));
        if (activityId === activity.id) {
          // Перемещаем в конец списка
          const endPosition = Math.max(activity.tasks.length - 1, 0);
          await moveTask(taskId, endPosition);
        }
      }
      return;
    }

    // Оригинальная логика для Story (карточек)
    // Парсим ID активного элемента (карточки): storyId-taskId-releaseId
    const activeParts = activeId.split('-');
    const storyId = Number(activeParts[0]);
    const sourceTaskId = Number(activeParts[1]);
    const sourceReleaseId = Number(activeParts[2]);

    // Если бросаем на ячейку (cell-taskId-releaseId)
    if (overId.startsWith('cell-')) {
      const cellParts = overId.replace('cell-', '').split('-');
      const targetTaskId = Number(cellParts[0]);
      const targetReleaseId = Number(cellParts[1]);
      
      // Перемещаем в эту ячейку
      await moveStory(storyId, targetTaskId, targetReleaseId, 0);
      return;
    }

    // Если бросаем на другую карточку
    const overParts = overId.split('-');
    if (overParts.length === 3) {
      const targetStoryId = Number(overParts[0]);
      const targetTaskId = Number(overParts[1]);
      const targetReleaseId = Number(overParts[2]);

      if (targetStoryId !== storyId) {
        const targetStory = findStory(targetTaskId, targetReleaseId, targetStoryId);
        if (targetStory) {
          await moveStory(storyId, targetTaskId, targetReleaseId, targetStory.position);
        }
      }
    }
  };

  const findStory = (taskId, releaseId, storyId) => {
    const task = allTasks.find(t => t.id === taskId);
    if (!task) return null;
    return task.stories.find(s => s.id === storyId && s.release_id === releaseId);
  };

  const moveStory = async (storyId, taskId, releaseId, position) => {
    try {
      await api.patch(`/story/${storyId}/move`, {
        task_id: taskId,
        release_id: releaseId,
        position: position
      });
      // Обновляем проект
      const res = await api.get(`/project/${project.id}`);
      onUpdate(res.data);
    } catch (error) {
      console.error('Error moving story:', error);
      const errorMsg = handleApiError(error, onUnauthorized);
      alert(errorMsg);
    }
  };

  const handleAddStory = async (taskId, releaseId) => {
    if (!newStoryTitle.trim()) return;

    try {
      const response = await api.post('/story', {
        task_id: taskId,
        release_id: releaseId,
        title: newStoryTitle,
        description: newStoryDescription,
        priority: newStoryPriority
      });

      setNewStoryTitle('');
      setNewStoryDescription('');
      setNewStoryPriority('MVP');
      setAddingToCell(null);

      // Локальное обновление проекта (оптимизация)
      const updatedProject = addStoryToProject(project, taskId, releaseId, response.data);
      onUpdate(updatedProject);
    } catch (error) {
      console.error('Error adding story:', error);
      const errorMsg = handleApiError(error, onUnauthorized);
      alert(errorMsg);
    }
  };

  const handleUpdateStory = async (updates) => {
    if (!editingStory) return;

    try {
      const response = await api.put(`/story/${editingStory.id}`, updates);

      // Локальное обновление проекта (оптимизация)
      const updatedProject = updateStoryInProject(project, editingStory.id, response.data);
      onUpdate(updatedProject);
      setEditingStory(null);
    } catch (error) {
      console.error('Error updating story:', error);
      const errorMsg = handleApiError(error, onUnauthorized);
      alert(errorMsg);
      // При ошибке всё равно закрываем модал
      setEditingStory(null);
    }
  };

  const handleDeleteStory = async () => {
    if (!editingStory) return;

    try {
      await api.delete(`/story/${editingStory.id}`);

      // Локальное обновление проекта (оптимизация)
      const updatedProject = removeStoryFromProject(project, editingStory.id);
      onUpdate(updatedProject);
      setEditingStory(null);
    } catch (error) {
      console.error('Error deleting story:', error);
      const errorMsg = handleApiError(error, onUnauthorized);
      alert(errorMsg);
      // При ошибке всё равно закрываем модал
      setEditingStory(null);
    }
  };

  const handleOpenEditModal = (story) => {
    setEditingStory(story);
  };

  const handleOpenAIAssistant = (story, taskId, releaseId) => {
    setAiAssistantStory(story);
    setAiAssistantTaskId(taskId);
    setAiAssistantReleaseId(releaseId);
    setAiAssistantOpen(true);
  };

  const handleCloseAIAssistant = () => {
    setAiAssistantOpen(false);
    setAiAssistantStory(null);
    setAiAssistantTaskId(null);
    setAiAssistantReleaseId(null);
  };

  const handleStoryImproved = async () => {
    // Обновляем проект после улучшения истории
    try {
      const res = await api.get(`/project/${project.id}`);
      onUpdate(res.data);
    } catch (error) {
      console.error('Error refreshing project:', error);
    }
  };

  const handleStatusChange = async (storyId, newStatus) => {
    try {
      const response = await api.patch(`/story/${storyId}/status`, { status: newStatus });

      // Локальное обновление проекта (оптимизация)
      const updatedProject = updateStoryInProject(project, storyId, response.data);
      onUpdate(updatedProject);
    } catch (error) {
      console.error('Error updating status:', error);
      const errorMsg = handleApiError(error, onUnauthorized);
      alert(errorMsg);
    }
  };

  // Подсчет прогресса по релизу
  const calculateReleaseProgress = (releaseId) => {
    let total = 0;
    let done = 0;
    
    allTasks.forEach(task => {
      task.stories.forEach(story => {
        if (story.release_id === releaseId) {
          total++;
          if (story.status === 'done') done++;
        }
      });
    });
    
    return { total, done, percent: total > 0 ? Math.round((done / total) * 100) : 0 };
  };

  // ========== ACTIVITY HANDLERS ==========
  
  const handleAddActivity = async () => {
    if (!newActivityTitle.trim()) {
      setAddingActivity(false);
      setNewActivityTitle('');
      return;
    }

    try {
      await activities.create(project.id, newActivityTitle.trim());
      setNewActivityTitle('');
      setAddingActivity(false);
      
      // Обновляем проект
      const res = await api.get(`/project/${project.id}`);
      onUpdate(res.data);
    } catch (error) {
      console.error('Error adding activity:', error);
      const errorMsg = handleApiError(error, onUnauthorized);
      alert(errorMsg);
    }
  };

  const handleUpdateActivity = async (activityId) => {
    if (!editingActivityTitle.trim()) {
      setEditingActivityId(null);
      setEditingActivityTitle('');
      return;
    }

    try {
      await activities.update(activityId, editingActivityTitle.trim());
      setEditingActivityId(null);
      setEditingActivityTitle('');
      
      // Обновляем проект
      const res = await api.get(`/project/${project.id}`);
      onUpdate(res.data);
    } catch (error) {
      console.error('Error updating activity:', error);
      const errorMsg = handleApiError(error, onUnauthorized);
      alert(errorMsg);
      // Восстанавливаем оригинальное название
      const activity = project.activities.find(a => a.id === activityId);
      if (activity) {
        setEditingActivityTitle(activity.title);
      }
    }
  };

  const handleDeleteActivity = async (activityId) => {
    if (!confirm('Вы уверены, что хотите удалить эту активность? Все связанные задачи и истории будут удалены.')) {
      return;
    }

    try {
      await activities.delete(activityId);
      
      // Обновляем проект
      const res = await api.get(`/project/${project.id}`);
      onUpdate(res.data);
    } catch (error) {
      console.error('Error deleting activity:', error);
      const errorMsg = handleApiError(error, onUnauthorized);
      alert(errorMsg);
    }
  };

  const startEditingActivity = (activity) => {
    setEditingActivityId(activity.id);
    setEditingActivityTitle(activity.title);
  };

  // ========== TASK HANDLERS ==========
  
  const handleAddTask = async (activityId) => {
    const trimmedTitle = newTaskTitle.trim();
    
    // Валидация на frontend (дополнительно к backend)
    if (!trimmedTitle) {
      alert('Поле названия шага должно быть заполнено');
      setAddingTaskActivityId(null);
      setNewTaskTitle('');
      return;
    }

    try {
      await tasks.create(activityId, trimmedTitle);
      setNewTaskTitle('');
      setAddingTaskActivityId(null);
      
      // Обновляем проект
      const res = await api.get(`/project/${project.id}`);
      onUpdate(res.data);
    } catch (error) {
      console.error('Error adding task:', error);
      const errorMsg = handleApiError(error, onUnauthorized);
      // Показываем конкретное сообщение об ошибке
      if (error.response?.data?.detail) {
        alert(error.response.data.detail);
      } else {
        alert(errorMsg);
      }
    }
  };

  const handleUpdateTask = async (taskId) => {
    const trimmedTitle = editingTaskTitle.trim();
    
    // Валидация на frontend (дополнительно к backend)
    if (!trimmedTitle) {
      alert('Поле названия шага должно быть заполнено');
      setEditingTaskId(null);
      setEditingTaskTitle('');
      return;
    }

    try {
      await tasks.update(taskId, trimmedTitle);
      setEditingTaskId(null);
      setEditingTaskTitle('');
      
      // Обновляем проект
      const res = await api.get(`/project/${project.id}`);
      onUpdate(res.data);
    } catch (error) {
      console.error('Error updating task:', error);
      const errorMsg = handleApiError(error, onUnauthorized);
      // Показываем конкретное сообщение об ошибке
      if (error.response?.data?.detail) {
        alert(error.response.data.detail);
      } else {
        alert(errorMsg);
      }
      // Восстанавливаем оригинальное название
      const task = allTasks.find(t => t.id === taskId);
      if (task) {
        setEditingTaskTitle(task.title);
      }
    }
  };

  const handleDeleteTask = async (taskId) => {
    if (!confirm('Вы уверены, что хотите удалить эту задачу? Все связанные истории будут удалены.')) {
      return;
    }

    try {
      await tasks.delete(taskId);
      
      // Обновляем проект
      const res = await api.get(`/project/${project.id}`);
      onUpdate(res.data);
    } catch (error) {
      console.error('Error deleting task:', error);
      const errorMsg = handleApiError(error, onUnauthorized);
      alert(errorMsg);
    }
  };

  const startEditingTask = (task) => {
    setEditingTaskId(task.id);
    setEditingTaskTitle(task.title);
  };

  const moveTask = async (taskId, newPosition) => {
    try {
      await tasks.move(taskId, newPosition);
      // Обновляем проект
      const res = await api.get(`/project/${project.id}`);
      onUpdate(res.data);
    } catch (error) {
      console.error('Error moving task:', error);
      const errorMsg = handleApiError(error, onUnauthorized);
      alert(errorMsg);
      // Обновляем проект в случае ошибки, но защищаемся от повторного падения
      try {
        const res = await api.get(`/project/${project.id}`);
        onUpdate(res.data);
      } catch (refreshError) {
        console.error('Error refreshing project after move failure:', refreshError);
      }
    }
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
      {/* Analysis Button - Floating */}
      <div className="mb-4 flex justify-end">
        <button
          onClick={() => setAnalysisPanelOpen(true)}
          className="bg-gradient-to-r from-indigo-500 to-purple-500 text-white px-4 py-2 rounded-lg font-medium shadow-lg hover:from-indigo-600 hover:to-purple-600 transition flex items-center gap-2"
        >
          <span>📊</span>
          Анализ карты
        </button>
      </div>

      <div className="w-full overflow-x-auto">
        <div className="inline-block min-w-full bg-white rounded-lg shadow-sm border border-gray-200">
          {/* BACKBONE */}
          <div className="sticky top-0 z-10 bg-gray-50 border-b-2 border-gray-300">
          <div className="flex border-b border-gray-200">
            <div className="w-32 flex-shrink-0 bg-gray-100 border-r-2 border-gray-300 p-2 flex items-center justify-center">
              <span className="text-xs font-bold text-gray-600 uppercase">Releases</span>
            </div>
            {project.activities.map(act => {
              const taskCount = act.tasks.length;
              // Учитываем кнопку "+ Task" при расчете ширины Activity
              const activityWidth = (taskCount + 1) * 220; // +1 для кнопки "+ Task"
              const isEditing = editingActivityId === act.id;
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
                        onBlur={() => handleUpdateActivity(act.id)}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter') {
                            handleUpdateActivity(act.id);
                          } else if (e.key === 'Escape') {
                            setEditingActivityId(null);
                            setEditingActivityTitle('');
                          }
                        }}
                        className="flex-1 px-2 py-1 text-sm border rounded bg-white text-gray-800"
                        autoFocus
                      />
                    </div>
                  ) : (
                    <>
                      <span 
                        className="text-sm cursor-pointer hover:underline"
                        onDoubleClick={() => startEditingActivity(act)}
                        title="Двойной клик для редактирования"
                      >
                        {act.title}
                      </span>
                      <div className="absolute top-1 right-1 opacity-0 group-hover:opacity-100 transition-opacity flex gap-1">
                        <button
                          onClick={() => startEditingActivity(act)}
                          className="p-1 text-blue-600 hover:text-blue-800 hover:bg-blue-200 rounded"
                          title="Редактировать"
                        >
                          ✏️
                        </button>
                        <button
                          onClick={() => handleDeleteActivity(act.id)}
                          className="p-1 text-red-600 hover:text-red-800 hover:bg-red-200 rounded"
                          title="Удалить"
                        >
                          🗑️
                        </button>
                      </div>
                    </>
                  )}
                </div>
              );
            })}
            {/* Кнопка добавления Activity */}
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
                        handleAddActivity();
                      } else if (e.key === 'Escape') {
                        setAddingActivity(false);
                        setNewActivityTitle('');
                      }
                    }}
                    className="w-full px-2 py-1 text-sm border rounded"
                    autoFocus
                  />
                  <div className="flex gap-2 mt-2">
                    <button
                      onClick={handleAddActivity}
                      className="flex-1 bg-green-600 text-white text-xs py-1 px-2 rounded hover:bg-green-700"
                    >
                      Добавить
                    </button>
                    <button
                      onClick={() => {
                        setAddingActivity(false);
                        setNewActivityTitle('');
                      }}
                      className="flex-1 bg-gray-300 text-gray-700 text-xs py-1 px-2 rounded hover:bg-gray-400"
                    >
                      Отмена
                    </button>
                  </div>
                </div>
              ) : (
                <button
                  onClick={() => setAddingActivity(true)}
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
            {project.activities.map(act => {
              // Ширина контейнера Tasks должна совпадать с шириной Activity
              const taskCount = act.tasks.length;
              const activityWidth = (taskCount + 1) * 220; // +1 для кнопки "+ Task"
              return (
                <SortableContext
                  key={`activity-tasks-${act.id}`}
                  items={act.tasks.map(t => `task-${t.id}`)}
                  strategy={horizontalListSortingStrategy}
                >
                  <DroppableTaskZone
                    activityId={act.id}
                    className="flex"
                    style={{ width: `${activityWidth}px`, flexShrink: 0 }}
                    id={`activity-tasks-${act.id}`}
                  >
                    {act.tasks.map(task => {
                      const isEditing = editingTaskId === task.id;
                      return (
                        <SortableTask
                          key={task.id}
                          task={task}
                          isEditing={isEditing}
                          editingTaskTitle={editingTaskTitle}
                          setEditingTaskTitle={setEditingTaskTitle}
                          onUpdateTask={handleUpdateTask}
                          onStartEditing={startEditingTask}
                          onDelete={handleDeleteTask}
                          setEditingTaskId={setEditingTaskId}
                        />
                      );
                    })}
                    {/* Кнопка добавления Task для каждой Activity */}
                    <div className="flex-shrink-0 border-r border-gray-200 w-[220px]">
                      {addingTaskActivityId === act.id ? (
                        <div className="p-3 bg-green-50 border border-green-300 min-h-[60px]">
                          <input
                            type="text"
                            placeholder="Название задачи"
                            value={newTaskTitle}
                            onChange={(e) => setNewTaskTitle(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === 'Enter') {
                                handleAddTask(act.id);
                              } else if (e.key === 'Escape') {
                                setAddingTaskActivityId(null);
                                setNewTaskTitle('');
                              }
                            }}
                            className="w-full px-2 py-1 text-xs border rounded"
                            autoFocus
                          />
                          <div className="flex gap-2 mt-2">
                            <button
                              onClick={() => handleAddTask(act.id)}
                              className="flex-1 bg-green-600 text-white text-xs py-1 px-2 rounded hover:bg-green-700"
                            >
                              Добавить
                            </button>
                            <button
                              onClick={() => {
                                setAddingTaskActivityId(null);
                                setNewTaskTitle('');
                              }}
                              className="flex-1 bg-gray-300 text-gray-700 text-xs py-1 px-2 rounded hover:bg-gray-400"
                            >
                              Отмена
                            </button>
                          </div>
                        </div>
                      ) : (
                        <button
                          onClick={() => setAddingTaskActivityId(act.id)}
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

        {/* BODY */}
        <div>
          {project.releases.map(release => {
            const progress = calculateReleaseProgress(release.id);
            return (
            <div key={release.id} className="flex border-b border-gray-200 min-h-[180px] hover:bg-gray-50 transition">
              <div className="w-32 flex-shrink-0 bg-gray-100 p-3 font-bold flex flex-col items-center justify-center text-gray-700 border-r-2 border-gray-300 gap-2">
                <span className="text-sm text-center">{release.title}</span>
                {/* Progress bar */}
                {progress.total > 0 && (
                  <div className="w-full px-1">
                    <div className="w-full bg-gray-200 rounded-full h-1.5 overflow-hidden">
                      <div 
                        className={`h-full rounded-full transition-all duration-500 ${
                          progress.percent === 100 ? 'bg-green-500' : 'bg-blue-500'
                        }`}
                        style={{ width: `${progress.percent}%` }}
                      />
                    </div>
                    <div className="text-[10px] text-gray-500 text-center mt-1">
                      {progress.done}/{progress.total}
                    </div>
                  </div>
                )}
              </div>

              {project.activities.map(act => {
                const taskCount = act.tasks.length;
                const activityWidth = (taskCount + 1) * 220; // +1 для кнопки "+ Task"
                return (
                  <div 
                    key={`activity-body-${act.id}`}
                    className="flex"
                    style={{ width: `${activityWidth}px`, flexShrink: 0 }}
                  >
                    {act.tasks.map(task => {
                      const storiesInCell = task.stories.filter(s => s.release_id === release.id);
                      const cellId = `cell-${task.id}-${release.id}`;
                      const isAdding = addingToCell === cellId;

                      return (
                        <DroppableCell
                          key={`${task.id}-${release.id}`}
                          cellId={cellId}
                          taskId={task.id}
                          releaseId={release.id}
                        >
                          <SortableContext 
                            items={storiesInCell.map(s => `${s.id}-${task.id}-${release.id}`)}
                            strategy={verticalListSortingStrategy}
                          >
                            <div className="flex flex-col gap-2 min-h-[150px]">
                              {storiesInCell.map(story => (
                                <StoryCard
                                  key={story.id}
                                  story={story}
                                  taskId={task.id}
                                  releaseId={release.id}
                                  onEdit={() => handleOpenEditModal(story)}
                                  onOpenAI={() => handleOpenAIAssistant(story, task.id, release.id)}
                                  onStatusChange={handleStatusChange}
                                />
                              ))}
                              
                              {isAdding ? (
                                <div className="bg-green-50 p-3 rounded border border-green-300">
                                  <input
                                    type="text"
                                    placeholder="Название истории"
                                    value={newStoryTitle}
                                    onChange={(e) => setNewStoryTitle(e.target.value)}
                                    className="w-full mb-2 p-2 text-sm border rounded"
                                    autoFocus
                                  />
                                  <textarea
                                    placeholder="Описание (опционально)"
                                    value={newStoryDescription}
                                    onChange={(e) => setNewStoryDescription(e.target.value)}
                                    className="w-full mb-2 p-2 text-xs border rounded resize-none"
                                    rows="2"
                                  />
                                  <select
                                    value={newStoryPriority}
                                    onChange={(e) => setNewStoryPriority(e.target.value)}
                                    className="w-full mb-2 p-1 text-xs border rounded"
                                  >
                                    <option value="MVP">MVP</option>
                                    <option value="Release 1">Release 1</option>
                                    <option value="Later">Later</option>
                                  </select>
                                  <div className="flex gap-2">
                                    <button
                                      onClick={() => handleAddStory(task.id, release.id)}
                                      className="flex-1 bg-green-600 text-white text-xs py-1 px-2 rounded hover:bg-green-700"
                                    >
                                      Добавить
                                    </button>
                                    <button
                                      onClick={() => {
                                        setAddingToCell(null);
                                        setNewStoryTitle('');
                                        setNewStoryDescription('');
                                      }}
                                      className="flex-1 bg-gray-300 text-gray-700 text-xs py-1 px-2 rounded hover:bg-gray-400"
                                    >
                                      Отмена
                                    </button>
                                  </div>
                                </div>
                              ) : (
                                <button
                                  onClick={() => setAddingToCell(cellId)}
                                  className="text-xs text-gray-400 hover:text-gray-600 py-2 border-2 border-dashed border-gray-300 rounded hover:border-gray-400 transition"
                                >
                                  + Добавить карточку
                                </button>
                              )}
                            </div>
                          </SortableContext>
                        </DroppableCell>
                      );
                    })}
                    {/* Пустая ячейка для выравнивания с кнопкой "+ Task" */}
                    <div className="w-[220px] flex-shrink-0 border-r border-gray-200"></div>
                  </div>
                );
              })}
            </div>
          );
          })}
        </div>
        </div>
      </div>

      {/* Edit Story Modal */}
      <EditStoryModal
        story={editingStory}
        releases={project.releases}
        isOpen={!!editingStory}
        onClose={() => setEditingStory(null)}
        onSave={handleUpdateStory}
        onDelete={handleDeleteStory}
      />

      {/* AI Assistant Modal */}
      {aiAssistantOpen && aiAssistantStory && (
        <AIAssistant
          story={aiAssistantStory}
          taskId={aiAssistantTaskId}
          releaseId={aiAssistantReleaseId}
          isOpen={aiAssistantOpen}
          onClose={handleCloseAIAssistant}
          onStoryImproved={handleStoryImproved}
        />
      )}

      {/* Analysis Panel Modal */}
      <AnalysisPanel
        projectId={project.id}
        isOpen={analysisPanelOpen}
        onClose={() => setAnalysisPanelOpen(false)}
      />
    </DndContext>
  );
}

// Компонент для droppable зоны задач активности
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

// Компонент для droppable ячейки
function DroppableCell({ cellId, taskId, releaseId, children }) {
  const { setNodeRef, isOver } = useDroppable({
    id: cellId,
    data: {
      type: 'cell',
      taskId,
      releaseId,
    },
  });

  return (
    <div
      ref={setNodeRef}
      className={`w-[220px] flex-shrink-0 p-2 border-r border-dashed border-gray-300 transition-colors ${
        isOver ? 'bg-blue-50 border-blue-400' : 'bg-white'
      }`}
    >
      {children}
    </div>
  );
}

// Компонент для sortable Task (шага)
function SortableTask({ 
  task, 
  isEditing, 
  editingTaskTitle, 
  setEditingTaskTitle, 
  onUpdateTask, 
  onStartEditing, 
  onDelete,
  setEditingTaskId 
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
    opacity: isDragging ? 0.5 : 1,
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
          />
        </div>
      ) : (
        <>
          {/* Drag Handle */}
          <div
            {...attributes}
            {...listeners}
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
              className="p-1 text-blue-600 hover:text-blue-800 hover:bg-blue-200 rounded text-xs"
              title="Редактировать"
            >
              ✏️
            </button>
            <button
              onClick={() => onDelete(task.id)}
              className="p-1 text-red-600 hover:text-red-800 hover:bg-red-200 rounded text-xs"
              title="Удалить"
            >
              🗑️
            </button>
          </div>
        </>
      )}
    </div>
  );
}

function StoryCard({ story, taskId, releaseId, onEdit, onOpenAI, onStatusChange }) {
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
    opacity: isDragging ? 0.5 : 1,
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
        {...attributes}
        {...listeners}
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
          className={`flex-shrink-0 w-5 h-5 rounded-full border-2 flex items-center justify-center text-xs font-bold transition-all hover:scale-110 ${
            currentStatus === 'done' 
              ? 'bg-green-500 border-green-500 text-white' 
              : currentStatus === 'in_progress'
              ? 'bg-blue-500 border-blue-500 text-white'
              : 'bg-white border-gray-300 text-gray-400 hover:border-gray-400'
          }`}
          title={currentStatus === 'todo' ? 'Начать' : currentStatus === 'in_progress' ? 'Завершить' : 'Вернуть в работу'}
        >
          {statusIcons[currentStatus]}
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

export default StoryMap;


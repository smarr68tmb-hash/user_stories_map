import { useState } from 'react';
import api from './api';
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

    // Парсим ID активного элемента (карточки): storyId-taskId-releaseId
    const activeParts = String(active.id).split('-');
    const storyId = Number(activeParts[0]);
    const sourceTaskId = Number(activeParts[1]);
    const sourceReleaseId = Number(activeParts[2]);

    // Проверяем куда бросаем
    const overId = String(over.id);
    
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
      await api.post('/story', {
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
      
      // Обновляем проект
      const res = await api.get(`/project/${project.id}`);
      onUpdate(res.data);
    } catch (error) {
      console.error('Error adding story:', error);
      const errorMsg = handleApiError(error, onUnauthorized);
      alert(errorMsg);
    }
  };

  const handleUpdateStory = async (updates) => {
    if (!editingStory) return;
    
    await api.put(`/story/${editingStory.id}`, updates);
    
    // Обновляем проект
    const res = await api.get(`/project/${project.id}`);
    onUpdate(res.data);
    setEditingStory(null);
  };

  const handleDeleteStory = async () => {
    if (!editingStory) return;

    await api.delete(`/story/${editingStory.id}`);
    
    // Обновляем проект
    const res = await api.get(`/project/${project.id}`);
    onUpdate(res.data);
    setEditingStory(null);
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

      <div className="inline-block min-w-full bg-white rounded-lg shadow-sm border border-gray-200">
        {/* BACKBONE */}
        <div className="sticky top-0 z-10 bg-gray-50 border-b-2 border-gray-300">
          <div className="flex border-b border-gray-200">
            <div className="w-32 flex-shrink-0 bg-gray-100 border-r-2 border-gray-300 p-2 flex items-center justify-center">
              <span className="text-xs font-bold text-gray-600 uppercase">Releases</span>
            </div>
            {project.activities.map(act => {
              const taskCount = act.tasks.length;
              return (
                <div 
                  key={act.id} 
                  className="bg-blue-100 border-r border-gray-200 p-3 text-center font-bold text-blue-800 flex items-center justify-center"
                  style={{ width: `${taskCount * 220}px`, minWidth: '220px' }}
                >
                  <span className="text-sm">{act.title}</span>
                </div>
              );
            })}
          </div>

          <div className="flex">
            <div className="w-32 flex-shrink-0 bg-gray-100 border-r-2 border-gray-300"></div>
            {allTasks.map(task => (
              <div 
                key={task.id} 
                className="w-[220px] flex-shrink-0 bg-blue-50 border-r border-gray-200 p-3 text-sm font-semibold text-center text-gray-700 min-h-[60px] flex items-center justify-center"
              >
                <span className="leading-tight">{task.title}</span>
              </div>
            ))}
          </div>
        </div>

        {/* BODY */}
        <div>
          {project.releases.map(release => (
            <div key={release.id} className="flex border-b border-gray-200 min-h-[180px] hover:bg-gray-50 transition">
              <div className="w-32 flex-shrink-0 bg-gray-100 p-3 font-bold flex items-center justify-center text-gray-700 border-r-2 border-gray-300">
                <span className="text-sm text-center">{release.title}</span>
              </div>

              {allTasks.map(task => {
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
            </div>
          ))}
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

function StoryCard({ story, taskId, releaseId, onEdit, onOpenAI }) {
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

  return (
    <div
      ref={setNodeRef}
      style={style}
      className="bg-yellow-100 p-3 rounded-lg shadow-sm hover:shadow-md transition-all text-sm border border-yellow-300 group relative cursor-pointer"
      onClick={onEdit}
    >
      {/* Drag Handle */}
      <div
        {...attributes}
        {...listeners}
        onClick={(e) => e.stopPropagation()}
        className="absolute top-2 right-2 cursor-grab active:cursor-grabbing p-1.5 hover:bg-yellow-200 rounded-md opacity-40 hover:opacity-100 transition z-10"
        title="Перетащить"
      >
        <svg xmlns="http://www.w3.org/2000/svg" className="h-3.5 w-3.5 text-gray-500" viewBox="0 0 20 20" fill="currentColor">
          <path d="M7 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 2zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 7 14zm6-8a2 2 0 1 0-.001-4.001A2 2 0 0 0 13 6zm0 2a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 8zm0 6a2 2 0 1 0 .001 4.001A2 2 0 0 0 13 14z" />
        </svg>
      </div>

      {/* Title */}
      <div className="font-medium text-gray-800 pr-7 leading-snug mb-1.5 line-clamp-2">
        {story.title}
      </div>

      {/* Description */}
      {story.description && (
        <div className="text-xs text-gray-600 line-clamp-2 mb-2">{story.description}</div>
      )}

      {/* Footer: Priority + AC count */}
      <div className="flex items-center gap-2 mt-auto pt-1">
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


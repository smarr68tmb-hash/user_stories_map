import { useState } from 'react';
import axios from 'axios';
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
import { CSS } from '@dnd-kit/utilities';

// Настройка axios для автоматического добавления токена
const getAuthHeaders = () => {
  const token = localStorage.getItem('auth_token');
  return token ? { Authorization: `Bearer ${token}` } : {};
};

const API_URL = "http://127.0.0.1:8000";

// Функция для обработки ошибок с проверкой 401
const handleApiError = (error, onUnauthorized) => {
  if (error.response?.status === 401) {
    // Токен истек или невалиден
    localStorage.removeItem('auth_token');
    if (onUnauthorized) {
      onUnauthorized();
    } else {
      window.location.reload();
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

  const sensors = useSensors(
    useSensor(PointerSensor),
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

    const [storyId, sourceTaskId, sourceReleaseId] = active.id.split('-').map(Number);
    const [targetStoryId, targetTaskId, targetReleaseId] = over.id.split('-').map(Number);

    // Если перетаскиваем на другую карточку, перемещаем в ту же ячейку
    if (targetStoryId && targetStoryId !== storyId) {
      const targetStory = findStory(targetTaskId, targetReleaseId, targetStoryId);
      if (targetStory) {
        await moveStory(storyId, targetTaskId, targetReleaseId, targetStory.position);
      }
      return;
    }

    // Если перетаскиваем в ячейку
    if (!targetStoryId && targetTaskId && targetReleaseId !== undefined) {
      await moveStory(storyId, targetTaskId, targetReleaseId, 0);
    }
  };

  const findStory = (taskId, releaseId, storyId) => {
    const task = allTasks.find(t => t.id === taskId);
    if (!task) return null;
    return task.stories.find(s => s.id === storyId && s.release_id === releaseId);
  };

  const moveStory = async (storyId, taskId, releaseId, position) => {
    try {
      await axios.patch(`${API_URL}/story/${storyId}/move`, {
        task_id: taskId,
        release_id: releaseId,
        position: position
      }, { headers: getAuthHeaders() });
      // Обновляем проект
      const res = await axios.get(`${API_URL}/project/${project.id}`, { headers: getAuthHeaders() });
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
      await axios.post(`${API_URL}/story`, {
        task_id: taskId,
        release_id: releaseId,
        title: newStoryTitle,
        description: newStoryDescription,
        priority: newStoryPriority
      }, { headers: getAuthHeaders() });
      
      setNewStoryTitle('');
      setNewStoryDescription('');
      setNewStoryPriority('MVP');
      setAddingToCell(null);
      
      // Обновляем проект
      const res = await axios.get(`${API_URL}/project/${project.id}`, { headers: getAuthHeaders() });
      onUpdate(res.data);
    } catch (error) {
      console.error('Error adding story:', error);
      const errorMsg = handleApiError(error, onUnauthorized);
      alert(errorMsg);
    }
  };

  const handleUpdateStory = async (storyId, updates) => {
    try {
      await axios.put(`${API_URL}/story/${storyId}`, updates, { headers: getAuthHeaders() });
      
      setEditingStory(null);
      
      // Обновляем проект
      const res = await axios.get(`${API_URL}/project/${project.id}`, { headers: getAuthHeaders() });
      onUpdate(res.data);
    } catch (error) {
      console.error('Error updating story:', error);
      const errorMsg = handleApiError(error, onUnauthorized);
      alert(errorMsg);
    }
  };

  const handleDeleteStory = async (storyId) => {
    if (!confirm('Удалить эту карточку?')) return;

    try {
      await axios.delete(`${API_URL}/story/${storyId}`, { headers: getAuthHeaders() });
      
      // Обновляем проект
      const res = await axios.get(`${API_URL}/project/${project.id}`, { headers: getAuthHeaders() });
      onUpdate(res.data);
    } catch (error) {
      console.error('Error deleting story:', error);
      const errorMsg = handleApiError(error, onUnauthorized);
      alert(errorMsg);
    }
  };

  return (
    <DndContext
      sensors={sensors}
      collisionDetection={closestCenter}
      onDragEnd={handleDragEnd}
    >
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
                  <div 
                    key={`${task.id}-${release.id}`} 
                    className="w-[220px] flex-shrink-0 p-2 border-r border-dashed border-gray-300 bg-white"
                    id={cellId}
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
                            isEditing={editingStory === story.id}
                            onEdit={() => setEditingStory(story.id)}
                            onSave={(updates) => handleUpdateStory(story.id, updates)}
                            onCancel={() => setEditingStory(null)}
                            onDelete={() => handleDeleteStory(story.id)}
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
                  </div>
                );
              })}
            </div>
          ))}
        </div>
      </div>
    </DndContext>
  );
}

function StoryCard({ story, taskId, releaseId, isEditing, onEdit, onSave, onCancel, onDelete }) {
  const [editTitle, setEditTitle] = useState(story.title);
  const [editDescription, setEditDescription] = useState(story.description || '');
  const [editPriority, setEditPriority] = useState(story.priority || 'MVP');
  const [editAC, setEditAC] = useState((story.acceptance_criteria || []).join('\n'));

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

  if (isEditing) {
    return (
      <div className="bg-blue-50 p-3 rounded shadow-sm border border-blue-300">
        <input
          type="text"
          value={editTitle}
          onChange={(e) => setEditTitle(e.target.value)}
          className="w-full mb-2 p-2 text-sm border rounded font-medium"
          autoFocus
        />
        <textarea
          value={editDescription}
          onChange={(e) => setEditDescription(e.target.value)}
          className="w-full mb-2 p-2 text-xs border rounded resize-none"
          rows="2"
          placeholder="Описание"
        />
        <select
          value={editPriority}
          onChange={(e) => setEditPriority(e.target.value)}
          className="w-full mb-2 p-1 text-xs border rounded"
        >
          <option value="MVP">MVP</option>
          <option value="Release 1">Release 1</option>
          <option value="Later">Later</option>
        </select>
        <textarea
          value={editAC}
          onChange={(e) => setEditAC(e.target.value)}
          className="w-full mb-2 p-1 text-xs border rounded resize-none"
          rows="2"
          placeholder="Acceptance Criteria (каждая строка - отдельный критерий)"
        />
        <div className="flex gap-2">
          <button
            onClick={() => onSave({
              title: editTitle,
              description: editDescription,
              priority: editPriority,
              acceptance_criteria: editAC.split('\n').filter(l => l.trim())
            })}
            className="flex-1 bg-blue-600 text-white text-xs py-1 px-2 rounded hover:bg-blue-700"
          >
            Сохранить
          </button>
          <button
            onClick={onCancel}
            className="flex-1 bg-gray-300 text-gray-700 text-xs py-1 px-2 rounded hover:bg-gray-400"
          >
            Отмена
          </button>
          <button
            onClick={onDelete}
            className="bg-red-500 text-white text-xs py-1 px-2 rounded hover:bg-red-600"
          >
            Удалить
          </button>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="bg-yellow-200 p-3 rounded shadow-sm hover:shadow-md transition cursor-move text-sm border border-yellow-300 group"
    >
      <div className="font-medium mb-1 text-gray-800">{story.title}</div>
      {story.description && (
        <div className="text-xs text-gray-600 line-clamp-2 mb-2">{story.description}</div>
      )}
      <div className="flex items-center justify-between mt-2">
        {story.priority && (
          <span className="text-[10px] uppercase px-2 py-0.5 bg-white/70 rounded font-semibold text-gray-700">
            {story.priority}
          </span>
        )}
        {story.acceptance_criteria && story.acceptance_criteria.length > 0 && (
          <span className="text-[10px] text-gray-500">
            {story.acceptance_criteria.length} AC
          </span>
        )}
      </div>
      <div className="hidden group-hover:flex gap-1 mt-2">
        <button
          onClick={(e) => {
            e.stopPropagation();
            onEdit();
          }}
          className="text-[10px] bg-blue-500 text-white px-2 py-1 rounded hover:bg-blue-600"
        >
          Редактировать
        </button>
      </div>
      {story.acceptance_criteria && story.acceptance_criteria.length > 0 && (
        <div className="hidden group-hover:block mt-2 pt-2 border-t border-yellow-300">
          <div className="text-[10px] font-semibold text-gray-700 mb-1">Acceptance Criteria:</div>
          <ul className="text-[10px] text-gray-600 space-y-1">
            {story.acceptance_criteria.slice(0, 3).map((ac, idx) => (
              <li key={idx} className="flex items-start">
                <span className="mr-1">•</span>
                <span>{ac}</span>
              </li>
            ))}
            {story.acceptance_criteria.length > 3 && (
              <li className="text-gray-500">+{story.acceptance_criteria.length - 3} more</li>
            )}
          </ul>
        </div>
      )}
    </div>
  );
}

export default StoryMap;


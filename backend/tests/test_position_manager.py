"""
Тесты для PositionManager - управление позициями элементов

Покрытие:
1. ✅ Получение максимальной позиции
2. ✅ Сдвиг позиций вправо
3. ✅ Сдвиг позиций влево
4. ✅ Нормализация позиций
5. ✅ Перемещение элементов
"""
import pytest

from models import Activity, UserTask
from utils import PositionManager


# ============================================================================
# Test Position Manager for Activities
# ============================================================================

class TestPositionManagerActivities:
    """Тесты для управления позициями активностей"""
    
    def test_get_max_position(self, db_session, test_project):
        """Проверка получения максимальной позиции"""
        # Создаем активности
        for i in range(3):
            activity = Activity(project_id=test_project.id, title=f"Activity {i}", position=i)
            db_session.add(activity)
        db_session.commit()
        
        manager = PositionManager(
            db=db_session,
            model_class=Activity,
            position_column=Activity.position,
            parent_column=Activity.project_id
        )
        
        max_pos = manager.get_max_position(test_project.id)
        assert max_pos == 3
    
    def test_get_max_position_empty(self, db_session, test_project):
        """Проверка максимальной позиции для пустого списка"""
        manager = PositionManager(
            db=db_session,
            model_class=Activity,
            position_column=Activity.position,
            parent_column=Activity.project_id
        )
        
        max_pos = manager.get_max_position(test_project.id)
        assert max_pos == 0
    
    def test_shift_positions_right(self, db_session, test_project):
        """Проверка сдвига позиций вправо"""
        # Создаем активности
        activities = []
        for i in range(3):
            activity = Activity(project_id=test_project.id, title=f"Activity {i}", position=i)
            db_session.add(activity)
            activities.append(activity)
        db_session.commit()
        
        manager = PositionManager(
            db=db_session,
            model_class=Activity,
            position_column=Activity.position,
            parent_column=Activity.project_id
        )
        
        # Сдвигаем с позиции 1
        manager.shift_positions_right(test_project.id, from_position=1)
        db_session.commit()
        
        # Проверяем позиции
        db_session.refresh(activities[0])
        db_session.refresh(activities[1])
        db_session.refresh(activities[2])
        
        assert activities[0].position == 0  # Не изменилась
        assert activities[1].position == 2  # Сдвинулась вправо
        assert activities[2].position == 3  # Сдвинулась вправо
    
    def test_shift_positions_left(self, db_session, test_project):
        """Проверка сдвига позиций влево"""
        # Создаем активности
        activities = []
        for i in range(3):
            activity = Activity(project_id=test_project.id, title=f"Activity {i}", position=i)
            db_session.add(activity)
            activities.append(activity)
        db_session.commit()
        
        manager = PositionManager(
            db=db_session,
            model_class=Activity,
            position_column=Activity.position,
            parent_column=Activity.project_id
        )
        
        # Сдвигаем влево с позиции 1
        manager.shift_positions_left(test_project.id, from_position=1)
        db_session.commit()
        
        # Проверяем позиции
        db_session.refresh(activities[0])
        db_session.refresh(activities[1])
        db_session.refresh(activities[2])
        
        assert activities[0].position == 0  # Не изменилась
        assert activities[1].position == 0  # Сдвинулась влево
        assert activities[2].position == 1  # Сдвинулась влево
    
    def test_normalize_position(self, db_session, test_project):
        """Проверка нормализации позиций"""
        # Создаем активности
        for i in range(3):
            activity = Activity(project_id=test_project.id, title=f"Activity {i}", position=i)
            db_session.add(activity)
        db_session.commit()
        
        manager = PositionManager(
            db=db_session,
            model_class=Activity,
            position_column=Activity.position,
            parent_column=Activity.project_id
        )
        
        # Нормализуем позиции
        assert manager.normalize_position(test_project.id, -1) == 0  # Ниже минимума
        assert manager.normalize_position(test_project.id, 0) == 0  # Валидная
        assert manager.normalize_position(test_project.id, 2) == 2  # Валидная
        assert manager.normalize_position(test_project.id, 5) == 2  # Выше максимума (max = 2)
    
    def test_move_item(self, db_session, test_project):
        """Проверка перемещения элемента"""
        # Создаем активности
        activities = []
        for i in range(4):
            activity = Activity(project_id=test_project.id, title=f"Activity {i}", position=i)
            db_session.add(activity)
            activities.append(activity)
        db_session.commit()
        
        manager = PositionManager(
            db=db_session,
            model_class=Activity,
            position_column=Activity.position,
            parent_column=Activity.project_id
        )
        
        # Перемещаем элемент с позиции 1 на позицию 3
        manager.move_item(activities[1].id, test_project.id, old_position=1, new_position=3)
        db_session.commit()
        
        # Проверяем позиции
        for activity in activities:
            db_session.refresh(activity)
        
        assert activities[0].position == 0  # Не изменилась
        assert activities[1].position == 3  # Перемещена
        assert activities[2].position == 1  # Сдвинулась влево
        assert activities[3].position == 2  # Сдвинулась влево


# ============================================================================
# Test Position Manager for Tasks
# ============================================================================

class TestPositionManagerTasks:
    """Тесты для управления позициями задач"""
    
    def test_move_task(self, db_session, test_project):
        """Проверка перемещения задачи"""
        from models import Activity
        
        activity = Activity(project_id=test_project.id, title="Test Activity", position=0)
        db_session.add(activity)
        db_session.commit()
        
        # Создаем задачи
        tasks = []
        for i in range(3):
            task = UserTask(activity_id=activity.id, title=f"Task {i}", position=i)
            db_session.add(task)
            tasks.append(task)
        db_session.commit()
        
        manager = PositionManager(
            db=db_session,
            model_class=UserTask,
            position_column=UserTask.position,
            parent_column=UserTask.activity_id
        )
        
        # Перемещаем задачу с позиции 0 на позицию 2
        manager.move_item(tasks[0].id, activity.id, old_position=0, new_position=2)
        db_session.commit()
        
        # Проверяем позиции
        for task in tasks:
            db_session.refresh(task)
        
        assert tasks[0].position == 2  # Перемещена
        assert tasks[1].position == 0  # Сдвинулась влево
        assert tasks[2].position == 1  # Сдвинулась влево


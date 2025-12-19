"""
Position Manager - управление позициями элементов

Упрощает работу с позициями при создании, обновлении и удалении элементов,
аналогично организации тестов в классы.
"""
from typing import TypeVar, Generic
from sqlalchemy.orm import Session
from sqlalchemy import Column

T = TypeVar('T')


class PositionManager:
    """
    Класс для управления позициями элементов в списках.
    
    Аналогично TestHelperFunctions в тестах - группирует связанные функции.
    """
    
    def __init__(self, db: Session, model_class: type, position_column: Column, parent_column: Column):
        """
        Args:
            db: Database session
            model_class: Класс модели (Activity, UserTask, UserStory и т.д.)
            position_column: Колонка с позицией (Activity.position, UserTask.position)
            parent_column: Колонка родителя (Activity.project_id, UserTask.activity_id)
        """
        self.db = db
        self.model_class = model_class
        self.position_column = position_column
        self.parent_column = parent_column
    
    def get_max_position(self, parent_id: int) -> int:
        """
        Возвращает максимальную позицию для родителя.
        
        Args:
            parent_id: ID родителя
            
        Returns:
            int: Максимальная позиция (или 0 если элементов нет)
        """
        max_pos = (
            self.db.query(self.position_column)
            .filter(self.parent_column == parent_id)
            .order_by(self.position_column.desc())
            .first()
        )
        return (max_pos[0] + 1) if max_pos else 0
    
    def shift_positions_right(self, parent_id: int, from_position: int, exclude_id: int = None) -> None:
        """
        Сдвигает позиции вправо (увеличивает) начиная с from_position.
        
        Args:
            parent_id: ID родителя
            from_position: Позиция, с которой начинать сдвиг
            exclude_id: ID элемента, который нужно исключить из сдвига
        """
        query = (
            self.db.query(self.model_class)
            .filter(self.parent_column == parent_id)
            .filter(self.position_column >= from_position)
        )
        
        if exclude_id:
            query = query.filter(self.model_class.id != exclude_id)
        
        items = query.all()
        for item in items:
            setattr(item, self.position_column.name, getattr(item, self.position_column.name) + 1)
    
    def shift_positions_left(self, parent_id: int, from_position: int, exclude_id: int = None) -> None:
        """
        Сдвигает позиции влево (уменьшает) начиная с from_position.
        
        Args:
            parent_id: ID родителя
            from_position: Позиция, с которой начинать сдвиг
            exclude_id: ID элемента, который нужно исключить из сдвига
        """
        query = (
            self.db.query(self.model_class)
            .filter(self.parent_column == parent_id)
            .filter(self.position_column > from_position)
        )
        
        if exclude_id:
            query = query.filter(self.model_class.id != exclude_id)
        
        items = query.all()
        for item in items:
            current_pos = getattr(item, self.position_column.name)
            if current_pos > 0:
                setattr(item, self.position_column.name, current_pos - 1)
    
    def normalize_position(self, parent_id: int, position: int) -> int:
        """
        Нормализует позицию в допустимый диапазон [0, max_position].
        
        Args:
            parent_id: ID родителя
            position: Желаемая позиция
            
        Returns:
            int: Нормализованная позиция
        """
        max_position = (
            self.db.query(self.model_class)
            .filter(self.parent_column == parent_id)
            .count()
        )
        max_position = max(max_position - 1, 0)
        
        if position < 0:
            return 0
        elif position > max_position:
            return max_position
        return position
    
    def move_item(self, item_id: int, parent_id: int, old_position: int, new_position: int) -> None:
        """
        Перемещает элемент на новую позицию с автоматическим сдвигом других элементов.
        
        Args:
            item_id: ID элемента
            parent_id: ID родителя
            old_position: Текущая позиция
            new_position: Новая позиция
        """
        if old_position == new_position:
            return
        
        if new_position < old_position:
            # Сдвигаем элементы вправо
            self.shift_positions_right(
                parent_id=parent_id,
                from_position=new_position,
                exclude_id=item_id
            )
        else:
            # Сдвигаем элементы влево
            self.shift_positions_left(
                parent_id=parent_id,
                from_position=old_position,
                exclude_id=item_id
            )
        
        # Обновляем позицию элемента
        item = self.db.query(self.model_class).filter(self.model_class.id == item_id).first()
        if item:
            setattr(item, self.position_column.name, new_position)


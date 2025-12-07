import { useState, useRef, useCallback } from 'react';

/**
 * Хук для управления отображением preview при наведении
 * @param {number} delay - Задержка перед показом в мс (по умолчанию 400мс)
 * @returns {Object} - { isShowing, position, showPreview, hidePreview, handleMouseEnter, handleMouseLeave }
 */
function useHoverPreview(delay = 400) {
  const [isShowing, setIsShowing] = useState(false);
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const timeoutRef = useRef(null);
  const elementRef = useRef(null);

  const showPreview = useCallback((element) => {
    if (!element) return;

    const rect = element.getBoundingClientRect();

    // Позиционируем preview справа от карточки
    // Если не влезает справа - показываем слева
    const padding = 10;
    const previewWidth = 320; // ширина preview из StoryCardPreview
    const spaceRight = window.innerWidth - rect.right;
    const spaceLeft = rect.left;

    let x, y;

    if (spaceRight >= previewWidth + padding) {
      // Показываем справа
      x = rect.right + padding;
    } else if (spaceLeft >= previewWidth + padding) {
      // Показываем слева
      x = rect.left - previewWidth - padding;
    } else {
      // Показываем справа от курсора, даже если не влезает полностью
      x = rect.right + padding;
    }

    // Вертикально - выравниваем по верхнему краю карточки
    // Но проверяем, чтобы не вылезало за пределы экрана
    y = rect.top;
    const maxY = window.innerHeight - 400; // примерная высота preview
    if (y > maxY) {
      y = Math.max(padding, maxY);
    }

    setPosition({ x, y });
    setIsShowing(true);
  }, []);

  const hidePreview = useCallback(() => {
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
      timeoutRef.current = null;
    }
    setIsShowing(false);
  }, []);

  const handleMouseEnter = useCallback((event) => {
    const element = event.currentTarget;
    elementRef.current = element;

    // Очищаем предыдущий таймер, если есть
    if (timeoutRef.current) {
      clearTimeout(timeoutRef.current);
    }

    // Устанавливаем новый таймер
    timeoutRef.current = setTimeout(() => {
      showPreview(element);
    }, delay);
  }, [delay, showPreview]);

  const handleMouseLeave = useCallback(() => {
    hidePreview();
  }, [hidePreview]);

  return {
    isShowing,
    position,
    showPreview,
    hidePreview,
    handleMouseEnter,
    handleMouseLeave,
  };
}

export default useHoverPreview;

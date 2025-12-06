// Unified API error handler used across StoryMap hooks/components
export function handleApiError(error, onUnauthorized) {
  if (error?.response?.status === 401) {
    if (onUnauthorized) {
      onUnauthorized();
    }
    return 'Сессия истекла. Пожалуйста, войдите снова.';
  }

  if (error?.response?.data?.detail) {
    return error.response.data.detail;
  }

  if (error?.response) {
    return `Ошибка сервера: ${error.response.status}`;
  }

  if (error?.request) {
    return 'Не удалось подключиться к серверу';
  }

  return 'Произошла неизвестная ошибка';
}

export default handleApiError;


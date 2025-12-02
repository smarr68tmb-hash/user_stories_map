import axios from 'axios';

// Используем переменную окружения для production, fallback на localhost для разработки
const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: API_URL,
});

// Интерцептор запросов: добавляет токен
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Интерцептор ответов: обрабатывает 401 и обновляет токен
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Если ошибка 401 и это не запрос на обновление токена
    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      const refreshToken = localStorage.getItem('refresh_token');
      
      if (refreshToken) {
        try {
          // Пытаемся обновить токен
          const response = await axios.post(`${API_URL}/refresh`, {
            refresh_token: refreshToken
          });

          const { access_token, refresh_token: newRefreshToken } = response.data;

          // Сохраняем новые токены
          localStorage.setItem('auth_token', access_token);
          if (newRefreshToken) {
            localStorage.setItem('refresh_token', newRefreshToken);
          }

          // Обновляем заголовок и повторяем исходный запрос
          originalRequest.headers.Authorization = `Bearer ${access_token}`;
          return api(originalRequest);
        } catch (refreshError) {
          // Если не удалось обновить токен - разлогиниваем
          localStorage.removeItem('auth_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/'; // Или используйте колбэк для редиректа
          return Promise.reject(refreshError);
        }
      } else {
        // Если нет refresh токена - разлогиниваем
        localStorage.removeItem('auth_token');
        // window.location.href = '/'; 
      }
    }

    return Promise.reject(error);
  }
);

// AI Enhancement API
export const enhancement = {
  /**
   * Stage 1: Улучшает требования перед генерацией карты
   * @param {string} text - Исходный текст требований
   * @returns {Promise} - Улучшенные требования
   */
  enhance: (text) => api.post('/enhance-requirements', { text }),
  
  /**
   * Генерирует карту с возможностью пропуска enhancement
   * @param {string} text - Текст требований
   * @param {boolean} skipEnhancement - Пропустить Stage 1
   * @param {boolean} useEnhancedText - Использовать улучшенный текст
   * @returns {Promise} - Результат генерации
   */
  generateMap: (text, skipEnhancement = false, useEnhancedText = true) => 
    api.post('/generate-map', { 
      text, 
      skip_enhancement: skipEnhancement,
      use_enhanced_text: useEnhancedText
    }),
};

export const auth = {
  login: async (username, password) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await api.post('/token', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
    });
    
    const { access_token, refresh_token } = response.data;
    localStorage.setItem('auth_token', access_token);
    if (refresh_token) {
      localStorage.setItem('refresh_token', refresh_token);
    }
    return response.data;
  },
  
  register: async (email, password, fullName) => {
    const response = await api.post('/register', {
      email,
      password,
      full_name: fullName
    });
    return response.data;
  },
  
  logout: async () => {
    const refreshToken = localStorage.getItem('refresh_token');
    if (refreshToken) {
      try {
        await api.post('/logout', { refresh_token: refreshToken });
      } catch (e) {
        console.error("Logout error:", e);
      }
    }
    localStorage.removeItem('auth_token');
    localStorage.removeItem('refresh_token');
  },
  
  getMe: () => api.get('/me')
};

export const activities = {
  create: (projectId, title, position) => 
    api.post('/activity', { project_id: projectId, title, position }),
  
  update: (activityId, title, position) => 
    api.put(`/activity/${activityId}`, { title, position }),
  
  delete: (activityId) => 
    api.delete(`/activity/${activityId}`),
};

export const tasks = {
  create: (activityId, title, position) => 
    api.post('/task', { activity_id: activityId, title, position }),
  
  update: (taskId, title, position) => 
    api.put(`/task/${taskId}`, { title, position }),
  
  delete: (taskId) => 
    api.delete(`/task/${taskId}`),
};

export const projects = {
  update: (projectId, name) => 
    api.put(`/project/${projectId}`, { name }),
  
  delete: (projectId) => 
    api.delete(`/project/${projectId}`),
};

export default api;


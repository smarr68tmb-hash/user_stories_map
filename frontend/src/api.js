import axios from 'axios';

// Используем переменную окружения для production, fallback на localhost для разработки
const API_URL = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";

const api = axios.create({
  baseURL: API_URL,
  withCredentials: true,
});

// Делаем отправку cookies явной для всех запросов
api.interceptors.request.use(
  (config) => {
    config.withCredentials = true;
    return config;
  },
  (error) => Promise.reject(error)
);

let isRefreshing = false;
let refreshSubscribers = [];

const subscribeTokenRefresh = (callback) => {
  refreshSubscribers.push(callback);
};

const onRefreshed = () => {
  refreshSubscribers.forEach((cb) => cb());
  refreshSubscribers = [];
};

// Интерцептор ответов: обрабатывает 401 и обновляет токен через httpOnly cookie
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    // Если ошибка 401 и это не запрос на обновление токена
    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest?.url?.includes('/refresh')
    ) {
      originalRequest._retry = true;

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          subscribeTokenRefresh(() => {
            api(originalRequest).then(resolve).catch(reject);
          });
        });
      }

      isRefreshing = true;

      try {
        await axios.post(`${API_URL}/refresh`, {}, { withCredentials: true });
        isRefreshing = false;
        onRefreshed();
        return api(originalRequest);
      } catch (refreshError) {
        isRefreshing = false;
        refreshSubscribers = [];
        try {
          await axios.post(`${API_URL}/logout`, {}, { withCredentials: true });
        } catch (logoutError) {
          console.error("Logout after refresh failure error:", logoutError);
        }
        // Не делаем redirect, чтобы избежать бесконечных перезагрузок.
        // Компоненты-вызывающие обработают 401 и покажут экран логина.
        return Promise.reject(refreshError);
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
   * @param {boolean} useAgent - Использовать AI-агента для генерации
   * @returns {Promise} - Результат генерации
   */
  generateMap: (text, skipEnhancement = false, useEnhancedText = true, useAgent = false) =>
    api.post('/generate-map', {
      text,
      skip_enhancement: skipEnhancement,
      use_enhanced_text: useEnhancedText,
      use_agent: useAgent
    }),
};

export const auth = {
  login: async (username, password) => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    
    const response = await api.post('/token', formData, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    withCredentials: true,
    });
    
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
  try {
    await api.post('/logout', {}, { withCredentials: true });
  } catch (e) {
    console.error("Logout error:", e);
  }
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
  
  move: (taskId, position) => 
    api.patch(`/task/${taskId}/move`, { position }),
};

export const projects = {
  get: (projectId) =>
    api.get(`/project/${projectId}`),

  update: (projectId, name) => 
    api.put(`/project/${projectId}`, { name }),
  
  delete: (projectId) => 
    api.delete(`/project/${projectId}`),
};

export default api;


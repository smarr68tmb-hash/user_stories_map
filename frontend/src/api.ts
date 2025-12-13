import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios';
import type {
  Activity,
  ActivityPayload,
  EnhancementResponse,
  GenerateMapResponse,
  Project,
  WireframeResponse,
  Story,
  StoryPayload,
  Task,
  TaskPayload,
  TokenResponse,
  User,
} from './types';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

// Хранение токенов в памяти (для cross-domain запросов)
// В production на разных доменах httpOnly cookies не работают из-за ограничений браузера
const tokenStorage = {
  accessToken: null as string | null,
  refreshToken: null as string | null,

  setTokens(access: string | null, refresh: string | null) {
    this.accessToken = access;
    this.refreshToken = refresh;
    // Сохраняем refresh token в localStorage для восстановления сессии
    if (refresh) {
      localStorage.setItem('refresh_token', refresh);
    } else {
      localStorage.removeItem('refresh_token');
    }
  },

  getAccessToken() {
    return this.accessToken;
  },

  getRefreshToken() {
    // Пробуем получить из памяти, затем из localStorage
    return this.refreshToken || localStorage.getItem('refresh_token');
  },

  clear() {
    this.accessToken = null;
    this.refreshToken = null;
    localStorage.removeItem('refresh_token');
  },
};

const api: AxiosInstance = axios.create({
  baseURL: API_URL,
  withCredentials: true,
});

// Request interceptor - добавляет Authorization header
api.interceptors.request.use(
  (config) => {
    const nextConfig = { ...config, withCredentials: true } as AxiosRequestConfig;

    // Добавляем access token в заголовок Authorization
    const accessToken = tokenStorage.getAccessToken();
    if (accessToken && nextConfig.headers) {
      (nextConfig.headers as Record<string, string>)['Authorization'] = `Bearer ${accessToken}`;
    }

    return nextConfig;
  },
  (error) => Promise.reject(error),
);

let isRefreshing = false;
let refreshSubscribers: Array<(token: string) => void> = [];

const subscribeTokenRefresh = (callback: (token: string) => void) => {
  refreshSubscribers.push(callback);
};

const onRefreshed = (newToken: string) => {
  refreshSubscribers.forEach((cb) => cb(newToken));
  refreshSubscribers = [];
};

// Response interceptor - обрабатывает 401 и обновляет токен
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

    if (
      error.response?.status === 401 &&
      !originalRequest._retry &&
      !originalRequest?.url?.includes('/refresh') &&
      !originalRequest?.url?.includes('/token')
    ) {
      originalRequest._retry = true;

      const refreshToken = tokenStorage.getRefreshToken();
      if (!refreshToken) {
        tokenStorage.clear();
        return Promise.reject(error);
      }

      if (isRefreshing) {
        return new Promise((resolve, reject) => {
          subscribeTokenRefresh((newToken: string) => {
            if (originalRequest.headers) {
              (originalRequest.headers as Record<string, string>)['Authorization'] = `Bearer ${newToken}`;
            }
            api(originalRequest).then(resolve).catch(reject);
          });
        });
      }

      isRefreshing = true;

      try {
        // Отправляем refresh token в теле запроса (не полагаемся на cookies)
        const response = await axios.post<TokenResponse>(
          `${API_URL}/refresh`,
          { refresh_token: refreshToken },
          { withCredentials: true }
        );

        const { access_token, refresh_token: newRefreshToken } = response.data;
        tokenStorage.setTokens(access_token, newRefreshToken);

        isRefreshing = false;
        onRefreshed(access_token);

        // Повторяем оригинальный запрос с новым токеном
        if (originalRequest.headers) {
          (originalRequest.headers as Record<string, string>)['Authorization'] = `Bearer ${access_token}`;
        }
        return api(originalRequest);
      } catch (refreshError) {
        isRefreshing = false;
        refreshSubscribers = [];
        tokenStorage.clear();

        try {
          const rt = tokenStorage.getRefreshToken();
          await axios.post(`${API_URL}/logout`, { refresh_token: rt }, { withCredentials: true });
        } catch (logoutError) {
          console.error('Logout after refresh failure error:', logoutError);
        }
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  },
);

export const enhancement = {
  enhance: (text: string) => api.post<EnhancementResponse>('/enhance-requirements', { text }),
  generateMap: (
    text: string,
    skipEnhancement = false,
    useEnhancedText = true,
    useAgent = false,
  ) =>
    api.post<GenerateMapResponse>('/generate-map', {
      text,
      skip_enhancement: skipEnhancement,
      use_enhanced_text: useEnhancedText,
      use_agent: useAgent,
    }),
  generateMapDemo: (text: string) =>
    axios.post<{
      status: string;
      project_name: string;
      map: any[];
      releases: any[];
      demo_mode: boolean;
      message: string;
    }>(`${API_URL}/generate-map/demo`, {
      text,
      skip_enhancement: true,
      use_enhanced_text: false,
      use_agent: false,
    }),
};

export const auth = {
  login: async (username: string, password: string): Promise<TokenResponse> => {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    const response = await api.post<TokenResponse>('/token', formData, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      withCredentials: true,
    });

    // Сохраняем токены после успешного логина
    const { access_token, refresh_token } = response.data;
    tokenStorage.setTokens(access_token, refresh_token);

    return response.data;
  },

  register: async (email: string, password: string, fullName?: string | null): Promise<User> => {
    const response = await api.post<User>('/register', {
      email,
      password,
      full_name: fullName,
    });
    return response.data;
  },

  logout: async () => {
    try {
      const refreshToken = tokenStorage.getRefreshToken();
      await api.post('/logout', { refresh_token: refreshToken }, { withCredentials: true });
    } catch (e) {
      console.error('Logout error:', e);
    } finally {
      tokenStorage.clear();
    }
  },

  getMe: () => api.get<User>('/me'),

  // Метод для восстановления сессии из localStorage при загрузке страницы
  tryRestoreSession: async (): Promise<User | null> => {
    const refreshToken = tokenStorage.getRefreshToken();
    if (!refreshToken) {
      return null;
    }

    try {
      // Пробуем обновить access token
      const response = await axios.post<TokenResponse>(
        `${API_URL}/refresh`,
        { refresh_token: refreshToken },
        { withCredentials: true }
      );

      const { access_token, refresh_token: newRefreshToken } = response.data;
      tokenStorage.setTokens(access_token, newRefreshToken);

      // Получаем данные пользователя
      const userResponse = await api.get<User>('/me');
      return userResponse.data;
    } catch {
      tokenStorage.clear();
      return null;
    }
  },
};

export const activities = {
  create: (projectId: number, title: string, position?: number) =>
    api.post<Activity>('/activity', { project_id: projectId, title, position } satisfies ActivityPayload),

  update: (activityId: number, title?: string, position?: number) =>
    api.put<Activity>(`/activity/${activityId}`, { title, position }),

  delete: (activityId: number) => api.delete(`/activity/${activityId}`),
};

export const tasks = {
  create: (activityId: number, title: string, position?: number) =>
    api.post<Task>('/task', { activity_id: activityId, title, position } satisfies TaskPayload),

  update: (taskId: number, title: string, position?: number) =>
    api.put<Task>(`/task/${taskId}`, { title, position }),

  delete: (taskId: number) => api.delete(`/task/${taskId}`),

  move: (taskId: number, position: number) => api.patch<Task>(`/task/${taskId}/move`, { position }),
};

export const projects = {
  get: (projectId: number | string) => api.get<Project>(`/project/${projectId}`),

  update: (projectId: number | string, name: string) => api.put<Project>(`/project/${projectId}`, { name }),

  delete: (projectId: number | string) => api.delete(`/project/${projectId}`),
};

export const wireframes = {
  generate: (projectId: number | string) => api.post<{ status: string; job_id: string }>(`/project/${projectId}/wireframe/generate`),
  get: (projectId: number | string) => api.get<WireframeResponse>(`/project/${projectId}/wireframe`),
  status: (projectId: number | string, jobId?: string | null) =>
    api.get<WireframeResponse>(`/project/${projectId}/wireframe/status`, {
      params: jobId ? { job_id: jobId } : undefined,
    }),
};

export const stories = {
  create: (payload: StoryPayload) => api.post<Story>('/story', payload),
  update: (storyId: number, updates: Partial<StoryPayload>) => api.put<Story>(`/story/${storyId}`, updates),
  delete: (storyId: number) => api.delete(`/story/${storyId}`),
  move: (storyId: number, target: { task_id: number; release_id: number | null; position: number }) =>
    api.patch<Story>(`/story/${storyId}/move`, target),
  changeStatus: (storyId: number, status: StoryPayload['status']) =>
    api.patch<Story>(`/story/${storyId}/status`, { status }),
};

export default api;

import axios, { type AxiosInstance, type AxiosRequestConfig } from 'axios';
import type {
  Activity,
  ActivityPayload,
  EnhancementResponse,
  GenerateMapResponse,
  Project,
  Story,
  StoryPayload,
  Task,
  TaskPayload,
  TokenResponse,
  User,
} from './types';

const API_URL = import.meta.env.VITE_API_URL || 'http://127.0.0.1:8000';

const api: AxiosInstance = axios.create({
  baseURL: API_URL,
  withCredentials: true,
});

api.interceptors.request.use(
  (config) => {
    const nextConfig = { ...config, withCredentials: true } as AxiosRequestConfig;
    return nextConfig;
  },
  (error) => Promise.reject(error),
);

let isRefreshing = false;
let refreshSubscribers: Array<() => void> = [];

const subscribeTokenRefresh = (callback: () => void) => {
  refreshSubscribers.push(callback);
};

const onRefreshed = () => {
  refreshSubscribers.forEach((cb) => cb());
  refreshSubscribers = [];
};

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config as AxiosRequestConfig & { _retry?: boolean };

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
      await api.post('/logout', {}, { withCredentials: true });
    } catch (e) {
      console.error('Logout error:', e);
    }
  },

  getMe: () => api.get<User>('/me'),
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


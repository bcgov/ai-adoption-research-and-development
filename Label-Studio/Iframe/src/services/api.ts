import axios from 'axios';

// In development, Vite proxies /api to the backend
// In production, this would be the actual API URL
const api = axios.create({
  baseURL: '',
  withCredentials: true,
});

export interface User {
  id: number;
  email: string;
}

export interface AuthResponse {
  success: boolean;
  user: User;
}

export interface MeResponse {
  user: User;
  authenticated: boolean;
}

export const authApi = {
  login: async (email: string, password: string): Promise<AuthResponse> => {
    const response = await api.post<AuthResponse>('/api/auth/login', { email, password });
    return response.data;
  },

  logout: async (): Promise<void> => {
    await api.post('/api/auth/logout');
  },

  me: async (): Promise<MeResponse> => {
    const response = await api.get<MeResponse>('/api/auth/me');
    return response.data;
  },
};

export default api;

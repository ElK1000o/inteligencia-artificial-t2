import { apiClient } from './client';
import { TokenResponse, User } from '../types';

export const login = (email: string, password: string) =>
  apiClient.post<TokenResponse>('/auth/login', { email, password });

export const getMe = () => apiClient.get<User>('/auth/me');

export const logout = (refreshToken: string) =>
  apiClient.post('/auth/logout', { refresh_token: refreshToken });

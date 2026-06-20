import { apiClient } from './client';
import { DashboardStats } from '../types';

export const getDashboardStats = () =>
  apiClient.get<DashboardStats>('/dashboard/stats');

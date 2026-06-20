import axios, { AxiosInstance, AxiosError, InternalAxiosRequestConfig } from 'axios';

const API_BASE = '/api/v1';

export const apiClient: AxiosInstance = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 30000,
});

// Attach token to every request
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// NOTE: localStorage is used for token storage as a pragmatic choice for this
// academic project. In production, prefer httpOnly cookies to prevent XSS token theft.

let _isRefreshing = false;
let _refreshQueue: Array<(token: string) => void> = [];

async function _tryRefresh(): Promise<string | null> {
  const refreshToken = localStorage.getItem('refresh_token');
  if (!refreshToken) return null;
  try {
    const resp = await axios.post(`${API_BASE}/auth/refresh`, {
      refresh_token: refreshToken,
    });
    const newToken: string = resp.data.access_token;
    const newRefresh: string = resp.data.refresh_token;
    localStorage.setItem('access_token', newToken);
    localStorage.setItem('refresh_token', newRefresh);
    return newToken;
  } catch {
    return null;
  }
}

// Handle 401: attempt token refresh once, then redirect to login
apiClient.interceptors.response.use(
  (res) => res,
  async (error: AxiosError) => {
    const original = error.config as InternalAxiosRequestConfig & { _retry?: boolean };
    if (error.response?.status === 401 && !original._retry) {
      original._retry = true;

      if (_isRefreshing) {
        // Another refresh already in-flight — queue this request
        return new Promise((resolve) => {
          _refreshQueue.push((token) => {
            original.headers.Authorization = `Bearer ${token}`;
            resolve(apiClient(original));
          });
        });
      }

      _isRefreshing = true;
      const newToken = await _tryRefresh();
      _isRefreshing = false;

      if (newToken) {
        _refreshQueue.forEach((cb) => cb(newToken));
        _refreshQueue = [];
        original.headers.Authorization = `Bearer ${newToken}`;
        return apiClient(original);
      }

      // Refresh failed — clear session and redirect
      _refreshQueue = [];
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

import axios from 'axios';

export function resolveApiBaseUrl(env = import.meta.env) {
  const raw = env?.VITE_API_URL || env?.VITE_API_BASE_URL || '';
  if (!raw || !raw.trim()) {
    return '/api';
  }
  const trimmed = raw.trim().replace(/\/+$/, '');
  return trimmed.endsWith('/api') ? trimmed : `${trimmed}/api`;
}

const API_BASE_URL = resolveApiBaseUrl();

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('hospital_jwt_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error?.response?.status;
    if (status === 401) {
      localStorage.removeItem('hospital_jwt_token');
      localStorage.removeItem('hospital_user');
      window.dispatchEvent(new CustomEvent('hospital:unauthorized'));
    }
    return Promise.reject(error);
  }
);

export function extractErrorMessage(err, fallback = 'An unexpected error occurred.') {
  return (
    err?.response?.data?.error?.message ||
    err?.message ||
    fallback
  );
}

export default api;

import axios from 'axios';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api';

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

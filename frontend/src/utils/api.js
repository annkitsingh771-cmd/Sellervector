import axios from 'axios';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
export const API = `${BACKEND_URL}/api`;

export const apiClient = axios.create({ baseURL: API });

// ── Request interceptor ───────────────────────────────────────
// Attaches JWT token + active store header on every request.
// This is what ensures Account A's calls never bleed into Account B's data.
apiClient.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // pass active store so backend can scope multi-store queries
    const storeId = localStorage.getItem('activeStoreId');
    if (storeId) {
      config.headers['X-Store-Id'] = storeId;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ── Response interceptor ─────────────────────────────────────
// Redirect to /login on 401 (expired token / wrong account)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token');
      localStorage.removeItem('user');
      localStorage.removeItem('activeStoreId');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

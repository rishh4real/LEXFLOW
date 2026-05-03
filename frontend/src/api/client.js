/**
 * api/client.js
 * -------------
 * Axios base client for LexFlow.
 * - Sets base URL to FastAPI backend
 * - Auto-injects Authorization header from localStorage token
 * - Handles 401 globally (clears token, redirects to login)
 */

import axios from 'axios';

const API_BASE =
  import.meta.env.VITE_API_URL ||
  (import.meta.env.DEV ? 'http://localhost:10000' : '/api');

const client = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
});

// ── Request interceptor: attach JWT token ─────────────────────────────────────
client.interceptors.request.use((config) => {
  const token = localStorage.getItem('lf_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response interceptor: handle auth errors globally ────────────────────────
client.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('lf_token');
      localStorage.removeItem('lf_user');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default client;

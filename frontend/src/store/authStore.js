/**
 * store/authStore.js
 * ------------------
 * Zustand global store for authentication state.
 * Persists token + user to localStorage so page refresh keeps session alive.
 */

import { create } from 'zustand';

const useAuthStore = create((set) => ({
  // ── State ──────────────────────────────────────────────────────────────────
  token: localStorage.getItem('lf_token') || null,
  user: (() => {
    try {
      return JSON.parse(localStorage.getItem('lf_user')) || null;
    } catch {
      return null;
    }
  })(),

  // ── Actions ────────────────────────────────────────────────────────────────

  /** Called after successful /auth/login */
  login: (token, user) => {
    localStorage.setItem('lf_token', token);
    localStorage.setItem('lf_user', JSON.stringify(user));
    set({ token, user });
  },

  /** Clear session and redirect to login */
  logout: () => {
    localStorage.removeItem('lf_token');
    localStorage.removeItem('lf_user');
    set({ token: null, user: null });
  },

  /** Update user data in store (e.g. after profile update) */
  setUser: (user) => {
    localStorage.setItem('lf_user', JSON.stringify(user));
    set({ user });
  },
}));

export default useAuthStore;

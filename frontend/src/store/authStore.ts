// TICKR — Zustand auth store
import { create } from 'zustand';
import type { User } from '../types';
import api from '../api/client';

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (username: string, password: string) => Promise<void>;
  register: (data: { username: string; email: string; full_name: string; password: string }) => Promise<void>;
  logout: () => void;
  updateProfile: (data: { full_name?: string; email?: string }) => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: (() => {
    try { return JSON.parse(localStorage.getItem('tickr_user') || 'null'); } catch { return null; }
  })(),
  token: localStorage.getItem('tickr_token'),
  isAuthenticated: !!localStorage.getItem('tickr_token'),

  login: async (username, password) => {
    const form = new FormData();
    form.append('username', username);
    form.append('password', password);
    const { data } = await api.post('/api/auth/login', form, {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    });
    localStorage.setItem('tickr_token', data.access_token);
    localStorage.setItem('tickr_user', JSON.stringify(data.user));
    set({ token: data.access_token, user: data.user, isAuthenticated: true });
  },

  register: async (payload) => {
    const { data } = await api.post('/api/auth/register', payload);
    localStorage.setItem('tickr_token', data.access_token);
    localStorage.setItem('tickr_user', JSON.stringify(data.user));
    set({ token: data.access_token, user: data.user, isAuthenticated: true });
  },

  logout: () => {
    localStorage.removeItem('tickr_token');
    localStorage.removeItem('tickr_user');
    set({ user: null, token: null, isAuthenticated: false });
  },

  updateProfile: async (payload) => {
    const { data } = await api.put('/api/profile', payload);
    set((s) => s.user ? { user: { ...s.user, ...data } } : {});
    const user = JSON.parse(localStorage.getItem('tickr_user') || '{}');
    localStorage.setItem('tickr_user', JSON.stringify({ ...user, ...data }));
  },
}));

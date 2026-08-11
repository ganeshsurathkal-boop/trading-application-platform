// TICKR — Zustand watchlist store
import { create } from 'zustand';
import type { Watchlist } from '../types';
import api from '../api/client';

interface WatchlistState {
  watchlists: Watchlist[];
  activeWatchlistId: number | null;
  loading: boolean;
  fetchWatchlists: () => Promise<void>;
  createWatchlist: (name: string) => Promise<void>;
  deleteWatchlist: (id: number) => Promise<void>;
  addStock: (watchlistId: number, symbol: string, exchange?: string) => Promise<void>;
  removeStock: (watchlistId: number, symbol: string) => Promise<void>;
  setActive: (id: number) => void;
}

export const useWatchlistStore = create<WatchlistState>((set, get) => ({
  watchlists: [],
  activeWatchlistId: null,
  loading: false,

  fetchWatchlists: async () => {
    set({ loading: true });
    try {
      const { data } = await api.get('/api/watchlists');
      set({ watchlists: data, activeWatchlistId: data[0]?.id ?? null, loading: false });
    } catch { set({ loading: false }); }
  },

  createWatchlist: async (name) => {
    const { data } = await api.post('/api/watchlists', { name });
    set((s) => ({ watchlists: [...s.watchlists, data], activeWatchlistId: data.id }));
  },

  deleteWatchlist: async (id) => {
    await api.delete(`/api/watchlists/${id}`);
    set((s) => {
      const wls = s.watchlists.filter((w) => w.id !== id);
      return { watchlists: wls, activeWatchlistId: wls[0]?.id ?? null };
    });
  },

  addStock: async (watchlistId, symbol, exchange = 'NSE') => {
    await api.post(`/api/watchlists/${watchlistId}/stocks`, { symbol, exchange });
    await get().fetchWatchlists();
  },

  removeStock: async (watchlistId, symbol) => {
    await api.delete(`/api/watchlists/${watchlistId}/stocks/${symbol}`);
    set((s) => ({
      watchlists: s.watchlists.map((w) =>
        w.id === watchlistId ? { ...w, stocks: w.stocks.filter((s) => s.symbol !== symbol) } : w
      ),
    }));
  },

  setActive: (id) => set({ activeWatchlistId: id }),
}));

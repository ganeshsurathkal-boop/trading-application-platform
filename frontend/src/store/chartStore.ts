// TICKR — Zustand chart store
import { create } from 'zustand';
import type { Candle, ActiveIndicator, IndicatorPlugin } from '../types';
import api from '../api/client';

export type ChartType = 'candlestick' | 'line';
export type Interval = '1D' | '1W' | '1M';
export type Duration = '1M' | '3M' | '6M' | '1Y' | '2Y' | '5Y';

// How many days to fetch per "load older" chunk
const OLDER_CHUNK_DAYS = 180; // 6 months per chunk

interface ChartState {
  symbol: string;
  interval: Interval;
  duration: Duration;
  chartType: ChartType;
  candles: Candle[];
  activeIndicators: ActiveIndicator[];
  availableIndicators: IndicatorPlugin[];
  loading: boolean;
  loadingMore: boolean;
  hasMoreHistory: boolean;
  error: string | null;

  setSymbol: (symbol: string) => void;
  setInterval: (interval: Interval) => void;
  setDuration: (duration: Duration) => void;
  setChartType: (type: ChartType) => void;
  fetchCandles: () => Promise<void>;
  fetchOlderCandles: () => Promise<void>;
  fetchAvailableIndicators: () => Promise<void>;
  addIndicator: (name: string, params?: Record<string, number>) => Promise<void>;
  removeIndicator: (id: string) => void;
}

export const useChartStore = create<ChartState>((set, get) => ({
  symbol: 'RELIANCE',
  interval: '1D',
  duration: '6M',
  chartType: 'candlestick',
  candles: [],
  activeIndicators: [],
  availableIndicators: [],
  loading: false,
  loadingMore: false,
  hasMoreHistory: true,
  error: null,

  setSymbol: (symbol) => {
    set({ symbol, hasMoreHistory: true });
    get().fetchCandles();
  },
  setInterval: (interval) => {
    set({ interval, hasMoreHistory: true });
    get().fetchCandles();
  },
  setDuration: (duration) => {
    set({ duration, hasMoreHistory: true });
    get().fetchCandles();
  },
  setChartType: (chartType) => set({ chartType }),

  fetchCandles: async () => {
    const { symbol, interval, duration } = get();
    set({ loading: true, error: null, hasMoreHistory: true });
    try {
      const { data } = await api.get(`/api/candles/${symbol}`, {
        params: { interval, duration, exchange: 'NSE' },
      });
      set({ candles: data.candles, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  fetchOlderCandles: async () => {
    const { symbol, interval, candles, loadingMore, hasMoreHistory } = get();
    if (loadingMore || !hasMoreHistory || candles.length === 0) return;

    // Determine the oldest date we currently have
    const sorted = [...candles].sort((a, b) => a.date.localeCompare(b.date));
    const oldestDate = new Date(sorted[0].date);

    // The "to_date" for the older chunk is the day before our oldest candle
    const toDate = new Date(oldestDate);
    toDate.setDate(toDate.getDate() - 1);

    // The "from_date" is OLDER_CHUNK_DAYS before that
    const fromDate = new Date(toDate);
    fromDate.setDate(fromDate.getDate() - OLDER_CHUNK_DAYS);

    const fmt = (d: Date) => d.toISOString().split('T')[0];

    set({ loadingMore: true });
    try {
      const { data } = await api.get(`/api/candles/${symbol}`, {
        params: {
          interval,
          exchange: 'NSE',
          from_date: fmt(fromDate),
          to_date: fmt(toDate),
        },
      });

      const olderCandles: Candle[] = data.candles ?? [];
      if (olderCandles.length === 0) {
        // No more history available — stop triggering further fetches
        set({ loadingMore: false, hasMoreHistory: false });
        return;
      }

      // Deduplicate and prepend older data
      const existingDates = new Set(candles.map((c) => c.date));
      const newCandles = olderCandles.filter((c) => !existingDates.has(c.date));
      set((s) => ({
        candles: [...newCandles, ...s.candles],
        loadingMore: false,
      }));
    } catch {
      set({ loadingMore: false });
    }
  },

  fetchAvailableIndicators: async () => {
    try {
      const { data } = await api.get('/api/indicators');
      set({ availableIndicators: data.indicators });
    } catch {}
  },

  addIndicator: async (name, params = {}) => {
    const { symbol, duration, availableIndicators } = get();
    const def = availableIndicators.find((i) => i.name === name);
    if (!def) return;
    const mergedParams = { ...def.default_params, ...params };
    try {
      const { data } = await api.post('/api/indicators/compute', {
        symbol, exchange: 'NSE', duration, indicator: name, params: mergedParams,
      });
      const id = `${name}_${Object.values(mergedParams).join('_')}`;
      const active: ActiveIndicator = {
        id,
        name,
        label: data.label,
        overlay: data.overlay,
        params: mergedParams,
        data: data.data,
      };
      set((s) => ({
        activeIndicators: [...s.activeIndicators.filter((i) => i.id !== id), active],
      }));
    } catch (e) {
      console.error('Failed to compute indicator', e);
    }
  },

  removeIndicator: (id) => {
    set((s) => ({ activeIndicators: s.activeIndicators.filter((i) => i.id !== id) }));
  },
}));


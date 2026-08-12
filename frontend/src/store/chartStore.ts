// TICKR — Zustand chart store
import { create } from 'zustand';
import type { Candle, ActiveIndicator, IndicatorPlugin } from '../types';
import api from '../api/client';

export type ChartType = 'candlestick' | 'line';
export type Interval = '1D' | '1W' | '1M';
export type Duration = '1M' | '3M' | '6M' | '1Y' | '2Y' | '5Y';

// Initial visible window — always load 90 days on first render (fast).
// Older data is fetched on-demand as the user scrolls left.
const INITIAL_WINDOW_DAYS = 90;

// How many days per "load older" chunk when scrolling left
const OLDER_CHUNK_DAYS = 180;

// Maximum lookback in days for each Duration setting
const DURATION_MAP: Record<Duration, number> = {
  '1M': 30, '3M': 90, '6M': 180, '1Y': 365, '2Y': 730, '5Y': 1825,
};

const fmt = (d: Date) => d.toISOString().split('T')[0];

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
  duration: '1Y',       // default: 1 year max lookback
  chartType: 'candlestick',
  candles: [],
  activeIndicators: [],
  availableIndicators: [],
  loading: false,
  loadingMore: false,
  hasMoreHistory: true,
  error: null,

  setSymbol: (symbol) => {
    set({ symbol, candles: [], hasMoreHistory: true });
    get().fetchCandles();
  },
  setInterval: (interval) => {
    set({ interval, candles: [], hasMoreHistory: true });
    get().fetchCandles();
  },
  setDuration: (duration) => {
    // Changing duration resets the view so the user gets the right cap applied
    set({ duration, candles: [], hasMoreHistory: true });
    get().fetchCandles();
  },
  setChartType: (chartType) => set({ chartType }),

  // ── Initial fetch: always a fixed 90-day window for fast first render ──────
  fetchCandles: async () => {
    const { symbol, interval } = get();
    set({ loading: true, error: null, hasMoreHistory: true });

    const toDate = new Date();
    const fromDate = new Date();
    fromDate.setDate(fromDate.getDate() - INITIAL_WINDOW_DAYS);

    try {
      const { data } = await api.get(`/api/candles/${symbol}`, {
        params: { interval, exchange: 'NSE', from_date: fmt(fromDate), to_date: fmt(toDate) },
      });
      set({ candles: data.candles, loading: false });
    } catch (e: any) {
      set({ error: e.message, loading: false });
    }
  },

  // ── On-demand fetch: loads older chunks as user scrolls left ───────────────
  fetchOlderCandles: async () => {
    const { symbol, interval, candles, loadingMore, hasMoreHistory, duration } = get();
    if (loadingMore || !hasMoreHistory || candles.length === 0) return;

    // Oldest candle we currently have
    const sorted = [...candles].sort((a, b) => a.date.localeCompare(b.date));
    const oldestDate = new Date(sorted[0].date);

    // Hard cap: never go further back than the selected duration
    const maxDays = DURATION_MAP[duration] ?? 365;
    const maxFromDate = new Date();
    maxFromDate.setDate(maxFromDate.getDate() - maxDays);

    if (oldestDate <= maxFromDate) {
      set({ hasMoreHistory: false });
      return;
    }

    const toDate = new Date(oldestDate);
    toDate.setDate(toDate.getDate() - 1);

    const fromDate = new Date(toDate);
    fromDate.setDate(fromDate.getDate() - OLDER_CHUNK_DAYS);
    // Don't go beyond the duration cap
    if (fromDate < maxFromDate) fromDate.setTime(maxFromDate.getTime());

    set({ loadingMore: true });
    try {
      const { data } = await api.get(`/api/candles/${symbol}`, {
        params: { interval, exchange: 'NSE', from_date: fmt(fromDate), to_date: fmt(toDate) },
      });

      const olderCandles: Candle[] = data.candles ?? [];
      if (olderCandles.length === 0) {
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

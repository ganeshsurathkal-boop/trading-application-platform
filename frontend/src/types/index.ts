// TICKR — Shared TypeScript types

export interface Candle {
  date: string;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  symbol?: string;
  exchange?: string;
}

export interface IndicatorPlugin {
  name: string;
  label: string;
  description: string;
  category: string;
  overlay: boolean;
  default_params: Record<string, number>;
  param_schema: ParamDef[];
}

export interface ParamDef {
  name: string;
  type: 'int' | 'float';
  min: number;
  max: number;
  step?: number;
  label: string;
}

export interface ActiveIndicator {
  id: string;           // unique key e.g. "SMA_20"
  name: string;
  label: string;
  overlay: boolean;
  params: Record<string, number>;
  data: IndicatorDataPoint[];
}

export interface IndicatorDataPoint {
  date: string;
  [key: string]: number | string;
}

export interface Watchlist {
  id: number;
  name: string;
  stocks: WatchlistStock[];
}

export interface WatchlistStock {
  symbol: string;
  exchange: string;
  price?: number;
  change_pct?: number;
}

export interface User {
  id: number;
  username: string;
  full_name: string;
  email: string;
  avatar_initials: string;
}

export interface ScannerDef {
  name: string;
  description: string;
  category: string;
  param_schema: ParamDef[];
}

export interface ScanResult {
  symbol: string;
  exchange: string;
  price: number;
  change_pct: number;
  [key: string]: string | number;
}

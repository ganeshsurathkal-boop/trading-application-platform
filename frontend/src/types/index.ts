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
  default?: number;
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
  matched_criteria?: string[];
  [key: string]: string | number | string[] | undefined;
}

export interface ComboCriterion {
  scanner_name: string;
  params: Record<string, number>;
}

export interface ScanCombo {
  id: number;
  name: string;
  universe: string;
  exchange: string;
  created_at: string;
  updated_at: string;
  criteria: ComboCriterion[];
}

export interface ComboRunResult {
  combo_id: number | null;
  combo_name: string | null;
  universe: string;
  exchange: string;
  run_at: string;
  criteria: ComboCriterion[];
  match_count: number;
  per_criterion_counts: Record<string, number>;
  results: ScanResult[];
}

// TICKR — Zustand scanner store: available scanners + saved combos + in-progress builder state
import { create } from 'zustand';
import type { ScannerDef, ScanCombo, ComboCriterion, ComboRunResult } from '../types';
import api from '../api/client';

interface ScannersByCategory {
  technical: ScannerDef[];
  fundamental: ScannerDef[];
  plugin: ScannerDef[];
}

interface ScannerState {
  scannersByCategory: ScannersByCategory;
  universes: string[];
  savedCombos: ScanCombo[];
  loading: boolean;
  running: boolean;

  builderCriteria: ComboCriterion[];
  builderUniverse: string;
  builderExchange: string;
  editingComboId: number | null;

  fetchScanners: () => Promise<void>;
  fetchSavedCombos: () => Promise<void>;

  addCriterion: (scannerName: string) => void;
  removeCriterion: (scannerName: string) => void;
  updateCriterionParam: (scannerName: string, paramName: string, value: number) => void;
  setBuilderUniverse: (universe: string) => void;
  loadComboIntoBuilder: (combo: ScanCombo) => void;
  resetBuilder: () => void;

  saveCombo: (name: string) => Promise<ScanCombo>;
  deleteCombo: (id: number) => Promise<void>;
  runBuilderAdHoc: () => Promise<ComboRunResult>;
  runSavedCombo: (id: number) => Promise<ComboRunResult>;

  findScannerDef: (scannerName: string) => ScannerDef | undefined;
}

export const useScannerStore = create<ScannerState>((set, get) => ({
  scannersByCategory: { technical: [], fundamental: [], plugin: [] },
  universes: [],
  savedCombos: [],
  loading: false,
  running: false,

  builderCriteria: [],
  builderUniverse: 'NIFTY 50',
  builderExchange: 'NSE',
  editingComboId: null,

  fetchScanners: async () => {
    set({ loading: true });
    try {
      const { data } = await api.get('/api/scanners');
      set({ scannersByCategory: data.scanners, universes: data.universes, loading: false });
    } catch {
      set({ loading: false });
    }
  },

  fetchSavedCombos: async () => {
    try {
      const { data } = await api.get('/api/scan-combos');
      set({ savedCombos: data });
    } catch {
      /* silently fail — the "My custom scanners" section just stays empty */
    }
  },

  findScannerDef: (scannerName) => {
    const { scannersByCategory } = get();
    const all = [
      ...scannersByCategory.technical,
      ...scannersByCategory.fundamental,
      ...scannersByCategory.plugin,
    ];
    return all.find((s) => s.name === scannerName);
  },

  addCriterion: (scannerName) => {
    const { builderCriteria, findScannerDef } = get();
    if (builderCriteria.some((c) => c.scanner_name === scannerName)) return;
    const def = findScannerDef(scannerName);
    const params: Record<string, number> = {};
    (def?.param_schema ?? []).forEach((p) => {
      if (p.default !== undefined) params[p.name] = p.default;
    });
    set({ builderCriteria: [...builderCriteria, { scanner_name: scannerName, params }] });
  },

  removeCriterion: (scannerName) => {
    set((s) => ({ builderCriteria: s.builderCriteria.filter((c) => c.scanner_name !== scannerName) }));
  },

  updateCriterionParam: (scannerName, paramName, value) => {
    set((s) => ({
      builderCriteria: s.builderCriteria.map((c) =>
        c.scanner_name === scannerName ? { ...c, params: { ...c.params, [paramName]: value } } : c
      ),
    }));
  },

  setBuilderUniverse: (universe) => set({ builderUniverse: universe }),

  loadComboIntoBuilder: (combo) => {
    set({
      builderCriteria: combo.criteria.map((c) => ({ ...c, params: { ...c.params } })),
      builderUniverse: combo.universe,
      builderExchange: combo.exchange,
      editingComboId: combo.id,
    });
  },

  resetBuilder: () => {
    set({ builderCriteria: [], builderUniverse: 'NIFTY 50', builderExchange: 'NSE', editingComboId: null });
  },

  saveCombo: async (name) => {
    const { builderCriteria, builderUniverse, builderExchange, editingComboId, savedCombos } = get();
    const body = { name, universe: builderUniverse, exchange: builderExchange, criteria: builderCriteria };
    const { data } = editingComboId
      ? await api.put(`/api/scan-combos/${editingComboId}`, body)
      : await api.post('/api/scan-combos', body);
    const exists = savedCombos.some((c) => c.id === data.id);
    set({
      savedCombos: exists
        ? savedCombos.map((c) => (c.id === data.id ? data : c))
        : [data, ...savedCombos],
      editingComboId: data.id,
    });
    return data;
  },

  deleteCombo: async (id) => {
    await api.delete(`/api/scan-combos/${id}`);
    set((s) => ({
      savedCombos: s.savedCombos.filter((c) => c.id !== id),
      editingComboId: s.editingComboId === id ? null : s.editingComboId,
    }));
  },

  runBuilderAdHoc: async () => {
    const { builderCriteria, builderUniverse, builderExchange } = get();
    set({ running: true });
    try {
      const { data } = await api.post('/api/scan-combos/run-ad-hoc', {
        universe: builderUniverse,
        exchange: builderExchange,
        criteria: builderCriteria,
      });
      return data as ComboRunResult;
    } finally {
      set({ running: false });
    }
  },

  runSavedCombo: async (id) => {
    set({ running: true });
    try {
      const { data } = await api.post(`/api/scan-combos/${id}/run`, {});
      return data as ComboRunResult;
    } finally {
      set({ running: false });
    }
  },
}));

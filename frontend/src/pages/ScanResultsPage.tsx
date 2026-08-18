// TICKR — Scan Results Page (Screen 3)
import { useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useChartStore } from '../store/chartStore';
import type { ComboRunResult } from '../types';
import api from '../api/client';

export default function ScanResultsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { setSymbol } = useChartStore();
  const [saveModal, setSaveModal] = useState(false);
  const [wlName, setWlName] = useState('');
  const [saving, setSaving] = useState(false);
  const [exporting, setExporting] = useState(false);

  const runResult = (location.state as { runResult?: ComboRunResult } | null)?.runResult;

  if (!runResult) {
    return (
      <div className="scanner-page">
        <div className="scanner-content">
          <p style={{ color: 'var(--text-muted)' }}>No scan results. <span style={{ color: 'var(--accent-red)', cursor: 'pointer' }} onClick={() => navigate('/scanner')}>Run a scan first →</span></p>
        </div>
      </div>
    );
  }

  const { combo_name, universe, run_at, criteria, match_count, per_criterion_counts, results: rows } = runResult;
  const title = combo_name || 'Ad-hoc scan';

  const handleRowClick = (sym: string) => {
    const clean = sym.replace('.NS', '').replace('.BSE', '');
    setSymbol(clean);
    navigate('/');
  };

  const handleSaveAs = async () => {
    if (!wlName.trim()) return;
    setSaving(true);
    try {
      await api.post('/api/scanners/save-as-watchlist', {
        name: wlName.trim(),
        symbols: rows.map((r) => r.symbol.replace('.NS', '')),
        exchange: 'NSE',
      });
      setSaveModal(false);
      alert(`Watchlist "${wlName}" created with ${rows.length} stocks.`);
    } catch { /* keep modal open on failure so the user can retry */ } finally { setSaving(false); }
  };

  const handleExport = async () => {
    setExporting(true);
    try {
      const res = await api.post(
        '/api/scan-combos/export',
        { combo_name, universe, exchange: runResult.exchange, criteria, run_at, results: rows },
        { responseType: 'blob' }
      );
      const blob = new Blob([res.data], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${(combo_name || 'adhoc_scan').replace(/[^A-Za-z0-9_-]+/g, '_')}_${run_at.slice(0, 10)}.xlsx`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch {
      alert('Export failed. Please try again.');
    } finally {
      setExporting(false);
    }
  };

  const extraCols = rows[0]
    ? Object.keys(rows[0]).filter((k) => !['symbol', 'exchange', 'price', 'change_pct', 'matched_criteria'].includes(k))
    : [];

  return (
    <div className="scanner-page">
      <div className="scanner-content" style={{ maxWidth: 900 }}>
        <div className="results-header">
          <h1 className="results-title">{title} · {universe}</h1>
          <div className="results-meta">
            Run {new Date(run_at).toLocaleString()} · {match_count} match{match_count !== 1 ? 'es' : ''}
            {criteria.length > 1 && (
              <> · {criteria.map((c) => `${c.scanner_name}: ${per_criterion_counts[c.scanner_name] ?? 0}`).join(', ')} before combining</>
            )}
          </div>
        </div>

        <table className="results-table" id="scan-results-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Price</th>
              <th>Change</th>
              {extraCols.map((k) => <th key={k}>{k.toUpperCase().replace(/_/g, ' ')}</th>)}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={i} onClick={() => handleRowClick(row.symbol)}>
                <td className="sym-cell">{row.symbol}</td>
                <td className="mono">{row.price?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                <td>
                  <span className={`change-badge ${row.change_pct >= 0 ? 'positive' : 'negative'}`}>
                    {row.change_pct >= 0 ? '+' : ''}{row.change_pct?.toFixed(2)}%
                  </span>
                </td>
                {extraCols.map((k) => {
                  const v = row[k];
                  return (
                    <td key={k} className="mono">
                      {typeof v === 'number' ? v.toLocaleString('en-IN', { minimumFractionDigits: 2 }) : String(v ?? '')}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>

        <div className="results-footer">
          Click a row to open it in the Chart terminal.
        </div>

        <div style={{ display: 'flex', gap: 10 }}>
          <button id="save-as-btn" className="btn-save-as" onClick={() => setSaveModal(true)}>
            Save as watchlist
          </button>
          <button id="export-excel-btn" className="btn-save-as" onClick={handleExport} disabled={exporting}>
            {exporting ? 'Exporting…' : 'Export to Excel'}
          </button>
        </div>

        {saveModal && (
          <div className="add-stock-modal">
            <div className="add-stock-card">
              <h3>Save as Watchlist</h3>
              <input
                autoFocus
                className="form-input"
                placeholder="Watchlist name..."
                value={wlName}
                onChange={(e) => setWlName(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSaveAs()}
              />
              <div className="modal-actions">
                <button className="btn-cancel" onClick={() => setSaveModal(false)}>Cancel</button>
                <button className="btn-confirm" onClick={handleSaveAs} disabled={saving}>
                  {saving ? 'Saving...' : 'Save'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

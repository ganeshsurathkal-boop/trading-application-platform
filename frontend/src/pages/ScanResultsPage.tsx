// TICKR — Scan Results Page (Screen 3)
import { useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { useChartStore } from '../store/chartStore';
import api from '../api/client';

export default function ScanResultsPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { setSymbol } = useChartStore();
  const [saveModal, setSaveModal] = useState(false);
  const [wlName, setWlName] = useState('');
  const [saving, setSaving] = useState(false);

  const { results, scanner, universe } = (location.state as any) || {};

  if (!results) {
    return (
      <div className="scanner-page">
        <div className="scanner-content">
          <p style={{ color: 'var(--text-muted)' }}>No scan results. <span style={{ color: 'var(--accent-red)', cursor: 'pointer' }} onClick={() => navigate('/scanner')}>Run a scan first →</span></p>
        </div>
      </div>
    );
  }

  const { match_count, run_at, results: rows } = results;

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
        symbols: rows.map((r: any) => r.symbol.replace('.NS', '')),
        exchange: 'NSE',
      });
      setSaveModal(false);
      alert(`Watchlist "${wlName}" created with ${rows.length} stocks.`);
    } catch { } finally { setSaving(false); }
  };

  return (
    <div className="scanner-page">
      <div className="scanner-content" style={{ maxWidth: 800 }}>
        <div className="results-header">
          <h1 className="results-title">{scanner} · {universe}</h1>
          <div className="results-meta">
            Run {run_at} IST · {match_count} match{match_count !== 1 ? 'es' : ''}
          </div>
        </div>

        <table className="results-table" id="scan-results-table">
          <thead>
            <tr>
              <th>Symbol</th>
              <th>Price</th>
              <th>Change</th>
              {rows[0] && Object.keys(rows[0])
                .filter((k) => !['symbol', 'exchange', 'price', 'change_pct'].includes(k))
                .map((k) => <th key={k}>{k.toUpperCase().replace(/_/g, ' ')}</th>)
              }
            </tr>
          </thead>
          <tbody>
            {rows.map((row: any, i: number) => (
              <tr key={i} onClick={() => handleRowClick(row.symbol)}>
                <td className="sym-cell">{row.symbol}</td>
                <td className="mono">{row.price?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                <td>
                  <span className={`change-badge ${row.change_pct >= 0 ? 'positive' : 'negative'}`}>
                    {row.change_pct >= 0 ? '+' : ''}{row.change_pct?.toFixed(2)}%
                  </span>
                </td>
                {Object.keys(row)
                  .filter((k) => !['symbol', 'exchange', 'price', 'change_pct'].includes(k))
                  .map((k) => (
                    <td key={k} className="mono">
                      {typeof row[k] === 'number'
                        ? row[k].toLocaleString('en-IN', { minimumFractionDigits: 2 })
                        : row[k]}
                    </td>
                  ))}
              </tr>
            ))}
          </tbody>
        </table>

        <div className="results-footer">
          Click a row to open it in the Chart terminal.
          {rows.length > 10 ? ` ${rows.length - 10} more rows not shown.` : ''}
        </div>

        <button id="save-as-btn" className="btn-save-as" onClick={() => setSaveModal(true)}>
          Save as watchlist
        </button>

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

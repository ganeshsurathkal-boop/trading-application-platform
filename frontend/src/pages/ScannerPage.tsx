// TICKR — Scanner Setup Page (Screen 2)
import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../api/client';

interface ScannerDef {
  name: string;
  description: string;
  category: string;
}

interface ScannersByCategory {
  technical: ScannerDef[];
  fundamental: ScannerDef[];
  plugin: ScannerDef[];
}

const UNIVERSES = ['NIFTY 50', 'NIFTY NEXT 50', 'NIFTY 500', 'NIFTY 1000'];

export default function ScannerPage() {
  const navigate = useNavigate();
  const [scanners, setScanners] = useState<ScannersByCategory>({ technical: [], fundamental: [], plugin: [] });
  const [selectedScanners, setSelectedScanners] = useState<string[]>([]);
  const [universe, setUniverse] = useState('NIFTY 50');
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get('/api/scanners')
      .then(({ data }) => { setScanners(data.scanners); setLoading(false); })
      .catch(() => setLoading(false));
  }, []);

  const toggleScanner = (name: string) => {
    setSelectedScanners((prev) =>
      prev.includes(name) ? prev.filter((s) => s !== name) : [...prev, name]
    );
  };

  const handleRun = async () => {
    if (selectedScanners.length === 0) return;
    setRunning(true);
    try {
      const scanner = selectedScanners[0]; // Run first selected scanner
      const { data } = await api.post(`/api/scanners/${encodeURIComponent(scanner)}/run`, {
        universe,
        exchange: 'NSE',
        params: {},
      });
      navigate('/results', { state: { results: data, scanner, universe } });
    } catch (e) {
      console.error(e);
    } finally {
      setRunning(false);
    }
  };

  const renderCategory = (label: string, items: ScannerDef[], category: string) => (
    <div className="scan-criteria-row" key={category}>
      <span className="scan-criteria-name">{label}</span>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {items.length === 0 ? (
          <span className="scan-badge inactive">none installed</span>
        ) : (
          items.map((s) => (
            <span
              key={s.name}
              id={`scanner-${s.name.replace(/\s/g, '-')}`}
              className={`scan-badge ${selectedScanners.includes(s.name) ? '' : 'inactive'}`}
              style={{ cursor: 'pointer' }}
              onClick={() => toggleScanner(s.name)}
              title={s.description}
            >
              {s.name}
            </span>
          ))
        )}
      </div>
      {items.length > 0 && (
        <span className="scan-badge" style={{ marginLeft: 'auto' }}>
          {selectedScanners.filter((n) => items.map((i) => i.name).includes(n)).length} active
        </span>
      )}
    </div>
  );

  return (
    <div className="scanner-page">
      <div className="scanner-content">
        <h1 className="scanner-title">Scan criteria</h1>

        <div style={{ marginBottom: 16 }}>
          <label style={{ fontSize: 12, color: 'var(--text-muted)', display: 'block', marginBottom: 6 }}>
            Universe
          </label>
          <select
            id="universe-select"
            className="universe-select"
            value={universe}
            onChange={(e) => setUniverse(e.target.value)}
          >
            {UNIVERSES.map((u) => <option key={u} value={u}>{u}</option>)}
          </select>
        </div>

        <div className="scan-criteria-list">
          {loading ? (
            <div className="spinner" style={{ padding: 32 }}>
              <div className="spin" /> Loading scanners...
            </div>
          ) : (
            <>
              {renderCategory('Technical scans', scanners.technical, 'technical')}
              {renderCategory('Fundamental scans', scanners.fundamental, 'fundamental')}
              {renderCategory('Plugin scans', scanners.plugin, 'plugin')}
            </>
          )}
        </div>

        <button
          id="run-scan-btn"
          className="btn-run-scan"
          onClick={handleRun}
          disabled={selectedScanners.length === 0 || running}
        >
          {running ? 'Running...' : `Run scan (${selectedScanners.length} selected)`}
        </button>
      </div>
    </div>
  );
}

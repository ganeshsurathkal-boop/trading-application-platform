// TICKR — Data Management Panel
// Provides UI for: Kite Connect OAuth, bulk download, Bhav Copy upload, and gap fill.
import { useState, useEffect, useRef, useCallback } from 'react';
import api from '../../api/client';

// ── Types ──────────────────────────────────────────────────────────────────────

interface KiteStatus {
  connected: boolean;
  has_api_key: boolean;
  has_access_token: boolean;
  mode: 'mock' | 'live' | 'disconnected';
  bulk_download: BulkProgress;
}

interface BulkProgress {
  running: boolean;
  done: number;
  total: number;
  current_symbol: string;
  pct: number;
  errors: string[];
}

interface GapInfo {
  missing_count: number;
  missing_dates: string[];
}

interface UploadResult {
  success: boolean;
  trading_date: string | null;
  symbols_updated: number;
  symbols_skipped: number;
  gaps_detected: number;
  gap_dates: string[];
  message: string;
}

interface BhavHistoryEntry {
  date: string;
  symbol_count: number;
}

// ── Main component ─────────────────────────────────────────────────────────────

export default function DataManagementPanel() {
  const [kiteStatus, setKiteStatus] = useState<KiteStatus | null>(null);
  const [gaps, setGaps] = useState<GapInfo | null>(null);
  const [bhavHistory, setBhavHistory] = useState<BhavHistoryEntry[]>([]);
  const [uploadResult, setUploadResult] = useState<UploadResult | null>(null);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isFillLoading, setIsFillLoading] = useState(false);
  const [fillResult, setFillResult] = useState<any>(null);
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // ── Load initial data ────────────────────────────────────────────────────────

  const loadKiteStatus = useCallback(async () => {
    try {
      const res = await api.get<KiteStatus>('/api/kite/status');
      setKiteStatus(res.data);
    } catch { /* silently fail */ }
  }, []);

  const loadGaps = useCallback(async () => {
    try {
      const res = await api.get<GapInfo>('/api/bhav/gaps?lookback_days=30');
      setGaps(res.data);
    } catch { /* silently fail */ }
  }, []);

  const loadHistory = useCallback(async () => {
    try {
      const res = await api.get<{ history: BhavHistoryEntry[] }>('/api/bhav/history?limit=5');
      setBhavHistory(res.data.history);
    } catch { /* silently fail */ }
  }, []);

  useEffect(() => {
    loadKiteStatus();
    loadGaps();
    loadHistory();
  }, [loadKiteStatus, loadGaps, loadHistory]);

  // ── Poll bulk download progress ───────────────────────────────────────────────

  useEffect(() => {
    if (kiteStatus?.bulk_download.running) {
      pollRef.current = setInterval(async () => {
        await loadKiteStatus();
      }, 2000);
    } else {
      if (pollRef.current) {
        clearInterval(pollRef.current);
        pollRef.current = null;
      }
    }
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, [kiteStatus?.bulk_download.running, loadKiteStatus]);

  // ── Toast helper ──────────────────────────────────────────────────────────────

  const showToast = (msg: string, type: 'success' | 'error') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  // ── Kite OAuth ────────────────────────────────────────────────────────────────

  const handleKiteConnect = async () => {
    try {
      const res = await api.get<{ login_url: string }>('/api/kite/login-url');
      window.location.href = res.data.login_url;
    } catch (e: any) {
      showToast(e.response?.data?.detail || 'Failed to get Kite login URL', 'error');
    }
  };

  const handleKiteDisconnect = async () => {
    if (!confirm('Disconnect from Zerodha Kite Connect? You will need to re-authenticate to use live data.')) return;
    try {
      await api.delete('/api/kite/session');
      showToast('Disconnected from Kite Connect.', 'success');
      await loadKiteStatus();
    } catch (e: any) {
      showToast(e.response?.data?.detail || 'Failed to disconnect', 'error');
    }
  };

  // ── Bulk download ─────────────────────────────────────────────────────────────

  const handleBulkDownload = async () => {
    try {
      await api.post('/api/kite/bulk-download');
      showToast('Bulk download started! This may take several minutes.', 'success');
      await loadKiteStatus();
    } catch (e: any) {
      showToast(e.response?.data?.detail || 'Failed to start bulk download', 'error');
    }
  };

  const handleCancelDownload = async () => {
    try {
      await api.delete('/api/kite/bulk-download');
      showToast('Cancellation requested — download will stop shortly.', 'success');
    } catch (e: any) {
      showToast(e.response?.data?.detail || 'Failed to cancel download', 'error');
    }
  };

  // ── Bhav Copy upload ──────────────────────────────────────────────────────────

  const handleFileUpload = async (file: File) => {
    setIsUploading(true);
    setUploadResult(null);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const res = await api.post<UploadResult>('/api/bhav/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      setUploadResult(res.data);
      showToast(`✓ ${res.data.message}`, 'success');
      await Promise.all([loadGaps(), loadHistory()]);
    } catch (e: any) {
      const detail = e.response?.data?.detail || 'Upload failed';
      showToast(detail, 'error');
    } finally {
      setIsUploading(false);
    }
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleFileUpload(file);
    e.target.value = '';
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFileUpload(file);
  };

  // ── Gap fill ──────────────────────────────────────────────────────────────────

  const handleFillGaps = async () => {
    setIsFillLoading(true);
    setFillResult(null);
    try {
      const res = await api.post('/api/bhav/fill-gaps?lookback_days=30');
      setFillResult(res.data);
      showToast(res.data.message, 'success');
      await loadGaps();
    } catch (e: any) {
      showToast(e.response?.data?.detail || 'Gap fill failed', 'error');
    } finally {
      setIsFillLoading(false);
    }
  };

  // ── Render helpers ────────────────────────────────────────────────────────────

  const bulk = kiteStatus?.bulk_download;

  return (
    <div className="data-mgmt-panel">

      {/* Toast */}
      {toast && (
        <div className={`dm-toast dm-toast--${toast.type}`}>{toast.msg}</div>
      )}

      {/* ── Section 1: Kite Connect ───────────────────────────────────────── */}
      <div className="dm-section">
        <div className="dm-section-header">
          <span className="dm-section-icon">🔌</span>
          <span className="dm-section-title">Kite Connect</span>
          <span className={`dm-badge ${kiteStatus?.connected ? 'dm-badge--live' : kiteStatus?.mode === 'mock' ? 'dm-badge--mock' : 'dm-badge--off'}`}>
            {kiteStatus?.connected ? 'Connected' : kiteStatus?.mode === 'mock' ? 'Mock Mode' : 'Disconnected'}
          </span>
        </div>

        {!kiteStatus?.has_api_key ? (
          <div className="dm-notice dm-notice--warn">
            <strong>API key not configured.</strong>
            <br />
            Add <code>KITE_API_KEY</code> and <code>KITE_API_SECRET</code> to <code>backend/.env</code> to enable live data.
          </div>
        ) : kiteStatus?.connected ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 8 }}>
            <span style={{ fontSize: 13, color: 'var(--text-secondary)' }}>
              ✓ Live data active
            </span>
            <button
              id="kite-disconnect-btn"
              className="dm-btn dm-btn--danger"
              onClick={handleKiteDisconnect}
              style={{ padding: '4px 12px', fontSize: 12 }}
            >
              Disconnect
            </button>
          </div>
        ) : (
          <button id="kite-connect-btn" className="dm-btn dm-btn--primary" onClick={handleKiteConnect}>
            Connect to Zerodha Kite →
          </button>
        )}

        {/* Bulk download section */}
        <div className="dm-subsection">
          <div className="dm-subsection-label">One-Time Historical Download</div>
          <div className="dm-desc">
            Downloads 5 years of daily OHLCV data for all NSE mainboard equity symbols (~1,800 stocks). Run this once after connecting.
          </div>

          {bulk?.running ? (
            <div className="dm-progress-wrap">
              <div className="dm-progress-info">
                <span className="dm-progress-symbol">{bulk.current_symbol}</span>
                <span className="dm-progress-count">{bulk.done.toLocaleString()} / {bulk.total.toLocaleString()}</span>
              </div>
              <div className="dm-progress-bar">
                <div className="dm-progress-fill" style={{ width: `${bulk.pct}%` }} />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 6 }}>
                <span className="dm-progress-pct">{bulk.pct}% complete</span>
                <button
                  id="cancel-download-btn"
                  className="dm-btn dm-btn--danger"
                  onClick={handleCancelDownload}
                  style={{ padding: '3px 10px', fontSize: 11 }}
                >
                  ✕ Cancel
                </button>
              </div>
            </div>
          ) : (
            <button
              id="bulk-download-btn"
              className="dm-btn dm-btn--secondary"
              onClick={handleBulkDownload}
              disabled={!kiteStatus?.connected}
            >
              ⬇ Start Bulk Download
            </button>
          )}

          {bulk && !bulk.running && bulk.done > 0 && (
            <div className="dm-notice dm-notice--success">
              ✓ Last download: {bulk.done.toLocaleString()} symbols processed
              {bulk.errors.length > 0 && ` (${bulk.errors.length} errors)`}
            </div>
          )}

        </div>
      </div>

      {/* ── Section 2: Bhav Copy Upload ───────────────────────────────────── */}
      <div className="dm-section">
        <div className="dm-section-header">
          <span className="dm-section-icon">📄</span>
          <span className="dm-section-title">Bhav Copy Upload</span>
        </div>

        <div className="dm-desc">
          Download the NSE Bhav Copy from{' '}
          <a href="https://nsearchives.nseindia.com/products/content/" target="_blank" rel="noreferrer" className="dm-link">
            nsearchives.nseindia.com
          </a>{' '}
          and upload it here. Supports <code>.csv</code> and <code>.zip</code> files.
        </div>

        {/* Recent history */}
        {bhavHistory.length > 0 && (
          <div className="dm-history">
            {bhavHistory.map((h) => (
              <div key={h.date} className="dm-history-row">
                <span className="dm-history-check">✓</span>
                <span className="dm-history-date">{h.date}</span>
                <span className="dm-history-count">{h.symbol_count.toLocaleString()} symbols</span>
              </div>
            ))}
          </div>
        )}

        {/* Gap warning */}
        {gaps && gaps.missing_count > 0 && (
          <div className="dm-notice dm-notice--warn">
            <strong>⚠ {gaps.missing_count} missing trading day{gaps.missing_count > 1 ? 's' : ''} detected</strong>
            <div className="dm-gap-dates">
              {gaps.missing_dates.slice(0, 5).map(d => (
                <span key={d} className="dm-gap-chip">{d}</span>
              ))}
              {gaps.missing_dates.length > 5 && <span className="dm-gap-chip">+{gaps.missing_dates.length - 5} more</span>}
            </div>
            <button
              id="fill-gaps-btn"
              className="dm-btn dm-btn--danger"
              onClick={handleFillGaps}
              disabled={isFillLoading || !kiteStatus?.connected}
              style={{ marginTop: 8 }}
            >
              {isFillLoading ? 'Filling gaps…' : 'Fill gaps from Kite Connect'}
            </button>
            {!kiteStatus?.connected && (
              <div style={{ fontSize: 11, color: 'var(--text-muted)', marginTop: 4 }}>
                Connect to Kite first to enable gap fill.
              </div>
            )}
          </div>
        )}

        {gaps && gaps.missing_count === 0 && (
          <div className="dm-notice dm-notice--success">✓ DB is up to date — no missing trading days</div>
        )}

        {fillResult && (
          <div className="dm-notice dm-notice--success">
            ✓ Filled {fillResult.days_processed} day(s) for {fillResult.symbols_filled} symbols
          </div>
        )}

        {/* Drop zone */}
        <div
          className={`dm-dropzone ${isDragging ? 'dm-dropzone--drag' : ''} ${isUploading ? 'dm-dropzone--uploading' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={onDrop}
          onClick={() => !isUploading && fileInputRef.current?.click()}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".csv,.zip"
            onChange={onFileChange}
            style={{ display: 'none' }}
            id="bhav-file-input"
          />
          {isUploading ? (
            <div className="dm-dropzone-inner">
              <div className="dm-spinner" />
              <span>Processing Bhav Copy…</span>
            </div>
          ) : (
            <div className="dm-dropzone-inner">
              <span className="dm-dropzone-icon">📂</span>
              <span className="dm-dropzone-text">Drag & drop Bhav Copy here</span>
              <span className="dm-dropzone-hint">or click to browse · .csv or .zip</span>
            </div>
          )}
        </div>

        {/* Upload result */}
        {uploadResult && uploadResult.success && (
          <div className="dm-notice dm-notice--success">
            <strong>✓ {uploadResult.trading_date}</strong> — {uploadResult.symbols_updated.toLocaleString()} symbols updated
            {uploadResult.symbols_skipped > 0 && `, ${uploadResult.symbols_skipped} skipped`}
            {uploadResult.gaps_detected > 0 && (
              <div style={{ marginTop: 4, color: 'var(--text-secondary)' }}>
                {uploadResult.gaps_detected} gap day{uploadResult.gaps_detected > 1 ? 's' : ''} detected after upload.
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

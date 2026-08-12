// TICKR — Admin: Plugin Management (indicators & scanners)
import { useState, useEffect, useCallback, useRef } from 'react';
import api from '../api/client';

interface Plugin {
  id: number;
  name: string;
  type: 'indicator' | 'scanner';
  version: string;
  description: string | null;
  author: string | null;
  enabled: boolean;
  installed_at: string | null;
}

type Tab = 'indicator' | 'scanner';

export default function AdminPluginsPage() {
  const [tab, setTab] = useState<Tab>('indicator');
  const [plugins, setPlugins] = useState<Plugin[]>([]);
  const [loading, setLoading] = useState(true);
  const [isUploading, setIsUploading] = useState(false);
  const [isDragging, setIsDragging] = useState(false);
  const [toast, setToast] = useState<{ msg: string; type: 'success' | 'error' } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const showToast = (msg: string, type: 'success' | 'error') => {
    setToast({ msg, type });
    setTimeout(() => setToast(null), 4000);
  };

  const loadPlugins = useCallback(async () => {
    try {
      const { data } = await api.get('/api/admin/plugins');
      setPlugins(data.plugins);
    } catch {
      showToast('Failed to load plugins', 'error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadPlugins(); }, [loadPlugins]);

  const handleUpload = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.zip')) {
      showToast('Plugins must be uploaded as a .zip file', 'error');
      return;
    }
    setIsUploading(true);
    const formData = new FormData();
    formData.append('file', file);
    try {
      const { data } = await api.post('/api/admin/plugins/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      showToast(`Installed ${data.plugin.name} v${data.plugin.version}`, 'success');
      setTab(data.plugin.type);
      await loadPlugins();
    } catch (e: any) {
      showToast(e.response?.data?.detail || 'Upload failed', 'error');
    } finally {
      setIsUploading(false);
    }
  };

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) handleUpload(file);
    e.target.value = '';
  };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleUpload(file);
  };

  const toggleEnabled = async (p: Plugin) => {
    try {
      await api.post(`/api/admin/plugins/${p.id}/${p.enabled ? 'disable' : 'enable'}`);
      showToast(`${p.name} ${p.enabled ? 'disabled' : 'enabled'}`, 'success');
      await loadPlugins();
    } catch (e: any) {
      showToast(e.response?.data?.detail || 'Failed to update plugin', 'error');
    }
  };

  const deletePlugin = async (p: Plugin) => {
    if (!confirm(`Uninstall "${p.name}"? This removes its code from disk — it can be reinstalled later by re-uploading the .zip.`)) return;
    try {
      await api.delete(`/api/admin/plugins/${p.id}`);
      showToast(`${p.name} uninstalled`, 'success');
      await loadPlugins();
    } catch (e: any) {
      showToast(e.response?.data?.detail || 'Failed to uninstall plugin', 'error');
    }
  };

  const filtered = plugins.filter((p) => p.type === tab);

  return (
    <div className="scanner-page">
      <div className="scanner-content" style={{ maxWidth: 720 }}>
        <h1 className="scanner-title">Plugin management</h1>

        {toast && <div className={`dm-toast dm-toast--${toast.type}`}>{toast.msg}</div>}

        <div className="dm-notice dm-notice--warn" style={{ marginBottom: 20 }}>
          <strong>Installing a plugin runs its code with full server privileges.</strong> There
          is no sandboxing — only install plugins you wrote yourself or fully trust.
        </div>

        {/* Tabs */}
        <div className="watchlist-tabs" style={{ marginBottom: 16 }}>
          <div
            className={`watchlist-tab ${tab === 'indicator' ? 'active' : ''}`}
            onClick={() => setTab('indicator')}
          >Indicators</div>
          <div
            className={`watchlist-tab ${tab === 'scanner' ? 'active' : ''}`}
            onClick={() => setTab('scanner')}
          >Scanners</div>
        </div>

        {/* Upload */}
        <div
          className={`dm-dropzone ${isDragging ? 'dm-dropzone--drag' : ''} ${isUploading ? 'dm-dropzone--uploading' : ''}`}
          onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
          onDragLeave={() => setIsDragging(false)}
          onDrop={onDrop}
          onClick={() => !isUploading && fileInputRef.current?.click()}
          style={{ marginBottom: 24 }}
        >
          <input
            ref={fileInputRef}
            type="file"
            accept=".zip"
            onChange={onFileChange}
            style={{ display: 'none' }}
            id="plugin-file-input"
          />
          {isUploading ? (
            <div className="dm-dropzone-inner">
              <div className="dm-spinner" />
              <span>Installing plugin…</span>
            </div>
          ) : (
            <div className="dm-dropzone-inner">
              <span className="dm-dropzone-icon">🔌</span>
              <span className="dm-dropzone-text">Drag &amp; drop a plugin .zip here</span>
              <span className="dm-dropzone-hint">or click to browse — built with plugin-dev/build.py</span>
            </div>
          )}
        </div>

        {/* List */}
        {loading ? (
          <div className="spinner" style={{ padding: 32 }}>
            <div className="spin" /> Loading plugins...
          </div>
        ) : filtered.length === 0 ? (
          <div style={{ padding: 20, textAlign: 'center', fontSize: 13, color: 'var(--text-muted)' }}>
            No {tab === 'indicator' ? 'indicator' : 'scanner'} plugins installed yet.
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {filtered.map((p) => (
              <div
                key={p.id}
                id={`plugin-row-${p.name}`}
                style={{
                  display: 'flex', alignItems: 'center', gap: 12,
                  padding: '12px 14px', border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-sm)', background: 'var(--bg-surface)',
                  opacity: p.enabled ? 1 : 0.55,
                }}
              >
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontWeight: 600, fontSize: 13 }}>{p.name}</span>
                    <span style={{ fontSize: 11, color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>v{p.version}</span>
                    {p.author && <span style={{ fontSize: 11, color: 'var(--text-muted)' }}>by {p.author}</span>}
                  </div>
                  {p.description && (
                    <div style={{ fontSize: 12, color: 'var(--text-secondary)', marginTop: 2 }}>{p.description}</div>
                  )}
                </div>

                <button
                  id={`plugin-toggle-${p.name}`}
                  className="dm-btn dm-btn--secondary"
                  onClick={() => toggleEnabled(p)}
                  style={{ padding: '5px 12px', fontSize: 12, width: 'auto', flexShrink: 0 }}
                >
                  {p.enabled ? 'Disable' : 'Enable'}
                </button>
                <button
                  id={`plugin-delete-${p.name}`}
                  className="dm-btn dm-btn--danger"
                  onClick={() => deletePlugin(p)}
                  style={{ padding: '5px 12px', fontSize: 12, width: 'auto', flexShrink: 0 }}
                >
                  Uninstall
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

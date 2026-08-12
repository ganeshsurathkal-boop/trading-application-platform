// TICKR — Watchlist Panel (right sidebar)
import { useState, useEffect, useRef, useCallback } from 'react';
import { useWatchlistStore } from '../../store/watchlistStore';
import { useChartStore } from '../../store/chartStore';
import api from '../../api/client';

export default function WatchlistPanel() {
  const { watchlists, activeWatchlistId, fetchWatchlists, createWatchlist, addStock, removeStock, setActive } = useWatchlistStore();
  const { setSymbol, symbol } = useChartStore();
  const [showAddStock, setShowAddStock] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [showNewWL, setShowNewWL] = useState(false);
  const [newWLName, setNewWLName] = useState('');

  // Autocomplete state
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [selectedIdx, setSelectedIdx] = useState(-1);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const dropdownRef = useRef<HTMLDivElement>(null);

  useEffect(() => { fetchWatchlists(); }, []);

  const activeWL = watchlists.find((w) => w.id === activeWatchlistId);

  // Debounced symbol search
  const searchSymbols = useCallback(async (q: string) => {
    if (q.length < 1) { setSuggestions([]); setShowDropdown(false); return; }
    try {
      const { data } = await api.get('/api/candles/search', { params: { q: q.toUpperCase() } });
      setSuggestions(data.symbols ?? []);
      setShowDropdown((data.symbols ?? []).length > 0);
      setSelectedIdx(-1);
    } catch {
      setSuggestions([]);
      setShowDropdown(false);
    }
  }, []);

  const handleSymbolInput = (val: string) => {
    setNewSymbol(val);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => searchSymbols(val), 280);
  };

  const pickSuggestion = (sym: string) => {
    setNewSymbol(sym);
    setSuggestions([]);
    setShowDropdown(false);
    inputRef.current?.focus();
  };

  const handleAddStock = async () => {
    if (!newSymbol.trim() || !activeWatchlistId) return;
    await addStock(activeWatchlistId, newSymbol.trim().toUpperCase());
    setNewSymbol('');
    setSuggestions([]);
    setShowDropdown(false);
    setShowAddStock(false);
  };

  const handleInputKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIdx((i) => Math.min(i + 1, suggestions.length - 1));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIdx((i) => Math.max(i - 1, -1));
    } else if (e.key === 'Enter') {
      if (selectedIdx >= 0 && suggestions[selectedIdx]) {
        pickSuggestion(suggestions[selectedIdx]);
      } else {
        handleAddStock();
      }
    } else if (e.key === 'Escape') {
      setShowDropdown(false);
    }
  };

  const handleCreateWL = async () => {
    if (!newWLName.trim()) return;
    await createWatchlist(newWLName.trim());
    setNewWLName('');
    setShowNewWL(false);
  };

  return (
    <div className="watchlist-panel">
      {/* Tabs */}
      <div className="watchlist-tabs">
        {watchlists.map((wl) => (
          <div
            key={wl.id}
            id={`watchlist-tab-${wl.id}`}
            className={`watchlist-tab ${wl.id === activeWatchlistId ? 'active' : ''}`}
            onClick={() => setActive(wl.id)}
          >
            {wl.name}
          </div>
        ))}
        <button
          id="add-watchlist-btn"
          className="watchlist-add-tab"
          onClick={() => setShowNewWL(true)}
          title="Add new watchlist"
        >+</button>
      </div>

      {/* New watchlist input */}
      {showNewWL && (
        <div className="watchlist-search" style={{ display: 'flex', gap: 4 }}>
          <input
            autoFocus
            placeholder="Watchlist name..."
            value={newWLName}
            onChange={(e) => setNewWLName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreateWL()}
            style={{ flex: 1, padding: '6px 8px', fontSize: 12, border: '1px solid var(--border-strong)', borderRadius: 'var(--radius-sm)', outline: 'none' }}
          />
          <button
            onClick={handleCreateWL}
            style={{ padding: '6px 10px', background: 'var(--accent-red)', color: 'white', border: 'none', borderRadius: 'var(--radius-sm)', fontSize: 12, cursor: 'pointer' }}
          >Add</button>
          <button
            onClick={() => setShowNewWL(false)}
            style={{ padding: '6px 8px', background: 'transparent', border: '1px solid var(--border-strong)', borderRadius: 'var(--radius-sm)', fontSize: 12, cursor: 'pointer' }}
          >✕</button>
        </div>
      )}

      {/* Column headers */}
      <div style={{ display: 'flex', padding: '6px 14px', borderBottom: '1px solid var(--border)', fontSize: 10, fontWeight: 600, letterSpacing: '0.06em', textTransform: 'uppercase', color: 'var(--text-muted)' }}>
        <span style={{ flex: 1 }}>Symbol</span>
        <span style={{ marginRight: 8 }}>Price</span>
        <span style={{ minWidth: 50, textAlign: 'right' }}>Chg%</span>
      </div>

      {/* Stock list */}
      <div className="watchlist-stocks">
        {(activeWL?.stocks || []).map((stock) => (
          <StockRow
            key={stock.symbol}
            symbol={stock.symbol}
            isActive={symbol === stock.symbol}
            onClick={() => setSymbol(stock.symbol)}
            onRemove={() => activeWatchlistId && removeStock(activeWatchlistId, stock.symbol)}
          />
        ))}
        {(!activeWL || activeWL.stocks.length === 0) && (
          <div style={{ padding: 20, textAlign: 'center', fontSize: 12, color: 'var(--text-muted)' }}>
            No stocks yet. Add one below.
          </div>
        )}
      </div>

      {/* Footer — Add stock with autocomplete */}
      <div className="watchlist-footer">
        {showAddStock ? (
          <div style={{ position: 'relative' }}>
            <div style={{ display: 'flex', gap: 4 }}>
              <input
                ref={inputRef}
                autoFocus
                placeholder="Type symbol (e.g. RELI…)"
                value={newSymbol}
                onChange={(e) => handleSymbolInput(e.target.value)}
                onKeyDown={handleInputKeyDown}
                onBlur={() => setTimeout(() => setShowDropdown(false), 150)}
                style={{
                  flex: 1, padding: '6px 8px', fontSize: 12,
                  border: '1px solid var(--border-strong)',
                  borderRadius: showDropdown ? 'var(--radius-sm) var(--radius-sm) 0 0' : 'var(--radius-sm)',
                  outline: 'none', textTransform: 'uppercase',
                }}
              />
              <button
                onClick={handleAddStock}
                style={{ padding: '6px 10px', background: 'var(--accent-red)', color: 'white', border: 'none', borderRadius: 'var(--radius-sm)', fontSize: 12, cursor: 'pointer' }}
              >Add</button>
              <button
                onClick={() => { setShowAddStock(false); setNewSymbol(''); setShowDropdown(false); }}
                style={{ padding: '6px 8px', background: 'transparent', border: '1px solid var(--border-strong)', borderRadius: 'var(--radius-sm)', fontSize: 12, cursor: 'pointer' }}
              >✕</button>
            </div>

            {/* Autocomplete dropdown */}
            {showDropdown && suggestions.length > 0 && (
              <div
                ref={dropdownRef}
                style={{
                  position: 'absolute',
                  top: '100%',
                  left: 0,
                  right: 0,
                  zIndex: 100,
                  background: 'var(--bg-panel, #fff)',
                  border: '1px solid var(--border-strong)',
                  borderTop: 'none',
                  borderRadius: '0 0 var(--radius-sm) var(--radius-sm)',
                  maxHeight: 200,
                  overflowY: 'auto',
                  boxShadow: '0 4px 12px rgba(0,0,0,0.12)',
                }}
              >
                {suggestions.map((sym, i) => (
                  <div
                    key={sym}
                    onMouseDown={() => pickSuggestion(sym)}
                    style={{
                      padding: '7px 10px',
                      fontSize: 12,
                      fontWeight: 500,
                      cursor: 'pointer',
                      letterSpacing: '0.03em',
                      background: i === selectedIdx ? 'var(--accent-red, #C0392B)' : 'transparent',
                      color: i === selectedIdx ? '#fff' : 'var(--text-primary)',
                      transition: 'background 0.1s',
                    }}
                    onMouseEnter={() => setSelectedIdx(i)}
                  >
                    {sym}
                    <span style={{ marginLeft: 6, fontSize: 10, opacity: 0.5, fontWeight: 400 }}>NSE</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ) : (
          <button id="add-stock-btn" className="btn-add-stock" onClick={() => setShowAddStock(true)}>
            + Add stock
          </button>
        )}
      </div>
    </div>
  );
}

function StockRow({ symbol, isActive, onClick, onRemove }: {
  symbol: string; isActive: boolean; onClick: () => void; onRemove: () => void;
}) {
  const [hovered, setHovered] = useState(false);
  const changePct = (Math.random() * 6 - 3).toFixed(2); // Placeholder until live price feed
  const isPos = parseFloat(changePct) >= 0;

  return (
    <div
      className={`stock-row ${isActive ? 'active' : ''}`}
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{ position: 'relative' }}
    >
      <span className="stock-row-symbol">{symbol}.NS</span>
      <span className="stock-row-price" style={{ fontSize: 11 }}>—</span>
      {hovered ? (
        <button
          title="Remove from watchlist"
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
          style={{
            background: 'transparent',
            border: 'none',
            cursor: 'pointer',
            color: 'var(--accent-red, #C0392B)',
            fontSize: 13,
            fontWeight: 700,
            padding: '0 4px',
            minWidth: 50,
            textAlign: 'right',
            lineHeight: 1,
          }}
        >✕</button>
      ) : (
        <span className={`stock-row-change ${isPos ? 'positive' : 'negative'}`}>
          {isPos ? '+' : ''}{changePct}%
        </span>
      )}
    </div>
  );
}

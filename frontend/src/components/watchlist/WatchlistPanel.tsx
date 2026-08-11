// TICKR — Watchlist Panel (right sidebar)
import { useState, useEffect } from 'react';
import { useWatchlistStore } from '../../store/watchlistStore';
import { useChartStore } from '../../store/chartStore';

export default function WatchlistPanel() {
  const { watchlists, activeWatchlistId, fetchWatchlists, createWatchlist, addStock, removeStock, setActive } = useWatchlistStore();
  const { setSymbol, symbol } = useChartStore();
  const [showAddStock, setShowAddStock] = useState(false);
  const [newSymbol, setNewSymbol] = useState('');
  const [showNewWL, setShowNewWL] = useState(false);
  const [newWLName, setNewWLName] = useState('');

  useEffect(() => { fetchWatchlists(); }, []);

  const activeWL = watchlists.find((w) => w.id === activeWatchlistId);

  const handleAddStock = async () => {
    if (!newSymbol.trim() || !activeWatchlistId) return;
    await addStock(activeWatchlistId, newSymbol.trim().toUpperCase());
    setNewSymbol('');
    setShowAddStock(false);
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

      {/* Footer */}
      <div className="watchlist-footer">
        {showAddStock ? (
          <div style={{ display: 'flex', gap: 4 }}>
            <input
              autoFocus
              placeholder="Symbol (e.g. RELIANCE)"
              value={newSymbol}
              onChange={(e) => setNewSymbol(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAddStock()}
              style={{ flex: 1, padding: '6px 8px', fontSize: 12, border: '1px solid var(--border-strong)', borderRadius: 'var(--radius-sm)', outline: 'none', textTransform: 'uppercase' }}
            />
            <button onClick={handleAddStock} style={{ padding: '6px 10px', background: 'var(--accent-red)', color: 'white', border: 'none', borderRadius: 'var(--radius-sm)', fontSize: 12, cursor: 'pointer' }}>Add</button>
            <button onClick={() => setShowAddStock(false)} style={{ padding: '6px 8px', background: 'transparent', border: '1px solid var(--border-strong)', borderRadius: 'var(--radius-sm)', fontSize: 12, cursor: 'pointer' }}>✕</button>
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

function StockRow({ symbol, isActive, onClick, onRemove: _onRemove }: {
  symbol: string; isActive: boolean; onClick: () => void; onRemove: () => void;
}) {
  const changePct = (Math.random() * 6 - 3).toFixed(2); // Placeholder until live price feed
  const isPos = parseFloat(changePct) >= 0;

  return (
    <div className={`stock-row ${isActive ? 'active' : ''}`} onClick={onClick}>
      <span className="stock-row-symbol">{symbol}.NS</span>
      <span className="stock-row-price" style={{ fontSize: 11 }}>—</span>
      <span className={`stock-row-change ${isPos ? 'positive' : 'negative'}`}>
        {isPos ? '+' : ''}{changePct}%
      </span>
    </div>
  );
}

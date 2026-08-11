// TICKR — Indicator dropdown and pill bar
import { useState, useRef, useEffect } from 'react';
import { useChartStore } from '../../store/chartStore';

export default function IndicatorBar() {
  const { availableIndicators, activeIndicators, addIndicator, removeIndicator } = useChartStore();
  const [open, setOpen] = useState(false);
  const dropRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropRef.current && !dropRef.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const overlays = availableIndicators.filter((i) => i.overlay);
  const subCharts = availableIndicators.filter((i) => !i.overlay);

  return (
    <div className="indicator-bar">
      {activeIndicators.map((ind) => (
        <div key={ind.id} className="indicator-pill">
          {ind.label}
          <button
            className="remove-btn"
            onClick={() => removeIndicator(ind.id)}
            title={`Remove ${ind.label}`}
          >×</button>
        </div>
      ))}

      <div className="indicator-dropdown" ref={dropRef}>
        <button
          id="add-indicator-btn"
          className="add-indicator-btn"
          onClick={() => setOpen((o) => !o)}
        >
          + Indicator
        </button>

        {open && (
          <div className="indicator-dropdown-menu">
            {overlays.length > 0 && (
              <>
                <div className="dropdown-section-label">On Chart</div>
                {overlays.map((ind) => (
                  <div
                    key={ind.name}
                    className="dropdown-item"
                    id={`indicator-${ind.name}`}
                    onClick={() => { addIndicator(ind.name); setOpen(false); }}
                  >
                    <span className="dropdown-item-name">{ind.label}</span>
                    <span className="dropdown-item-badge overlay">Overlay</span>
                  </div>
                ))}
              </>
            )}
            {subCharts.length > 0 && (
              <>
                <div className="dropdown-section-label">Sub Chart</div>
                {subCharts.map((ind) => (
                  <div
                    key={ind.name}
                    className="dropdown-item"
                    id={`indicator-${ind.name}`}
                    onClick={() => { addIndicator(ind.name); setOpen(false); }}
                  >
                    <span className="dropdown-item-name">{ind.label}</span>
                    <span className="dropdown-item-badge sub-chart">Sub Chart</span>
                  </div>
                ))}
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

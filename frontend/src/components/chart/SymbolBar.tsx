// TICKR — Symbol Bar (symbol picker, timeframe, duration, chart type)
import { useChartStore } from '../../store/chartStore';
import type { Interval, Duration } from '../../store/chartStore';

const INTERVALS: Interval[] = ['1D', '1W', '1M'];
const DURATIONS: Duration[] = ['1M', '3M', '6M', '1Y', '2Y', '5Y'];

const POPULAR_SYMBOLS = [
  'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK', 'KOTAKBANK',
  'LT', 'BAJFINANCE', 'HINDUNILVR', 'SBIN', 'AXISBANK', 'WIPRO',
  'BHARTIARTL', 'ASIANPAINT', 'MARUTI', 'TITAN', 'NESTLEIND', 'ULTRACEMCO',
];

export default function SymbolBar() {
  const { symbol, interval, duration, chartType, setSymbol, setInterval, setDuration, setChartType } = useChartStore();

  return (
    <div className="symbol-bar">
      <select
        id="symbol-selector"
        className="symbol-selector"
        value={symbol}
        onChange={(e) => setSymbol(e.target.value)}
      >
        {POPULAR_SYMBOLS.map((s) => (
          <option key={s} value={s}>{s}.NS — {getCompanyName(s)}</option>
        ))}
      </select>

      <div style={{ display: 'flex', gap: 4, marginLeft: 8 }}>
        {INTERVALS.map((iv) => (
          <button
            key={iv}
            id={`interval-${iv}`}
            className={`interval-btn ${interval === iv ? 'active' : ''}`}
            onClick={() => setInterval(iv)}
          >{iv}</button>
        ))}
      </div>

      <select
        id="duration-select"
        className="duration-select"
        value={duration}
        onChange={(e) => setDuration(e.target.value as Duration)}
      >
        {DURATIONS.map((d) => <option key={d} value={d}>{d}</option>)}
      </select>

      <button
        id="zoom-control"
        className="zoom-control"
        onClick={() => {}}
        title="Scroll / click to zoom range"
      >
        ⟷ Scroll / click to zoom range
      </button>

      <div style={{ marginLeft: 'auto', display: 'flex', gap: 4 }}>
        <button
          id="chart-type-candle"
          className={`interval-btn ${chartType === 'candlestick' ? 'active' : ''}`}
          onClick={() => setChartType('candlestick')}
          title="Candlestick chart"
        >⊞ Candle</button>
        <button
          id="chart-type-line"
          className={`interval-btn ${chartType === 'line' ? 'active' : ''}`}
          onClick={() => setChartType('line')}
          title="Line chart"
        >∿ Line</button>
      </div>
    </div>
  );
}

function getCompanyName(sym: string): string {
  const names: Record<string, string> = {
    RELIANCE: 'Reliance Industries', TCS: 'Tata Consultancy Services',
    HDFCBANK: 'HDFC Bank', INFY: 'Infosys', ICICIBANK: 'ICICI Bank',
    KOTAKBANK: 'Kotak Mahindra Bank', LT: 'Larsen & Toubro',
    BAJFINANCE: 'Bajaj Finance', HINDUNILVR: 'Hindustan Unilever',
    SBIN: 'State Bank of India', AXISBANK: 'Axis Bank', WIPRO: 'Wipro',
    BHARTIARTL: 'Bharti Airtel', ASIANPAINT: 'Asian Paints',
    MARUTI: 'Maruti Suzuki', TITAN: 'Titan Company',
    NESTLEIND: 'Nestle India', ULTRACEMCO: 'UltraTech Cement',
  };
  return names[sym] || sym;
}

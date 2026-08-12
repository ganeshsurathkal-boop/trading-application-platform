// TICKR — Main Chart using TradingView lightweight-charts v5
// v5 uses createChart + series factories (CandlestickSeries, LineSeries, HistogramSeries)
import { useEffect, useRef } from 'react';
import {
  createChart,
  CrosshairMode,
  CandlestickSeries,
  LineSeries,
  HistogramSeries,
  type IChartApi,
  type ISeriesApi,
  type Time,
} from 'lightweight-charts';
import type { Candle, ActiveIndicator } from '../../types';
import type { ChartType } from '../../store/chartStore';

// How many bars from the left edge triggers an older-data fetch
const SCROLL_LEFT_THRESHOLD = 10;

interface Props {
  candles: Candle[];
  chartType: ChartType;
  activeIndicators: ActiveIndicator[];
  onScrollLeft?: () => void;
  isLoadingMore?: boolean;
}

const COLORS = ['#2563EB', '#D97706', '#7C3AED', '#0891B2', '#059669', '#DC2626'];

export default function MainChart({ candles, chartType, activeIndicators, onScrollLeft, isLoadingMore }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const mainSeriesRef = useRef<ISeriesApi<any> | null>(null);
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const indicatorSeriesRef = useRef<Record<string, ISeriesApi<any>[]>>({});
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const volumeSeriesRef = useRef<ISeriesApi<any> | null>(null);
  // Keep onScrollLeft in a ref so the timeScale subscriber always calls the latest version
  const onScrollLeftRef = useRef(onScrollLeft);
  useEffect(() => { onScrollLeftRef.current = onScrollLeft; }, [onScrollLeft]);
  // Previous sorted candles — used to tell a "prepend older history" update
  // (scroll-triggered lazy load) apart from a fresh dataset (symbol/interval/
  // duration change), so we only reset the zoom/pan on a genuine fresh load.
  const prevSortedRef = useRef<Candle[]>([]);

  // ── Initialize chart ─────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: {
        background: { color: '#FDFAF5' },
        textColor: '#6B6560',
        fontFamily: 'Inter, -apple-system, sans-serif',
        fontSize: 11,
      },
      grid: {
        vertLines: { color: '#E8E3D8', style: 1 },
        horzLines: { color: '#E8E3D8', style: 1 },
      },
      crosshair: {
        mode: CrosshairMode.Normal,
        vertLine: { color: '#C0392B', width: 1, style: 2, labelBackgroundColor: '#C0392B' },
        horzLine: { color: '#C0392B', width: 1, style: 2, labelBackgroundColor: '#C0392B' },
      },
      rightPriceScale: {
        borderColor: '#DDD8CC',
        scaleMargins: { top: 0.08, bottom: 0.2 },
      },
      timeScale: {
        borderColor: '#DDD8CC',
        timeVisible: true,
        secondsVisible: false,
      },
      width: containerRef.current.clientWidth,
      height: containerRef.current.clientHeight,
    });

    chartRef.current = chart;

    const ro = new ResizeObserver(() => {
      if (containerRef.current) {
        chart.applyOptions({
          width: containerRef.current.clientWidth,
          height: containerRef.current.clientHeight,
        });
      }
    });
    ro.observe(containerRef.current);

    // Detect left-scroll to load older candles
    const handleRangeChange = (range: { from: number; to: number } | null) => {
      if (!range) return;
      if (range.from < SCROLL_LEFT_THRESHOLD) {
        onScrollLeftRef.current?.();
      }
    };
    chart.timeScale().subscribeVisibleLogicalRangeChange(handleRangeChange);

    return () => {
      chart.timeScale().unsubscribeVisibleLogicalRangeChange(handleRangeChange);
      ro.disconnect();
      chart.remove();
      chartRef.current = null;
    };
  }, []);

  // ── Update chart data ─────────────────────────────────────────────────────
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || candles.length === 0) return;

    const sorted = [...candles].sort((a, b) => a.date.localeCompare(b.date));
    const prevSorted = prevSortedRef.current;

    // A "prepend" is a lazy-load of older history: same newest bar, more bars
    // total, all added at the front. Everything else (symbol/interval/duration
    // change, or the very first load) is a fresh dataset.
    const isPrepend =
      prevSorted.length > 0 &&
      sorted.length > prevSorted.length &&
      sorted[sorted.length - 1]?.date === prevSorted[prevSorted.length - 1]?.date;
    const addedBars = isPrepend ? sorted.length - prevSorted.length : 0;
    // Must be captured BEFORE removing the current series below — once a chart
    // has no series attached, getVisibleLogicalRange() can return null, which
    // would silently fall back to fitContent() and reset the user's scroll.
    const prevVisibleRange = isPrepend ? chart.timeScale().getVisibleLogicalRange() : null;

    if (mainSeriesRef.current) {
      try { chart.removeSeries(mainSeriesRef.current); } catch { /* chart already destroyed */ }
      mainSeriesRef.current = null;
    }
    if (volumeSeriesRef.current) {
      try { chart.removeSeries(volumeSeriesRef.current); } catch { /* chart already destroyed */ }
      volumeSeriesRef.current = null;
    }
    // Guard: chart may have been destroyed by StrictMode cleanup
    if (!chartRef.current) return;

    if (chartType === 'candlestick') {
      const series = chart.addSeries(CandlestickSeries, {
        upColor: '#16A34A',
        downColor: '#DC2626',
        borderUpColor: '#16A34A',
        borderDownColor: '#DC2626',
        wickUpColor: '#16A34A',
        wickDownColor: '#DC2626',
      });
      series.setData(
        sorted.map((c) => ({
          time: c.date as Time,
          open: c.open,
          high: c.high,
          low: c.low,
          close: c.close,
        }))
      );
      // Current price line
      if (sorted.length > 0) {
        series.createPriceLine({
          price: sorted[sorted.length - 1].close,
          color: '#C0392B',
          lineWidth: 1,
          lineStyle: 0,
          axisLabelVisible: true,
          title: '',
        });
      }
      mainSeriesRef.current = series;
    } else {
      const series = chart.addSeries(LineSeries, {
        color: '#C0392B',
        lineWidth: 2,
        crosshairMarkerVisible: true,
        crosshairMarkerRadius: 4,
      });
      series.setData(sorted.map((c) => ({ time: c.date as Time, value: c.close })));
      mainSeriesRef.current = series;
    }

    // Volume
    const volSeries = chart.addSeries(HistogramSeries, {
      color: '#DDD8CC',
      priceFormat: { type: 'volume' },
      priceScaleId: 'volume',
    });
    chart.priceScale('volume').applyOptions({
      scaleMargins: { top: 0.85, bottom: 0 },
    });
    volSeries.setData(
      sorted.map((c) => ({
        time: c.date as Time,
        value: c.volume,
        color: c.close >= c.open ? 'rgba(22,163,74,0.3)' : 'rgba(220,38,38,0.3)',
      }))
    );
    volumeSeriesRef.current = volSeries;

    if (isPrepend && prevVisibleRange) {
      // Keep the same bars on screen — shift the visible range forward by
      // however many older bars were just prepended, instead of snapping
      // the zoom back out to fit everything (which cancelled the user's scroll).
      chart.timeScale().setVisibleLogicalRange({
        from: prevVisibleRange.from + addedBars,
        to: prevVisibleRange.to + addedBars,
      });
    } else {
      chart.timeScale().fitContent();
    }
    prevSortedRef.current = sorted;
  }, [candles, chartType]);

  // ── Overlay indicators ────────────────────────────────────────────────────
  useEffect(() => {
    const chart = chartRef.current;
    if (!chart) return;

    Object.values(indicatorSeriesRef.current).flat().forEach((s) => {
      try { chart.removeSeries(s); } catch {}
    });
    indicatorSeriesRef.current = {};

    activeIndicators.filter((i) => i.overlay).forEach((ind, idx) => {
      const color = COLORS[idx % COLORS.length];
      const dataKeys = ind.data.length > 0
        ? Object.keys(ind.data[0]).filter((k) => k !== 'date')
        : [];

      const series: ISeriesApi<'Line'>[] = [];
      dataKeys.forEach((key, ki) => {
        const s = chart.addSeries(LineSeries, {
          color: ki === 0 ? color : COLORS[(idx + ki + 1) % COLORS.length],
          lineWidth: 1,
          title: key,
          crosshairMarkerVisible: false,
          lastValueVisible: true,
          priceLineVisible: false,
        });
        s.setData(
          ind.data
            .filter((d) => d[key] != null && !isNaN(Number(d[key])))
            .map((d) => ({ time: d.date as Time, value: Number(d[key]) }))
        );
        series.push(s as ISeriesApi<'Line'>);
      });
      indicatorSeriesRef.current[ind.id] = series;
    });
  }, [activeIndicators]);

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div
        ref={containerRef}
        id="main-chart"
        style={{ width: '100%', height: '100%' }}
      />
      {isLoadingMore && (
        <div
          style={{
            position: 'absolute',
            top: 8,
            left: 8,
            display: 'flex',
            alignItems: 'center',
            gap: 6,
            background: 'rgba(253,250,245,0.92)',
            border: '1px solid #DDD8CC',
            borderRadius: 6,
            padding: '4px 10px',
            fontSize: 11,
            color: '#6B6560',
            fontFamily: 'Inter, -apple-system, sans-serif',
            pointerEvents: 'none',
            zIndex: 10,
            backdropFilter: 'blur(4px)',
          }}
        >
          <span
            style={{
              display: 'inline-block',
              width: 10,
              height: 10,
              border: '2px solid #C0392B',
              borderTopColor: 'transparent',
              borderRadius: '50%',
              animation: 'spin 0.7s linear infinite',
            }}
          />
          Loading older data…
        </div>
      )}
    </div>
  );
}

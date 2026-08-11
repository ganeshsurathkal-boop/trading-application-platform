// TICKR — Sub-chart panel for non-overlay indicators (RSI, MACD) — v5 API
import { useEffect, useRef } from 'react';
import {
  createChart,
  CrosshairMode,
  LineSeries,
  type IChartApi,
  type Time,
} from 'lightweight-charts';
import type { ActiveIndicator } from '../../types';

interface Props {
  indicator: ActiveIndicator;
}

export default function SubChart({ indicator }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const chartRef = useRef<IChartApi | null>(null);

  useEffect(() => {
    if (!containerRef.current) return;

    const chart = createChart(containerRef.current, {
      layout: { background: { color: '#FDFAF5' }, textColor: '#6B6560', fontSize: 10 },
      grid: {
        vertLines: { color: '#E8E3D8', style: 1 },
        horzLines: { color: '#E8E3D8', style: 1 },
      },
      crosshair: { mode: CrosshairMode.Normal },
      rightPriceScale: { borderColor: '#DDD8CC', scaleMargins: { top: 0.1, bottom: 0.1 } },
      timeScale: { borderColor: '#DDD8CC', timeVisible: true, secondsVisible: false },
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

    return () => { ro.disconnect(); chart.remove(); };
  }, []);

  useEffect(() => {
    const chart = chartRef.current;
    if (!chart || indicator.data.length === 0) return;

    const dataKeys = Object.keys(indicator.data[0]).filter((k) => k !== 'date');
    dataKeys.forEach((key) => {
      const series = chart.addSeries(LineSeries, {
        color: '#7C3AED',
        lineWidth: 1,
        title: key,
        priceLineVisible: false,
      });
      series.setData(
        indicator.data
          .filter((d) => d[key] != null && !isNaN(Number(d[key])))
          .map((d) => ({ time: d.date as Time, value: Number(d[key]) }))
      );

      if (indicator.name === 'RSI') {
        series.createPriceLine({ price: 70, color: '#DC2626', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
        series.createPriceLine({ price: 30, color: '#16A34A', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
        series.createPriceLine({ price: 50, color: '#DDD8CC', lineWidth: 1, lineStyle: 2, axisLabelVisible: false, title: '' });
      }
    });

    chart.timeScale().fitContent();
  }, [indicator]);

  return (
    <div className="sub-chart-wrapper">
      <span className="sub-chart-label">{indicator.label}</span>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
    </div>
  );
}

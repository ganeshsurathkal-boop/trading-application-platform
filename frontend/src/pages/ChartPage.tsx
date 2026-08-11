// TICKR — Chart Terminal Page (Screen 1)
import { useEffect } from 'react';
import SymbolBar from '../components/chart/SymbolBar';
import IndicatorBar from '../components/indicators/IndicatorBar';
import MainChart from '../components/chart/MainChart';
import SubChart from '../components/chart/SubChart';
import WatchlistPanel from '../components/watchlist/WatchlistPanel';
import { useChartStore } from '../store/chartStore';

export default function ChartPage() {
  const {
    candles,
    chartType,
    activeIndicators,
    fetchCandles,
    fetchAvailableIndicators,
    fetchOlderCandles,
    loading,
    loadingMore,
  } = useChartStore();

  useEffect(() => {
    fetchCandles();
    fetchAvailableIndicators();
  }, []);

  const overlayIndicators = activeIndicators.filter((i) => i.overlay);
  const subChartIndicators = activeIndicators.filter((i) => !i.overlay);

  return (
    <div className="chart-page">
      {/* Keyframe for the loading-more spinner */}
      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>

      <SymbolBar />
      <IndicatorBar />

      <div className="chart-terminal">
        <div className="chart-container">
          {loading ? (
            <div className="spinner">
              <div className="spin" />
              Loading chart data...
            </div>
          ) : (
            <>
              <div className="main-chart-wrapper">
                <MainChart
                  candles={candles}
                  chartType={chartType}
                  activeIndicators={overlayIndicators}
                  onScrollLeft={fetchOlderCandles}
                  isLoadingMore={loadingMore}
                />
              </div>
              {subChartIndicators.map((ind) => (
                <SubChart key={ind.id} indicator={ind} />
              ))}
            </>
          )}
        </div>

        <WatchlistPanel />
      </div>
    </div>
  );
}

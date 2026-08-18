// TICKR — Scanner Builder Page (Screen 2)
import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useScannerStore } from '../store/scannerStore';
import CriteriaBrowser from '../components/scanner/CriteriaBrowser';
import CombinationPanel from '../components/scanner/CombinationPanel';

export default function ScannerPage() {
  const navigate = useNavigate();
  const { loading, running, fetchScanners, fetchSavedCombos, runBuilderAdHoc, runSavedCombo } = useScannerStore();

  useEffect(() => {
    fetchScanners();
    fetchSavedCombos();
  }, []);

  const handleRun = async () => {
    try {
      const result = await runBuilderAdHoc();
      navigate('/results', { state: { runResult: result } });
    } catch (e) {
      console.error(e);
    }
  };

  const handleRunSaved = async (id: number) => {
    try {
      const result = await runSavedCombo(id);
      navigate('/results', { state: { runResult: result } });
    } catch (e) {
      console.error(e);
    }
  };

  if (loading) {
    return (
      <div className="scanner-page">
        <div className="spinner" style={{ padding: 32 }}>
          <div className="spin" /> Loading scanners...
        </div>
      </div>
    );
  }

  return (
    <div className="scanner-page">
      <div className="scanner-builder">
        <CriteriaBrowser onRunCombo={handleRunSaved} />
        <CombinationPanel onRun={handleRun} running={running} />
      </div>
    </div>
  );
}

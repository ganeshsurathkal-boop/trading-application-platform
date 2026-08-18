// TICKR — Left pane of the Scanner builder: browse Technical/Fundamental scanners + My custom scanners
import type { ScannerDef, ScanCombo } from '../../types';
import { useScannerStore } from '../../store/scannerStore';

interface Props {
  onRunCombo: (id: number) => void;
}

export default function CriteriaBrowser({ onRunCombo }: Props) {
  const {
    scannersByCategory, savedCombos, builderCriteria,
    addCriterion, loadComboIntoBuilder, deleteCombo,
  } = useScannerStore();

  const selectedNames = new Set(builderCriteria.map((c) => c.scanner_name));

  const renderScannerCard = (s: ScannerDef) => (
    <div className="criterion-browse-card" key={s.name} id={`browse-${s.name.replace(/\s/g, '-')}`}>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div className="criterion-browse-name">{s.name}</div>
        <div className="criterion-browse-desc">{s.description}</div>
      </div>
      <button
        className="criterion-browse-add"
        disabled={selectedNames.has(s.name)}
        onClick={() => addCriterion(s.name)}
      >
        {selectedNames.has(s.name) ? 'Added' : '+ Add'}
      </button>
    </div>
  );

  const renderSavedCombo = (c: ScanCombo) => (
    <div className="saved-combo-row" key={c.id} id={`saved-combo-${c.id}`}>
      <span className="saved-combo-name" onClick={() => loadComboIntoBuilder(c)}>{c.name}</span>
      <button className="saved-combo-action" title="Run" onClick={() => onRunCombo(c.id)}>Run</button>
      <button
        className="saved-combo-action"
        title="Delete"
        onClick={() => {
          if (confirm(`Delete saved scan "${c.name}"?`)) deleteCombo(c.id);
        }}
      >
        ✕
      </button>
    </div>
  );

  return (
    <div className="scanner-builder-left">
      <div className="builder-section-label">Technical</div>
      {scannersByCategory.technical.length === 0 ? (
        <div className="fundamental-empty">No technical scanners installed.</div>
      ) : (
        scannersByCategory.technical.map(renderScannerCard)
      )}

      {scannersByCategory.plugin.length > 0 && (
        <>
          <div className="builder-section-label">Plugin</div>
          {scannersByCategory.plugin.map(renderScannerCard)}
        </>
      )}

      <div className="builder-section-label">Fundamental</div>
      <div className="fundamental-empty">
        Coming soon — no fundamental data source configured yet.
      </div>

      <div className="builder-section-label">My Custom Scanners</div>
      {savedCombos.length === 0 ? (
        <div className="fundamental-empty">
          Build a combination on the right, then Save it here.
        </div>
      ) : (
        savedCombos.map(renderSavedCombo)
      )}
    </div>
  );
}

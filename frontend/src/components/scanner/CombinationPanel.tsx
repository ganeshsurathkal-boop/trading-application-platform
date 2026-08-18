// TICKR — Right pane of the Scanner builder: the in-progress combination + Save/Run
import { useState } from 'react';
import { useScannerStore } from '../../store/scannerStore';
import CriterionParamEditor from './CriterionParamEditor';
import SaveComboModal from './SaveComboModal';

interface Props {
  onRun: () => void;
  running: boolean;
}

export default function CombinationPanel({ onRun, running }: Props) {
  const {
    builderCriteria, builderUniverse, universes, editingComboId, savedCombos,
    removeCriterion, updateCriterionParam, setBuilderUniverse, saveCombo, findScannerDef,
  } = useScannerStore();

  const [showSaveModal, setShowSaveModal] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const editingCombo = savedCombos.find((c) => c.id === editingComboId);

  const handleSave = async (name: string) => {
    setSaving(true);
    setSaveError(null);
    try {
      await saveCombo(name);
      setShowSaveModal(false);
    } catch (e: any) {
      setSaveError(e.response?.data?.detail || 'Failed to save combination');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="scanner-builder-right">
      <div className="builder-section-label">Combination</div>

      <div style={{ marginBottom: 14 }}>
        <div className="criterion-param-label">Universe</div>
        <select
          id="builder-universe-select"
          className="universe-select"
          style={{ width: '100%', marginBottom: 0 }}
          value={builderUniverse}
          onChange={(e) => setBuilderUniverse(e.target.value)}
        >
          {universes.map((u) => <option key={u} value={u}>{u}</option>)}
        </select>
      </div>

      {builderCriteria.length === 0 ? (
        <div className="builder-empty">
          Add one or more scanners from the left to build a combination.
          A stock must match all of them to appear in the results.
        </div>
      ) : (
        <div style={{ flex: 1 }}>
          {builderCriteria.map((c) => {
            const def = findScannerDef(c.scanner_name);
            return (
              <div className="criterion-card" key={c.scanner_name} id={`criterion-card-${c.scanner_name.replace(/\s/g, '-')}`}>
                <div className="criterion-card-header">
                  <span className="criterion-card-name">{c.scanner_name}</span>
                  <button
                    className="criterion-card-remove"
                    title={`Remove ${c.scanner_name}`}
                    onClick={() => removeCriterion(c.scanner_name)}
                  >
                    ×
                  </button>
                </div>
                {def && (
                  <CriterionParamEditor
                    paramSchema={def.param_schema}
                    values={c.params}
                    onChange={(paramName, value) => updateCriterionParam(c.scanner_name, paramName, value)}
                  />
                )}
              </div>
            );
          })}
        </div>
      )}

      <div className="builder-footer">
        <button
          id="save-combo-btn"
          className="btn-builder-save"
          disabled={builderCriteria.length === 0}
          onClick={() => setShowSaveModal(true)}
        >
          {editingCombo ? `Save "${editingCombo.name}"` : 'Save'}
        </button>
        <button
          id="run-combo-btn"
          className="btn-builder-run"
          disabled={builderCriteria.length === 0 || running}
          onClick={onRun}
        >
          {running ? 'Running…' : 'Run'}
        </button>
      </div>

      {showSaveModal && (
        <SaveComboModal
          initialName={editingCombo?.name}
          saving={saving}
          error={saveError}
          onSave={handleSave}
          onClose={() => { setShowSaveModal(false); setSaveError(null); }}
        />
      )}
    </div>
  );
}

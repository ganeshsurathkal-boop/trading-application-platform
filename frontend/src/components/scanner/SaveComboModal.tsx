// TICKR — Name-and-save modal for the scanner combination builder
import { useState } from 'react';

interface Props {
  initialName?: string;
  saving: boolean;
  error: string | null;
  onSave: (name: string) => void;
  onClose: () => void;
}

export default function SaveComboModal({ initialName, saving, error, onSave, onClose }: Props) {
  const [name, setName] = useState(initialName ?? '');

  return (
    <div className="add-stock-modal">
      <div className="add-stock-card">
        <h3>Save Scanner Combination</h3>
        <input
          autoFocus
          className="form-input"
          placeholder="e.g. Momentum breakout"
          value={name}
          onChange={(e) => setName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && name.trim() && onSave(name.trim())}
        />
        {error && (
          <div style={{ color: 'var(--red)', fontSize: 12, marginTop: 8 }}>{error}</div>
        )}
        <div className="modal-actions">
          <button className="btn-cancel" onClick={onClose}>Cancel</button>
          <button
            className="btn-confirm"
            disabled={saving || !name.trim()}
            onClick={() => onSave(name.trim())}
          >
            {saving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

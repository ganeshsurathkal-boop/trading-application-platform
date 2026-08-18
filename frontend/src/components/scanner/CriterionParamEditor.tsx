// TICKR — Parameter editor for one criterion card, generated from its scanner's param_schema
import type { ParamDef } from '../../types';

interface Props {
  paramSchema: ParamDef[];
  values: Record<string, number>;
  onChange: (paramName: string, value: number) => void;
}

export default function CriterionParamEditor({ paramSchema, values, onChange }: Props) {
  if (paramSchema.length === 0) {
    return null;
  }

  return (
    <>
      {paramSchema.map((p) => (
        <div className="criterion-param-row" key={p.name}>
          <div className="criterion-param-label">{p.label}</div>
          <input
            type="number"
            className="criterion-param-input"
            value={values[p.name] ?? p.default ?? p.min}
            min={p.min}
            max={p.max}
            step={p.step ?? (p.type === 'int' ? 1 : 0.1)}
            onChange={(e) => {
              const raw = e.target.value;
              if (raw === '') return;
              const num = p.type === 'int' ? parseInt(raw, 10) : parseFloat(raw);
              if (!isNaN(num)) onChange(p.name, num);
            }}
          />
        </div>
      ))}
    </>
  );
}

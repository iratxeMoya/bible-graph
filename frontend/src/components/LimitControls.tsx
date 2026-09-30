export interface Limits {
  seeds: number;
  neighbors: number;
}

export const DEFAULT_LIMITS: Limits = { seeds: 25, neighbors: 8 };

interface Props {
  limits: Limits;
  onChange: (limits: Limits) => void;
}

export function LimitControls({ limits, onChange }: Props) {
  return (
    <div className="limit-controls">
      <label>
        Semillas
        <input
          type="range"
          min={1}
          max={100}
          value={limits.seeds}
          onChange={(event) => onChange({ ...limits, seeds: Number(event.target.value) })}
        />
        <output>{limits.seeds}</output>
      </label>
      <label>
        Vecinos
        <input
          type="range"
          min={0}
          max={20}
          value={limits.neighbors}
          onChange={(event) => onChange({ ...limits, neighbors: Number(event.target.value) })}
        />
        <output>{limits.neighbors}</output>
      </label>
    </div>
  );
}

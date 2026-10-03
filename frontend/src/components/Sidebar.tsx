import { Info } from "lucide-react";
import type { SearchResponse } from "../api";

export interface Limits {
  seeds: number;
  neighbors: number;
}

export const DEFAULT_LIMITS: Limits = { seeds: 5, neighbors: 10 };

interface Props {
  limits: Limits;
  onChange: (limits: Limits) => void;
  response: SearchResponse | null;
  open: boolean;
}

export function Sidebar({ limits, onChange, response, open }: Props) {
  const seedCount = response?.nodes.filter((node) => node.is_seed).length ?? 0;

  return (
    <aside className={open ? "sidebar open" : "sidebar"} aria-label="Controles">
      <section className="control">
        <h2 id="seeds-label">Semillas</h2>
        <p>Pasajes que contienen el término o concepto de búsqueda.</p>
        <div className="slider">
          <input
            type="range"
            min={1}
            max={100}
            value={limits.seeds}
            aria-labelledby="seeds-label"
            onChange={(event) => onChange({ ...limits, seeds: Number(event.target.value) })}
          />
          <output>{limits.seeds}</output>
        </div>
      </section>

      <section className="control">
        <h2 id="neighbors-label">Vecinos</h2>
        <p>Pasajes relacionados con las semillas.</p>
        <div className="slider">
          <input
            type="range"
            min={0}
            max={20}
            value={limits.neighbors}
            aria-labelledby="neighbors-label"
            onChange={(event) => onChange({ ...limits, neighbors: Number(event.target.value) })}
          />
          <output>{limits.neighbors}</output>
        </div>
      </section>

      <footer className="sidebar-footer">
        {response && response.nodes.length > 0 && (
          <p className="stats">
            {seedCount} de {response.total_matches} coincidencias · {response.nodes.length} nodos
            {response.truncated && " · recortado a 600 nodos"}
          </p>
        )}
        <div className="about">
          <Info size={15} aria-hidden="true" />
          <p>
            <strong>La Biblia es una red de conexiones.</strong>
            Explora cómo los pasajes se relacionan entre sí.
          </p>
        </div>
        <p>
          Referencias cruzadas de{" "}
          <a href="https://www.openbible.info/labs/cross-references/" target="_blank" rel="noreferrer">
            OpenBible.info
          </a>{" "}
          (CC-BY) · Texto: Reina-Valera 1909 (dominio público)
        </p>
      </footer>
    </aside>
  );
}

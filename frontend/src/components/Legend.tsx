import type { CSSProperties } from "react";
import { BOOK_GROUPS, groupVar } from "../groups";

export function dotStyle(colorVar: string): CSSProperties {
  return { "--dot": `var(${colorVar})` } as CSSProperties;
}

export function Legend() {
  return (
    <ul className="legend" aria-label="Leyenda">
      <li>
        <i className="dot" style={dotStyle("--accent")} /> Coincidencia
      </li>
      {BOOK_GROUPS.map((group) => (
        <li key={group.id}>
          <i className="dot" style={dotStyle(groupVar(group))} /> {group.name}
        </li>
      ))}
    </ul>
  );
}

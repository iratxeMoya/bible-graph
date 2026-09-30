import { ChevronRight, X } from "lucide-react";
import type { GraphNode, Passage } from "../api";
import type { Connection } from "../graph";
import { groupOf, groupVar } from "../groups";
import { snippet } from "../text";
import { dotStyle } from "./Legend";

export type PassageState =
  | { status: "loading"; label: string }
  | { status: "error"; label: string }
  | { status: "done"; label: string; passage: Passage };

/** Frases de relación de un versículo: las recibidas y las que aún se están pidiendo. */
export interface ExplanationsState {
  verse: number;
  texts: Map<number, string | null>;
  pending: Set<number>;
}

interface Props {
  node: GraphNode;
  nodes: Map<number, GraphNode>;
  connections: Connection[];
  explanations: ExplanationsState;
  passage: PassageState | null;
  onSelectNode: (id: number) => void;
  onOpenPassage: (connection: Connection) => void;
  onClose: () => void;
}

function colorVar(node: GraphNode): string {
  return node.is_seed ? "--accent" : groupVar(groupOf(node.id));
}

function Why({ connection, other, explanations }: {
  connection: Connection & { fromId: number };
  other: GraphNode | undefined;
  explanations: ExplanationsState;
}) {
  // Mientras llegan las del versículo abierto, las de otro versículo no se muestran.
  const pending =
    explanations.verse !== connection.fromId || explanations.pending.has(connection.nodeId);
  if (pending) {
    return (
      <span className="why">
        <span className="visually-hidden">Generando…</span>
        <span className="skeleton" aria-hidden="true" />
      </span>
    );
  }
  const text = explanations.texts.get(connection.nodeId);
  if (text) return <span className="why">{text}</span>;
  return <span className="why quote">«{snippet(other?.text ?? "", 70)}»</span>;
}

export function VersePanel({
  node,
  nodes,
  connections,
  explanations,
  passage,
  onSelectNode,
  onOpenPassage,
  onClose,
}: Props) {
  return (
    <aside className="verse-panel" aria-label={`Versículo ${node.ref}`}>
      <button type="button" className="close" onClick={onClose} aria-label="Cerrar">
        <X size={18} />
      </button>
      <header className="panel-header">
        <i className="dot" style={dotStyle(colorVar(node))} />
        <div>
          <h2>{node.ref}</h2>
          <p className="group">{groupOf(node.id).name}</p>
        </div>
        {node.is_seed && <span className="badge">Semilla</span>}
      </header>
      <p className="verse-text">{node.text}</p>

      {passage && (
        <section className="passage">
          <h3>{passage.status === "done" ? passage.passage.ref : passage.label}</h3>
          {passage.status === "loading" && <p className="muted">Cargando pasaje…</p>}
          {passage.status === "error" && <p className="muted">No se pudo cargar el pasaje.</p>}
          {passage.status === "done" &&
            passage.passage.verses.map((verse) => (
              <p key={verse.id}>
                <sup>{verse.ref.split(":").pop()}</sup> {verse.text}
              </p>
            ))}
        </section>
      )}

      <h3 className="relations-title">
        <span>Relaciones</span>
        <span>{connections.length}</span>
      </h3>
      {connections.length === 0 && <p className="muted relations-title">Sin relaciones en este grafo.</p>}
      <ul className="relations">
        {connections.map((connection) => {
          const other = nodes.get(connection.nodeId);
          const [from, to] =
            connection.direction === "out" ? [node.label, connection.label] : [connection.label, node.label];
          return (
            <li key={connection.key}>
              <button
                type="button"
                className="relation"
                onClick={() => onSelectNode(connection.nodeId)}
                title={`${from} remite a ${to} · ${connection.weight} votos en OpenBible`}
              >
                <i className="dot" style={dotStyle(other ? colorVar(other) : "--muted")} />
                <span className="body">
                  <span className="ref">{connection.label}</span>
                  <Why
                    connection={{ ...connection, fromId: node.id }}
                    other={other}
                    explanations={explanations}
                  />
                </span>
                <ChevronRight size={16} className="chevron" aria-hidden="true" />
              </button>
              {connection.rangeEndId !== null && (
                <div className="relation-extra">
                  <button type="button" onClick={() => onOpenPassage(connection)}>
                    leer pasaje
                  </button>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </aside>
  );
}

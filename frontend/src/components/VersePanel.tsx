import type { GraphNode, Passage } from "../api";
import type { Connection } from "../graph";

export type PassageState =
  | { status: "loading"; label: string }
  | { status: "error"; label: string }
  | { status: "done"; label: string; passage: Passage };

interface Props {
  node: GraphNode;
  connections: Connection[];
  passage: PassageState | null;
  onSelectNode: (id: number) => void;
  onOpenPassage: (connection: Connection) => void;
  onClose: () => void;
}

export function VersePanel({
  node,
  connections,
  passage,
  onSelectNode,
  onOpenPassage,
  onClose,
}: Props) {
  return (
    <aside className="verse-panel">
      <header>
        <h2>{node.ref}</h2>
        <button type="button" onClick={onClose} aria-label="Cerrar">
          ×
        </button>
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

      <h3>Conexiones ({connections.length})</h3>
      {connections.length === 0 && <p className="muted">Sin conexiones en este grafo.</p>}
      <ul className="connections">
        {connections.map((connection) => (
          <li key={connection.key}>
            <button
              type="button"
              onClick={() => onSelectNode(connection.nodeId)}
              title={
                connection.direction === "out"
                  ? `${node.ref} remite a ${connection.label}`
                  : `${connection.label} remite a ${node.ref}`
              }
            >
              <span aria-hidden="true">{connection.direction === "out" ? "→" : "←"}</span>{" "}
              {connection.label}
            </button>
            {connection.rangeEndId !== null && (
              <button type="button" className="link" onClick={() => onOpenPassage(connection)}>
                leer pasaje
              </button>
            )}
            <span className="weight" title="Votos en OpenBible">
              {connection.weight}
            </span>
          </li>
        ))}
      </ul>
    </aside>
  );
}

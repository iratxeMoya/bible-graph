import { useEffect, useMemo, useRef, useState } from "react";
import { fetchPassage, searchGraph, type SearchResponse } from "./api";
import { GraphView } from "./components/GraphView";
import { DEFAULT_LIMITS, LimitControls, type Limits } from "./components/LimitControls";
import { MIN_QUERY_LENGTH, SearchBar } from "./components/SearchBar";
import { type PassageState, VersePanel } from "./components/VersePanel";
import { type Connection, connectionsOf } from "./graph";

const LIMITS_DEBOUNCE_MS = 300;
const SLOW_AFTER_MS = 5000;

type Search =
  | { status: "idle" }
  | { status: "loading"; slow: boolean }
  | { status: "error" }
  | { status: "done"; response: SearchResponse };

function initialQuery(): string {
  return new URLSearchParams(window.location.search).get("q")?.trim() ?? "";
}

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

export function App() {
  const [query, setQuery] = useState(initialQuery);
  const [limits, setLimits] = useState<Limits>(DEFAULT_LIMITS);
  const debouncedLimits = useDebounced(limits, LIMITS_DEBOUNCE_MS);
  const [attempt, setAttempt] = useState(0);
  const [search, setSearch] = useState<Search>({ status: "idle" });
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [passage, setPassage] = useState<PassageState | null>(null);
  const passageRequest = useRef<AbortController | null>(null);

  useEffect(() => {
    if (query.length < MIN_QUERY_LENGTH) {
      setSearch({ status: "idle" });
      return;
    }
    // Abortar la petición anterior evita que una respuesta lenta pise a una más reciente.
    const controller = new AbortController();
    setSearch({ status: "loading", slow: false });
    const slowTimer = window.setTimeout(() => {
      if (!controller.signal.aborted) setSearch({ status: "loading", slow: true });
    }, SLOW_AFTER_MS);

    searchGraph({ q: query, ...debouncedLimits }, controller.signal)
      .then((response) => {
        if (controller.signal.aborted) return;
        setSearch({ status: "done", response });
        // El nodo seleccionado puede no estar en el grafo nuevo.
        setSelectedId((current) =>
          current !== null && response.nodes.some((node) => node.id === current) ? current : null,
        );
      })
      .catch(() => {
        if (!controller.signal.aborted) setSearch({ status: "error" });
      })
      .finally(() => window.clearTimeout(slowTimer));

    return () => {
      controller.abort();
      window.clearTimeout(slowTimer);
    };
  }, [query, debouncedLimits, attempt]);

  // El pasaje abierto pertenece al nodo seleccionado: al cambiar de nodo se cierra.
  useEffect(() => {
    passageRequest.current?.abort();
    setPassage(null);
  }, [selectedId]);

  function runSearch(next: string) {
    const url = new URL(window.location.href);
    url.searchParams.set("q", next);
    window.history.replaceState(null, "", url);
    setSelectedId(null);
    setQuery(next);
    setAttempt((n) => n + 1);
  }

  function openPassage(connection: Connection) {
    passageRequest.current?.abort();
    const controller = new AbortController();
    passageRequest.current = controller;
    setPassage({ status: "loading", label: connection.label });
    fetchPassage(connection.nodeId, connection.rangeEndId, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) {
          setPassage({ status: "done", label: connection.label, passage: result });
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setPassage({ status: "error", label: connection.label });
      });
  }

  const response = search.status === "done" ? search.response : null;
  const selectedNode = useMemo(
    () => response?.nodes.find((node) => node.id === selectedId) ?? null,
    [response, selectedId],
  );
  const connections = useMemo(
    () => (response && selectedId !== null ? connectionsOf(selectedId, response) : []),
    [response, selectedId],
  );
  const seedCount = response?.nodes.filter((node) => node.is_seed).length ?? 0;

  return (
    <div className="app">
      <header className="top-bar">
        <h1>Grafo bíblico</h1>
        <SearchBar query={query} onSearch={runSearch} />
        <LimitControls limits={limits} onChange={setLimits} />
      </header>

      <main className="workspace">
        <section className="graph-area">
          {search.status === "idle" && (
            <p className="message">
              Escribe un término o concepto para ver los versículos relacionados y sus conexiones.
            </p>
          )}
          {search.status === "loading" && (
            <p className="message">
              Buscando…
              {search.slow && <span> La API puede tardar hasta un minuto en despertar.</span>}
            </p>
          )}
          {search.status === "error" && (
            <p className="message">
              No se pudo completar la búsqueda.{" "}
              <button type="button" onClick={() => setAttempt((n) => n + 1)}>
                Reintentar
              </button>
            </p>
          )}
          {response && response.nodes.length === 0 && (
            <p className="message">No hay versículos que contengan «{response.query}».</p>
          )}
          {response && response.nodes.length > 0 && (
            <GraphView response={response} selectedId={selectedId} onSelect={setSelectedId} />
          )}
        </section>

        {selectedNode && (
          <VersePanel
            node={selectedNode}
            connections={connections}
            passage={passage}
            onSelectNode={setSelectedId}
            onOpenPassage={openPassage}
            onClose={() => setSelectedId(null)}
          />
        )}
      </main>

      <footer className="status-bar">
        {response && response.nodes.length > 0 && (
          <span>
            {seedCount} de {response.total_matches} coincidencias · {response.nodes.length} nodos
            {response.truncated && " · Grafo recortado a 600 nodos"}
          </span>
        )}
        <span className="legend">
          <i className="dot seed" /> Coincidencia <i className="dot at" /> AT{" "}
          <i className="dot nt" /> NT
        </span>
        <span>
          Referencias cruzadas de{" "}
          <a
            href="https://www.openbible.info/labs/cross-references/"
            target="_blank"
            rel="noreferrer"
          >
            OpenBible.info
          </a>{" "}
          (CC-BY) · Texto: Reina-Valera 1909 (dominio público)
        </span>
      </footer>
    </div>
  );
}

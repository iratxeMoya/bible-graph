import { useEffect, useMemo, useRef, useState } from "react";
import { fetchExplanations, fetchPassage, searchGraph, type SearchResponse } from "./api";
import { GraphView } from "./components/GraphView";
import { MIN_QUERY_LENGTH } from "./components/SearchBar";
import { DEFAULT_LIMITS, type Limits, Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { type ExplanationsState, type PassageState, VersePanel } from "./components/VersePanel";
import { type Connection, explanationTargets, relationsOf } from "./graph";
import { applyTheme, readTheme, type Theme } from "./theme";

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

function browserStorage(): Storage | undefined {
  try {
    return window.localStorage;
  } catch {
    return undefined;
  }
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
  const [explanations, setExplanations] = useState<ExplanationsState>({ status: "loading" });
  const [theme, setTheme] = useState<Theme>(() => {
    const initial = readTheme(browserStorage());
    applyTheme(browserStorage(), initial);
    return initial;
  });
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const passageRequest = useRef<AbortController | null>(null);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSelectedId(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

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

  const response = search.status === "done" ? search.response : null;
  const nodes = useMemo(() => new Map((response?.nodes ?? []).map((n) => [n.id, n])), [response]);
  const selectedNode = selectedId === null ? null : (nodes.get(selectedId) ?? null);
  const connections = useMemo(
    () => (response && selectedId !== null ? relationsOf(selectedId, response) : []),
    [response, selectedId],
  );
  const targets = useMemo(() => explanationTargets(connections), [connections]);

  // Frases de relación: se piden al abrir un versículo. La primera vez las genera Ollama.
  useEffect(() => {
    if (selectedId === null || targets.length === 0) return;
    const controller = new AbortController();
    setExplanations({ status: "loading" });
    fetchExplanations(selectedId, targets, controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        setExplanations({
          status: "done",
          texts: new Map(result.explanations.map((e) => [e.other, e.text])),
        });
      })
      .catch(() => {
        if (!controller.signal.aborted) setExplanations({ status: "done", texts: new Map() });
      });
    return () => controller.abort();
  }, [selectedId, targets]);

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

  return (
    <div className="app">
      <TopBar
        query={query}
        onSearch={runSearch}
        theme={theme}
        onToggleTheme={() => {
          const next = theme === "dark" ? "light" : "dark";
          applyTheme(browserStorage(), next);
          setTheme(next);
        }}
        onToggleSidebar={() => setSidebarOpen((open) => !open)}
      />
      <Sidebar limits={limits} onChange={setLimits} response={response} open={sidebarOpen} />

      <main className="graph-area">
        {search.status === "idle" && (
          <p className="message">
            Escribe un término o concepto para ver los pasajes que lo contienen y cómo se
            conectan con el resto de la Biblia.
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
            No se pudo completar la búsqueda.
            <br />
            <button type="button" onClick={() => setAttempt((n) => n + 1)}>
              Reintentar
            </button>
          </p>
        )}
        {response && response.nodes.length === 0 && (
          <p className="message">No hay versículos que contengan «{response.query}».</p>
        )}
        {response && response.nodes.length > 0 && (
          <GraphView
            response={response}
            theme={theme}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        )}
      </main>

      {selectedNode && (
        <VersePanel
          node={selectedNode}
          nodes={nodes}
          connections={connections}
          explanations={targets.length === 0 ? { status: "done", texts: new Map() } : explanations}
          passage={passage}
          onSelectNode={setSelectedId}
          onOpenPassage={openPassage}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  );
}

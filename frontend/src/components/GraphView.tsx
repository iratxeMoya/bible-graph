import cytoscape, {
  type Core,
  type LayoutOptions,
  type NodeSingular,
  type StylesheetJson,
} from "cytoscape";
import fcose from "cytoscape-fcose";
import { Minus, Plus } from "lucide-react";
import { useEffect, useRef } from "react";
import type { SearchResponse } from "../api";
import { TERM_ID, toElements } from "../graph";
import { BOOK_GROUPS } from "../groups";
import { cssVar, type Theme } from "../theme";
import { Legend } from "./Legend";

cytoscape.use(fcose);

const ZOOM_STEP = 1.25;

/** Estilos de Cytoscape. Los colores salen de las variables CSS del tema activo. */
function buildStyle(): StylesheetJson {
  const accent = cssVar("--accent");
  const colors: [string, string][] = [
    ["seed", accent],
    ...BOOK_GROUPS.map((g): [string, string] => [g.id, cssVar(`--group-${g.id}`)]),
  ];
  return [
    {
      selector: "node",
      style: {
        width: 12,
        height: 12,
        "background-color": cssVar("--node-fill"),
        "border-width": 1.5,
        "underlay-opacity": 0.14,
        "underlay-padding": 4,
        "underlay-shape": "ellipse",
      },
    },
    ...colors.map(([name, color]) => ({
      selector: `node.c-${name}`,
      style: { "border-color": color, "underlay-color": color },
    })),
    {
      selector: "node.seed",
      style: { width: 22, height: 22, "border-width": 2, "underlay-opacity": 0.22, "underlay-padding": 7 },
    },
    {
      selector: "node.term",
      style: {
        width: 46,
        height: 46,
        "border-width": 2.5,
        "border-color": accent,
        "underlay-color": accent,
        "underlay-opacity": 0.3,
        "underlay-padding": 12,
      },
    },
    {
      selector: "edge",
      style: {
        width: "data(width)",
        "line-color": cssVar("--edge"),
        "target-arrow-color": cssVar("--edge"),
        "target-arrow-shape": "triangle",
        "arrow-scale": 0.5,
        "curve-style": "bezier",
        opacity: 0.45,
      },
    },
    {
      selector: "edge.term-edge",
      style: { width: 1, "line-color": accent, "target-arrow-shape": "none", opacity: 0.35 },
    },
    ...colors.map(([name, color]) => ({
      selector: `edge.lit.to-${name}`,
      style: { "line-color": color, "target-arrow-color": color, opacity: 0.9 },
    })),
    { selector: ".faded", style: { opacity: 0.12 } },
    { selector: "edge.faded", style: { opacity: 0.05 } },
    {
      selector: "node.selected",
      style: { "border-width": 3, "underlay-opacity": 0.4, "underlay-padding": 9 },
    },
  ];
}

const LAYOUT = {
  name: "fcose",
  animate: false,
  quality: "default",
  nodeSeparation: 70,
  idealEdgeLength: 80,
  nodeRepulsion: 7000,
  padding: 40,
  fixedNodeConstraint: [{ nodeId: TERM_ID, position: { x: 0, y: 0 } }],
} as LayoutOptions;

/** Etiquetas HTML de dos líneas, recolocadas sobre el lienzo en cada fotograma. */
function createLabelLayer(cy: Core, layer: HTMLElement): () => void {
  const labels = new Map<string, HTMLElement>();
  cy.nodes().forEach((node) => {
    const el = document.createElement("div");
    el.className = node.id() === TERM_ID ? "node-label term" : "node-label";
    const title = document.createElement("span");
    title.className = "title";
    title.textContent = node.data("label");
    const subtitle = document.createElement("span");
    subtitle.className = "subtitle";
    subtitle.textContent = node.data("snippet");
    el.append(title, subtitle);
    layer.append(el);
    labels.set(node.id(), el);
  });

  const isVisible = (node: NodeSingular) =>
    node.hasClass("term") ||
    node.hasClass("seed") ||
    node.hasClass("hover") ||
    node.hasClass("selected") ||
    node.hasClass("near");

  const place = () => {
    cy.nodes().forEach((node) => {
      const el = labels.get(node.id());
      if (!el) return;
      const visible = isVisible(node);
      el.classList.toggle("visible", visible);
      if (!visible) return;
      el.classList.toggle("dimmed", node.hasClass("faded"));
      // Los vecinos del seleccionado muestran solo la referencia, para no solaparse.
      el.classList.toggle(
        "compact",
        node.hasClass("near") &&
          !node.hasClass("selected") &&
          !node.hasClass("hover") &&
          !node.hasClass("seed") &&
          !node.hasClass("term"),
      );
      const { x, y } = node.renderedPosition();
      const offset = node.renderedOuterHeight() / 2 + 4;
      el.style.transform = `translate(calc(${x}px - 50%), ${y + offset}px)`;
    });
  };
  cy.on("render", place);
  place();
  return () => {
    cy.off("render", place);
    labels.forEach((el) => el.remove());
  };
}

interface Props {
  response: SearchResponse;
  theme: Theme;
  selectedId: number | null;
  onSelect: (id: number | null) => void;
}

export function GraphView({ response, theme, selectedId, onSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const layerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    const cy = cytoscape({
      container: containerRef.current,
      elements: toElements(response),
      style: buildStyle(),
      layout: LAYOUT,
      minZoom: 0.2,
      maxZoom: 3,
    });
    const removeLabels = createLabelLayer(cy, layerRef.current!);
    cy.on("tap", "node", (event) => {
      const id = event.target.id();
      if (id !== TERM_ID) onSelectRef.current(Number(id));
    });
    cy.on("tap", (event) => {
      if (event.target === cy) onSelectRef.current(null);
    });
    cy.on("mouseover", "node", (event) => event.target.addClass("hover"));
    cy.on("mouseout", "node", (event) => event.target.removeClass("hover"));
    cyRef.current = cy;
    return () => {
      cyRef.current = null;
      removeLabels();
      cy.destroy();
    };
  }, [response]);

  // El tema cambia los colores del grafo: se recalculan desde las variables CSS.
  useEffect(() => {
    cyRef.current?.style(buildStyle());
  }, [theme]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().removeClass("faded selected near lit");
    if (selectedId === null) return;
    const node = cy.getElementById(String(selectedId));
    if (node.empty()) return;
    const neighborhood = node.closedNeighborhood();
    cy.elements().not(neighborhood).addClass("faded");
    neighborhood.nodes().addClass("near");
    node.connectedEdges().addClass("lit");
    node.addClass("selected");
    // Al abrirse el panel el lienzo se estrecha: si el nodo queda fuera, se centra.
    const timer = window.setTimeout(() => {
      cy.resize();
      const { x, y } = node.renderedPosition();
      const margin = 60;
      if (x < margin || y < margin || x > cy.width() - margin || y > cy.height() - margin) {
        cy.animate({ center: { eles: node } }, { duration: 300 });
      }
    }, 60);
    return () => window.clearTimeout(timer);
  }, [response, selectedId]);

  function zoomBy(factor: number) {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({
      level: cy.zoom() * factor,
      renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
    });
  }

  return (
    <>
      <div ref={containerRef} className="graph-view" />
      <div ref={layerRef} className="label-layer" aria-hidden="true" />
      <div className="graph-tools">
        <Legend />
        <div className="zoom">
          <button type="button" onClick={() => zoomBy(ZOOM_STEP)} aria-label="Acercar">
            <Plus size={16} />
          </button>
          <button type="button" onClick={() => zoomBy(1 / ZOOM_STEP)} aria-label="Alejar">
            <Minus size={16} />
          </button>
        </div>
      </div>
    </>
  );
}

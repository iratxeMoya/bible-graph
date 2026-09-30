import cytoscape, { type Core, type LayoutOptions, type StylesheetJson } from "cytoscape";
import fcose from "cytoscape-fcose";
import { useEffect, useRef } from "react";
import type { SearchResponse } from "../api";
import { toElements } from "../graph";

cytoscape.use(fcose);

const STYLE: StylesheetJson = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      "font-size": 9,
      color: "#1f2933",
      "text-valign": "bottom",
      "text-margin-y": 3,
      width: 14,
      height: 14,
    },
  },
  { selector: "node.at", style: { "background-color": "#4f7cac" } },
  { selector: "node.nt", style: { "background-color": "#5a9a6e" } },
  {
    selector: "node.seed",
    style: {
      "background-color": "#d97706",
      width: 24,
      height: 24,
      "font-size": 11,
      "font-weight": "bold",
    },
  },
  {
    selector: "edge",
    style: {
      width: "data(width)",
      "line-color": "#9aa5b1",
      "target-arrow-color": "#9aa5b1",
      "target-arrow-shape": "triangle",
      "arrow-scale": 0.7,
      "curve-style": "bezier",
      opacity: 0.55,
    },
  },
  { selector: ".faded", style: { opacity: 0.1, "text-opacity": 0 } },
  {
    selector: "node.selected",
    style: { "border-width": 3, "border-color": "#111827" },
  },
];

const LAYOUT = {
  name: "fcose",
  animate: false,
  quality: "default",
  nodeSeparation: 60,
  idealEdgeLength: 70,
  nodeRepulsion: 6000,
  padding: 30,
} as LayoutOptions;

interface Props {
  response: SearchResponse;
  selectedId: number | null;
  onSelect: (id: number | null) => void;
}

export function GraphView({ response, selectedId, onSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    const cy = cytoscape({
      container: containerRef.current,
      elements: toElements(response),
      style: STYLE,
      layout: LAYOUT,
      minZoom: 0.2,
      maxZoom: 3,
    });
    cy.on("tap", "node", (event) => onSelectRef.current(Number(event.target.id())));
    cy.on("tap", (event) => {
      if (event.target === cy) onSelectRef.current(null);
    });
    cyRef.current = cy;
    return () => {
      cyRef.current = null;
      cy.destroy();
    };
  }, [response]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().removeClass("faded selected");
    if (selectedId === null) return;
    const node = cy.getElementById(String(selectedId));
    if (node.empty()) return;
    cy.elements().not(node.closedNeighborhood()).addClass("faded");
    node.addClass("selected");
  }, [response, selectedId]);

  return <div ref={containerRef} className="graph-view" />;
}

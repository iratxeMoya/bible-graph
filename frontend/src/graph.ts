import type { ElementDefinition } from "cytoscape";
import type { GraphEdge, GraphNode, SearchResponse } from "./api";

const MIN_EDGE_WIDTH = 1;
const MAX_EDGE_WIDTH = 8;

/** Grosor de la arista: crece con el logaritmo del peso, porque los votos van de 1 a varios cientos. */
export function edgeWidth(weight: number): number {
  const width = MIN_EDGE_WIDTH + 2 * Math.log10(Math.max(weight, 1));
  return Math.min(MAX_EDGE_WIDTH, Math.round(width * 10) / 10);
}

export function edgeId(edge: Pick<GraphEdge, "source" | "target">): string {
  return `e${edge.source}-${edge.target}`;
}

function nodeClasses(node: GraphNode): string {
  return [node.is_seed ? "seed" : "neighbor", node.testament === "AT" ? "at" : "nt"].join(" ");
}

/** Convierte la respuesta de la API en elementos de Cytoscape. Los IDs de Cytoscape son cadenas. */
export function toElements(response: SearchResponse): ElementDefinition[] {
  const nodeIds = new Set(response.nodes.map((node) => node.id));
  const nodes: ElementDefinition[] = response.nodes.map((node) => ({
    group: "nodes",
    data: { id: String(node.id), label: node.label },
    classes: nodeClasses(node),
  }));
  const edges: ElementDefinition[] = response.edges
    .filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
    .map((edge) => ({
      group: "edges",
      data: {
        id: edgeId(edge),
        source: String(edge.source),
        target: String(edge.target),
        width: edgeWidth(edge.weight),
      },
    }));
  return [...nodes, ...edges];
}

export interface Connection {
  /** Identificador único de la conexión dentro del panel. */
  key: string;
  /** El nodo del otro extremo. */
  nodeId: number;
  /** Texto a mostrar: la referencia del otro extremo, con rango si la arista lo tiene. */
  label: string;
  weight: number;
  /** "out": el versículo seleccionado cita al otro. "in": el otro lo cita a él. */
  direction: "out" | "in";
  /** Último versículo del rango al que apunta la arista, o null si apunta a un solo versículo. */
  rangeEndId: number | null;
}

/** Conexiones de un nodo dentro del grafo mostrado, de mayor a menor peso. */
export function connectionsOf(nodeId: number, response: SearchResponse): Connection[] {
  const labels = new Map(response.nodes.map((node) => [node.id, node.label]));
  const connections: Connection[] = [];
  for (const edge of response.edges) {
    if (edge.source === nodeId && labels.has(edge.target)) {
      connections.push({
        key: `out-${edgeId(edge)}`,
        nodeId: edge.target,
        label: edge.target_label,
        weight: edge.weight,
        direction: "out",
        rangeEndId: edge.target_end_id,
      });
    } else if (edge.target === nodeId && labels.has(edge.source)) {
      connections.push({
        key: `in-${edgeId(edge)}`,
        nodeId: edge.source,
        label: labels.get(edge.source) ?? String(edge.source),
        weight: edge.weight,
        direction: "in",
        rangeEndId: null,
      });
    }
  }
  return connections.sort((a, b) => b.weight - a.weight || a.nodeId - b.nodeId);
}

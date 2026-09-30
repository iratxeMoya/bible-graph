import type { ElementDefinition } from "cytoscape";
import type { GraphEdge, GraphNode, SearchResponse } from "./api";
import { groupOf } from "./groups";
import { capitalize, snippet } from "./text";

/** ID del nodo central con el término buscado. Los versículos usan su ID numérico. */
export const TERM_ID = "term";
export const MAX_EXPLANATIONS = 30;

const MIN_EDGE_WIDTH = 0.6;
const MAX_EDGE_WIDTH = 4;

/** Grosor de la arista: crece con el logaritmo del peso, porque los votos van de 1 a varios cientos. */
export function edgeWidth(weight: number): number {
  const width = MIN_EDGE_WIDTH + 1.2 * Math.log10(Math.max(weight, 1));
  return Math.min(MAX_EDGE_WIDTH, Math.round(width * 10) / 10);
}

export function edgeId(edge: Pick<GraphEdge, "source" | "target">): string {
  return `e${edge.source}-${edge.target}`;
}

/** Color con que se ilumina una arista o se pinta un nodo: ámbar si es semilla, si no el de su grupo. */
export function colorClass(node: GraphNode): string {
  return node.is_seed ? "seed" : groupOf(node.id).id;
}

/** Convierte la respuesta de la API en elementos de Cytoscape, con el término en el centro. */
export function toElements(response: SearchResponse): ElementDefinition[] {
  const byId = new Map(response.nodes.map((node) => [node.id, node]));
  const seeds = response.nodes.filter((node) => node.is_seed);
  if (response.nodes.length === 0) return [];

  const term: ElementDefinition = {
    group: "nodes",
    data: {
      id: TERM_ID,
      label: capitalize(response.query),
      snippet: `${response.total_matches} ${response.total_matches === 1 ? "pasaje" : "pasajes"}`,
    },
    classes: "term",
  };
  const nodes: ElementDefinition[] = response.nodes.map((node) => ({
    group: "nodes",
    data: { id: String(node.id), label: node.label, snippet: snippet(node.text) },
    classes: `${node.is_seed ? "seed" : "neighbor"} c-${colorClass(node)}`,
  }));
  const termEdges: ElementDefinition[] = seeds.map((seed) => ({
    group: "edges",
    data: { id: `t${seed.id}`, source: TERM_ID, target: String(seed.id), width: 1 },
    classes: "term-edge to-seed",
  }));
  const edges: ElementDefinition[] = response.edges
    .filter((edge) => byId.has(edge.source) && byId.has(edge.target))
    .map((edge) => ({
      group: "edges",
      data: {
        id: edgeId(edge),
        source: String(edge.source),
        target: String(edge.target),
        width: edgeWidth(edge.weight),
      },
      classes: `to-${colorClass(byId.get(edge.target)!)}`,
    }));
  return [term, ...nodes, ...termEdges, ...edges];
}

export interface Connection {
  /** Identificador único de la conexión dentro del panel. */
  key: string;
  /** El nodo del otro extremo. */
  nodeId: number;
  /** Texto a mostrar: la referencia del otro extremo, con rango si la arista lo tiene. */
  label: string;
  weight: number;
  /** "out": el versículo seleccionado remite al otro. "in": el otro remite a él. */
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

/**
 * Relaciones del panel: una por versículo relacionado aunque haya referencia en los dos
 * sentidos. Se queda la de más peso y conserva el rango si alguna de las dos lo tiene.
 */
export function relationsOf(nodeId: number, response: SearchResponse): Connection[] {
  const byNode = new Map<number, Connection>();
  for (const connection of connectionsOf(nodeId, response)) {
    const kept = byNode.get(connection.nodeId);
    if (!kept) {
      byNode.set(connection.nodeId, connection);
    } else if (kept.rangeEndId === null && connection.rangeEndId !== null) {
      byNode.set(connection.nodeId, {
        ...kept,
        label: connection.label,
        rangeEndId: connection.rangeEndId,
      });
    }
  }
  return [...byNode.values()];
}

/** Versículos cuya frase se pide a la API: sin repetir, en el orden del panel y como máximo 30. */
export function explanationTargets(connections: Connection[]): number[] {
  return [...new Set(connections.map((c) => c.nodeId))].slice(0, MAX_EXPLANATIONS);
}

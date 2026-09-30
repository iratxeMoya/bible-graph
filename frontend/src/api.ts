export interface GraphNode {
  id: number;
  ref: string;
  label: string;
  book: string;
  testament: "AT" | "NT";
  text: string;
  is_seed: boolean;
  hop: number;
}

export interface GraphEdge {
  source: number;
  target: number;
  weight: number;
  target_end_id: number | null;
  target_label: string;
}

export interface SearchResponse {
  query: string;
  total_matches: number;
  truncated: boolean;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface PassageVerse {
  id: number;
  ref: string;
  text: string;
}

export interface Passage {
  ref: string;
  verses: PassageVerse[];
}

export interface SearchParams {
  q: string;
  seeds: number;
  neighbors: number;
}

const DEFAULT_API_URL = "http://localhost:8000";

export function apiBase(configured: string | undefined): string {
  return (configured?.trim() || DEFAULT_API_URL).replace(/\/+$/, "");
}

export function searchUrl(base: string, params: SearchParams): string {
  const query = new URLSearchParams({
    q: params.q,
    seeds: String(params.seeds),
    neighbors: String(params.neighbors),
  });
  return `${base}/api/search?${query}`;
}

export function passageUrl(base: string, id: number, endId: number | null): string {
  return endId === null ? `${base}/api/verses/${id}` : `${base}/api/verses/${id}?end=${endId}`;
}

const API_BASE = apiBase(import.meta.env?.VITE_API_URL);

async function getJson<T>(url: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal });
  if (!response.ok) {
    throw new Error(`La API respondió ${response.status}`);
  }
  return (await response.json()) as T;
}

export function searchGraph(params: SearchParams, signal: AbortSignal): Promise<SearchResponse> {
  return getJson<SearchResponse>(searchUrl(API_BASE, params), signal);
}

export function fetchPassage(
  id: number,
  endId: number | null,
  signal: AbortSignal,
): Promise<Passage> {
  return getJson<Passage>(passageUrl(API_BASE, id, endId), signal);
}

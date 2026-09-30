import { describe, expect, it } from "vitest";
import { apiBase, passageUrl, searchUrl, type SearchResponse } from "./api";
import { connectionsOf, edgeWidth, toElements } from "./graph";

const ROM = 45003024;
const EPH = 49002008;
const TIT = 56003005;
const TIT_END = 56003007;
const GEN = 1001001;

const response: SearchResponse = {
  query: "gracia",
  total_matches: 2,
  truncated: false,
  nodes: [
    { id: ROM, ref: "Romanos 3:24", label: "Ro 3:24", book: "Romanos", testament: "NT", text: "…", is_seed: true, hop: 0 },
    { id: EPH, ref: "Efesios 2:8", label: "Ef 2:8", book: "Efesios", testament: "NT", text: "…", is_seed: true, hop: 0 },
    { id: TIT, ref: "Tito 3:5", label: "Tit 3:5", book: "Tito", testament: "NT", text: "…", is_seed: false, hop: 1 },
    { id: GEN, ref: "Génesis 1:1", label: "Gn 1:1", book: "Génesis", testament: "AT", text: "…", is_seed: false, hop: 1 },
  ],
  edges: [
    { source: ROM, target: EPH, weight: 40, target_end_id: null, target_label: "Ef 2:8" },
    { source: EPH, target: ROM, weight: 35, target_end_id: null, target_label: "Ro 3:24" },
    { source: ROM, target: TIT, weight: 30, target_end_id: TIT_END, target_label: "Tit 3:5-7" },
    { source: GEN, target: ROM, weight: 50, target_end_id: null, target_label: "Ro 3:24" },
  ],
};

describe("toElements", () => {
  it("creates one element per node and per edge, with string ids", () => {
    const elements = toElements(response);
    expect(elements.filter((e) => e.group === "nodes")).toHaveLength(4);
    expect(elements.filter((e) => e.group === "edges")).toHaveLength(4);
    expect(elements[0].data).toEqual({ id: String(ROM), label: "Ro 3:24" });
  });

  it("marks seeds, neighbors and testament with classes", () => {
    const classes = Object.fromEntries(toElements(response).map((e) => [e.data.id, e.classes]));
    expect(classes[String(ROM)]).toBe("seed nt");
    expect(classes[String(TIT)]).toBe("neighbor nt");
    expect(classes[String(GEN)]).toBe("neighbor at");
  });

  it("gives opposite edges between the same pair different ids", () => {
    const ids = toElements(response)
      .filter((e) => e.group === "edges")
      .map((e) => e.data.id);
    expect(new Set(ids).size).toBe(4);
  });

  it("drops edges whose ends are not among the nodes", () => {
    const dangling: SearchResponse = {
      ...response,
      edges: [{ source: ROM, target: 99, weight: 3, target_end_id: null, target_label: "?" }],
    };
    expect(toElements(dangling).filter((e) => e.group === "edges")).toHaveLength(0);
  });

  it("returns nothing for an empty response", () => {
    expect(toElements({ ...response, nodes: [], edges: [] })).toEqual([]);
  });
});

describe("edgeWidth", () => {
  it("grows with the logarithm of the weight", () => {
    expect(edgeWidth(1)).toBe(1);
    expect(edgeWidth(10)).toBe(3);
    expect(edgeWidth(100)).toBe(5);
  });

  it("stays within bounds for zero, negative and huge weights", () => {
    expect(edgeWidth(0)).toBe(1);
    expect(edgeWidth(-5)).toBe(1);
    expect(edgeWidth(1_000_000)).toBe(8);
  });
});

describe("connectionsOf", () => {
  it("lists outgoing and incoming connections from heaviest to lightest", () => {
    const connections = connectionsOf(ROM, response);
    expect(connections.map((c) => [c.label, c.weight, c.direction])).toEqual([
      ["Gn 1:1", 50, "in"],
      ["Ef 2:8", 40, "out"],
      ["Ef 2:8", 35, "in"],
      ["Tit 3:5-7", 30, "out"],
    ]);
    expect(new Set(connections.map((c) => c.key)).size).toBe(4);
  });

  it("keeps the range end only on outgoing edges that point to a range", () => {
    const connections = connectionsOf(ROM, response);
    expect(connections.find((c) => c.nodeId === TIT)?.rangeEndId).toBe(TIT_END);
    expect(connections.find((c) => c.nodeId === GEN)?.rangeEndId).toBeNull();
    expect(connectionsOf(TIT, response)).toEqual([
      { key: `in-e${ROM}-${TIT}`, nodeId: ROM, label: "Ro 3:24", weight: 30, direction: "in", rangeEndId: null },
    ]);
  });

  it("returns nothing for an unknown node", () => {
    expect(connectionsOf(12345, response)).toEqual([]);
  });
});

describe("api urls", () => {
  it("uses the configured base without trailing slashes, or the local default", () => {
    expect(apiBase("https://api.example.com/")).toBe("https://api.example.com");
    expect(apiBase(undefined)).toBe("http://localhost:8000");
    expect(apiBase("  ")).toBe("http://localhost:8000");
  });

  it("encodes the search term", () => {
    expect(searchUrl("http://x", { q: "vida eterna & más", seeds: 25, neighbors: 8 })).toBe(
      "http://x/api/search?q=vida+eterna+%26+m%C3%A1s&seeds=25&neighbors=8",
    );
  });

  it("builds verse and range urls", () => {
    expect(passageUrl("http://x", TIT, null)).toBe(`http://x/api/verses/${TIT}`);
    expect(passageUrl("http://x", TIT, TIT_END)).toBe(`http://x/api/verses/${TIT}?end=${TIT_END}`);
  });
});

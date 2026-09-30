import { describe, expect, it } from "vitest";
import { apiBase, explanationsUrl, passageUrl, searchUrl, type SearchResponse } from "./api";
import {
  chunks,
  connectionsOf,
  EXPLANATION_CHUNK,
  edgeWidth,
  explanationTargets,
  MAX_EXPLANATIONS,
  relationsOf,
  TERM_ID,
  toElements,
} from "./graph";

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
    { id: ROM, ref: "Romanos 3:24", label: "Ro 3:24", book: "Romanos", testament: "NT", text: "Siendo justificados gratuitamente por su gracia, por la redención", is_seed: true, hop: 0 },
    { id: EPH, ref: "Efesios 2:8", label: "Ef 2:8", book: "Efesios", testament: "NT", text: "Porque por gracia sois salvos", is_seed: true, hop: 0 },
    { id: TIT, ref: "Tito 3:5", label: "Tit 3:5", book: "Tito", testament: "NT", text: "No por obras", is_seed: false, hop: 1 },
    { id: GEN, ref: "Génesis 1:1", label: "Gn 1:1", book: "Génesis", testament: "AT", text: "EN el principio", is_seed: false, hop: 1 },
  ],
  edges: [
    { source: ROM, target: EPH, weight: 40, target_end_id: null, target_label: "Ef 2:8" },
    { source: EPH, target: ROM, weight: 35, target_end_id: null, target_label: "Ro 3:24" },
    { source: ROM, target: TIT, weight: 30, target_end_id: TIT_END, target_label: "Tit 3:5-7" },
    { source: GEN, target: ROM, weight: 50, target_end_id: null, target_label: "Ro 3:24" },
  ],
};

const byId = () => Object.fromEntries(toElements(response).map((e) => [e.data.id, e]));

describe("toElements", () => {
  it("adds the search term as a central node joined to every seed", () => {
    const elements = byId();
    expect(elements[TERM_ID].data).toEqual({ id: TERM_ID, label: "Gracia", snippet: "2 pasajes" });
    expect(elements[TERM_ID].classes).toBe("term");
    expect(elements[`t${ROM}`].data).toMatchObject({ source: TERM_ID, target: String(ROM) });
    expect(elements[`t${EPH}`].classes).toBe("term-edge to-seed");
    expect(elements[`t${TIT}`]).toBeUndefined();
  });

  it("creates one element per verse and per edge, with string ids and a snippet", () => {
    const elements = toElements(response);
    expect(elements.filter((e) => e.group === "nodes")).toHaveLength(5);
    expect(elements.filter((e) => e.group === "edges")).toHaveLength(6);
    expect(byId()[String(ROM)].data).toEqual({
      id: String(ROM),
      label: "Ro 3:24",
      snippet: "Siendo justificados gratuitamente por su…",
    });
  });

  it("colors seeds in amber and neighbors by book group", () => {
    const elements = byId();
    expect(elements[String(ROM)].classes).toBe("seed c-seed");
    expect(elements[String(TIT)].classes).toBe("neighbor c-cartas");
    expect(elements[String(GEN)].classes).toBe("neighbor c-ley");
  });

  it("colors each edge after its target", () => {
    const elements = byId();
    expect(elements[`e${ROM}-${TIT}`].classes).toBe("to-cartas");
    expect(elements[`e${GEN}-${ROM}`].classes).toBe("to-seed");
  });

  it("drops edges whose ends are not among the nodes", () => {
    const dangling: SearchResponse = {
      ...response,
      edges: [{ source: ROM, target: 99, weight: 3, target_end_id: null, target_label: "?" }],
    };
    const edges = toElements(dangling).filter((e) => e.group === "edges");
    expect(edges.map((e) => e.data.id)).toEqual([`t${ROM}`, `t${EPH}`]);
  });

  it("returns nothing for an empty response", () => {
    expect(toElements({ ...response, nodes: [], edges: [] })).toEqual([]);
  });

  it("says pasaje in singular for one match", () => {
    const one = { ...response, total_matches: 1 };
    expect(toElements(one)[0].data.snippet).toBe("1 pasaje");
  });
});

describe("edgeWidth", () => {
  it("grows with the logarithm of the weight", () => {
    expect(edgeWidth(1)).toBe(0.6);
    expect(edgeWidth(10)).toBe(1.8);
    expect(edgeWidth(100)).toBe(3);
  });

  it("stays within bounds for zero, negative and huge weights", () => {
    expect(edgeWidth(0)).toBe(0.6);
    expect(edgeWidth(-5)).toBe(0.6);
    expect(edgeWidth(1_000_000)).toBe(4);
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
  });

  it("returns nothing for an unknown node", () => {
    expect(connectionsOf(12345, response)).toEqual([]);
  });
});

describe("explanationTargets", () => {
  it("asks once per verse, in panel order", () => {
    expect(explanationTargets(connectionsOf(ROM, response))).toEqual([GEN, EPH, TIT]);
  });

  it("asks for at most 30 verses", () => {
    const many = Array.from({ length: 40 }, (_, i) => ({
      key: `k${i}`, nodeId: 1001001 + i, label: "", weight: 40 - i, direction: "out" as const, rangeEndId: null,
    }));
    expect(explanationTargets(many)).toHaveLength(MAX_EXPLANATIONS);
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

  it("builds the explanations url", () => {
    expect(explanationsUrl("http://x", ROM, [EPH, TIT])).toBe(
      `http://x/api/explanations?verse=${ROM}&others=${EPH}%2C${TIT}`,
    );
  });
});

describe("relationsOf", () => {
  it("merges both directions into one row per verse, keeping the heaviest", () => {
    const relations = relationsOf(ROM, response);
    expect(relations.map((r) => [r.nodeId, r.weight, r.direction])).toEqual([
      [GEN, 50, "in"],
      [EPH, 40, "out"],
      [TIT, 30, "out"],
    ]);
  });

  it("keeps the range when only the lighter direction has it", () => {
    const withRange: SearchResponse = {
      ...response,
      edges: [
        { source: TIT, target: ROM, weight: 60, target_end_id: null, target_label: "Ro 3:24" },
        { source: ROM, target: TIT, weight: 30, target_end_id: TIT_END, target_label: "Tit 3:5-7" },
      ],
    };
    expect(relationsOf(ROM, withRange)).toEqual([
      { key: `in-e${TIT}-${ROM}`, nodeId: TIT, label: "Tit 3:5-7", weight: 60, direction: "in", rangeEndId: TIT_END },
    ]);
  });
});

describe("chunks", () => {
  it("splits a list into groups of the given size, keeping the order", () => {
    expect(chunks([1, 2, 3, 4, 5], 2)).toEqual([[1, 2], [3, 4], [5]]);
    expect(chunks([], 8)).toEqual([]);
    expect(chunks([1, 2], 8)).toEqual([[1, 2]]);
  });

  it("asks for the explanations of a verse in groups of 8", () => {
    expect(EXPLANATION_CHUNK).toBe(8);
  });
});

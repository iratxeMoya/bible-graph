import { describe, expect, it } from "vitest";
import { BOOK_GROUPS, bookOf, groupOf } from "./groups";
import { capitalize, snippet } from "./text";
import { readTheme, writeTheme } from "./theme";

describe("groupOf", () => {
  it.each([
    [1001001, "ley"],
    [5034012, "ley"],
    [6001001, "historicos"],
    [17010003, "historicos"],
    [19023001, "poeticos"],
    [23001001, "profetas"],
    [39004006, "profetas"],
    [40001001, "evangelios"],
    [44028031, "evangelios"],
    [45003024, "cartas"],
    [66022021, "cartas"],
  ])("puts verse %i in %s", (id, group) => {
    expect(groupOf(id).id).toBe(group);
  });

  it("covers the 66 books exactly once", () => {
    const books = BOOK_GROUPS.flatMap((g) =>
      Array.from({ length: g.lastBook - g.firstBook + 1 }, (_, i) => g.firstBook + i),
    );
    expect(books).toEqual(Array.from({ length: 66 }, (_, i) => i + 1));
  });

  it("rejects ids outside the Bible", () => {
    expect(() => groupOf(67001001)).toThrow();
    expect(bookOf(43003016)).toBe(43);
  });
});

describe("snippet", () => {
  it("keeps short texts", () => {
    expect(snippet("Dios es amor.")).toBe("Dios es amor.");
  });

  it("cuts long texts at a word boundary and adds an ellipsis", () => {
    expect(snippet("La caridad es sufrida, es benigna; la caridad no tiene envidia")).toBe(
      "La caridad es sufrida, es benigna; la…",
    );
  });

  it("drops punctuation before the ellipsis and collapses spaces", () => {
    expect(snippet("Una   frase  corta,  y otra más", 12)).toBe("Una frase…");
  });

  it("cuts inside a word when there is no good boundary", () => {
    expect(snippet("Supercalifragilisticoespialidoso", 10)).toBe("Supercalif…");
  });
});

describe("capitalize", () => {
  it("uppercases the first letter", () => {
    expect(capitalize("amor")).toBe("Amor");
    expect(capitalize("émulo")).toBe("Émulo");
    expect(capitalize("")).toBe("");
  });
});

describe("theme storage", () => {
  const storage = (value: string | null) => ({
    getItem: () => value,
    setItem: (_key: string, v: string) => {
      value = v;
    },
  });

  it("defaults to dark", () => {
    expect(readTheme(storage(null))).toBe("dark");
    expect(readTheme(storage("violeta"))).toBe("dark");
    expect(readTheme(undefined)).toBe("dark");
  });

  it("reads light back after writing it", () => {
    const s = storage(null);
    writeTheme(s, "light");
    expect(readTheme(s)).toBe("light");
  });

  it("survives a storage that throws", () => {
    const broken = {
      getItem: () => {
        throw new Error("bloqueado");
      },
      setItem: () => {
        throw new Error("bloqueado");
      },
    };
    expect(readTheme(broken)).toBe("dark");
    expect(() => writeTheme(broken, "light")).not.toThrow();
  });
});

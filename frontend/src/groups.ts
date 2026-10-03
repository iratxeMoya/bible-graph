/** Grupos de libros de la Biblia. El color de cada uno está en la variable CSS `--group-<id>`. */
export interface BookGroup {
  id: string;
  name: string;
  firstBook: number;
  lastBook: number;
}

export const BOOK_GROUPS: BookGroup[] = [
  { id: "ley", name: "Ley", firstBook: 1, lastBook: 5 },
  { id: "historicos", name: "Históricos", firstBook: 6, lastBook: 17 },
  { id: "poeticos", name: "Poéticos", firstBook: 18, lastBook: 22 },
  { id: "profetas", name: "Profetas", firstBook: 23, lastBook: 39 },
  { id: "evangelios", name: "Evangelios y Hechos", firstBook: 40, lastBook: 44 },
  { id: "cartas", name: "Cartas y Apocalipsis", firstBook: 45, lastBook: 66 },
];

/** Libro de un versículo a partir de su ID BBCCCVVV (Juan 3:16 = 43003016). */
export function bookOf(verseId: number): number {
  return Math.floor(verseId / 1_000_000);
}

export function groupOf(verseId: number): BookGroup {
  const book = bookOf(verseId);
  const group = BOOK_GROUPS.find((g) => book >= g.firstBook && book <= g.lastBook);
  if (!group) throw new Error(`ID de versículo fuera de rango: ${verseId}`);
  return group;
}

export function groupVar(group: BookGroup): string {
  return `--group-${group.id}`;
}

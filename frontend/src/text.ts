export const SNIPPET_LENGTH = 40;

/** Comienzo de un texto, cortado en un límite de palabra y con "…" si se ha recortado. */
export function snippet(text: string, max = SNIPPET_LENGTH): string {
  const clean = text.replace(/\s+/g, " ").trim();
  if (clean.length <= max) return clean;
  // Un carácter más: si justo ahí hay un espacio, la última palabra cabe entera.
  const lastSpace = clean.slice(0, max + 1).lastIndexOf(" ");
  const base = lastSpace > max / 2 ? clean.slice(0, lastSpace) : clean.slice(0, max);
  return `${base.replace(/[\s,;:.]+$/, "")}…`;
}

/** "amor" → "Amor". */
export function capitalize(text: string): string {
  return text.charAt(0).toLocaleUpperCase("es") + text.slice(1);
}

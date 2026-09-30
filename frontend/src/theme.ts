export type Theme = "dark" | "light";

const STORAGE_KEY = "bible-graph-theme";

/** Tema guardado, o el oscuro si no hay ninguno o el almacenamiento no está disponible. */
export function readTheme(storage: Pick<Storage, "getItem"> | undefined): Theme {
  try {
    return storage?.getItem(STORAGE_KEY) === "light" ? "light" : "dark";
  } catch {
    return "dark";
  }
}

export function writeTheme(storage: Pick<Storage, "setItem"> | undefined, theme: Theme): void {
  try {
    storage?.setItem(STORAGE_KEY, theme);
  } catch {
    // Sin almacenamiento el tema dura lo que la pestaña.
  }
}

/** Aplica el tema al documento y lo recuerda. Hay que llamarla antes de pintar el grafo,
 * que lee sus colores de las variables CSS. */
export function applyTheme(storage: Pick<Storage, "setItem"> | undefined, theme: Theme): void {
  document.documentElement.dataset.theme = theme;
  writeTheme(storage, theme);
}

/** Lee el valor calculado de una variable CSS del documento (los colores del grafo). */
export function cssVar(name: string): string {
  return getComputedStyle(document.documentElement).getPropertyValue(name).trim();
}

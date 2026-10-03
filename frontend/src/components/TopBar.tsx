import { BookOpen, Menu, Moon, Sun } from "lucide-react";
import type { Theme } from "../theme";
import { SearchBar } from "./SearchBar";

interface Props {
  query: string;
  onSearch: (query: string) => void;
  theme: Theme;
  onToggleTheme: () => void;
  onToggleSidebar: () => void;
}

export function TopBar({ query, onSearch, theme, onToggleTheme, onToggleSidebar }: Props) {
  return (
    <header className="top-bar">
      <button
        type="button"
        className="icon-button menu-button"
        onClick={onToggleSidebar}
        aria-label="Mostrar controles"
      >
        <Menu size={18} />
      </button>
      <h1 className="brand">
        <BookOpen size={20} strokeWidth={1.6} aria-hidden="true" />
        <span>Biblia en red</span>
      </h1>
      <SearchBar query={query} onSearch={onSearch} />
      <button
        type="button"
        className="icon-button"
        onClick={onToggleTheme}
        aria-label={theme === "dark" ? "Cambiar a tema claro" : "Cambiar a tema oscuro"}
      >
        {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
      </button>
    </header>
  );
}

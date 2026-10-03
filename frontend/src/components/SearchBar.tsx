import { Search } from "lucide-react";
import { type FormEvent, useEffect, useState } from "react";

export const MIN_QUERY_LENGTH = 2;
export const MAX_QUERY_LENGTH = 100;

interface Props {
  query: string;
  onSearch: (query: string) => void;
}

export function SearchBar({ query, onSearch }: Props) {
  const [draft, setDraft] = useState(query);

  useEffect(() => setDraft(query), [query]);

  function submit(event: FormEvent) {
    event.preventDefault();
    const trimmed = draft.trim();
    if (trimmed.length >= MIN_QUERY_LENGTH) onSearch(trimmed);
  }

  return (
    <form className="search-bar" onSubmit={submit} role="search">
      <Search size={16} aria-hidden="true" />
      <input
        type="search"
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        placeholder="Busca un término: amor, gracia, perdón…"
        aria-label="Término o concepto bíblico"
        maxLength={MAX_QUERY_LENGTH}
        autoFocus
      />
    </form>
  );
}

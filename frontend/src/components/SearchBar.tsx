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

  const trimmed = draft.trim();
  const valid = trimmed.length >= MIN_QUERY_LENGTH;

  function submit(event: FormEvent) {
    event.preventDefault();
    if (valid) onSearch(trimmed);
  }

  return (
    <form className="search-bar" onSubmit={submit} role="search">
      <input
        type="search"
        value={draft}
        onChange={(event) => setDraft(event.target.value)}
        placeholder="gracia, perdón, justicia…"
        aria-label="Término o concepto bíblico"
        maxLength={MAX_QUERY_LENGTH}
        autoFocus
      />
      <button type="submit" disabled={!valid}>
        Buscar
      </button>
    </form>
  );
}

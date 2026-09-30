CREATE EXTENSION IF NOT EXISTS unaccent;

DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_ts_config WHERE cfgname = 'es_unaccent') THEN
    CREATE TEXT SEARCH CONFIGURATION es_unaccent (COPY = spanish);
    ALTER TEXT SEARCH CONFIGURATION es_unaccent
      ALTER MAPPING FOR hword, hword_part, word WITH unaccent, spanish_stem;
  END IF;
END
$$;

CREATE TABLE IF NOT EXISTS books (
  id        smallint PRIMARY KEY,
  osis      text UNIQUE NOT NULL,
  name_es   text NOT NULL,
  abbr_es   text NOT NULL,
  testament char(2) NOT NULL CHECK (testament IN ('AT', 'NT'))
);

CREATE TABLE IF NOT EXISTS verses (
  id      integer PRIMARY KEY,
  book_id smallint NOT NULL REFERENCES books,
  chapter smallint NOT NULL,
  verse   smallint NOT NULL,
  UNIQUE (book_id, chapter, verse)
);

CREATE TABLE IF NOT EXISTS verse_texts (
  verse_id    integer NOT NULL REFERENCES verses,
  translation text NOT NULL,
  text        text NOT NULL,
  tsv         tsvector GENERATED ALWAYS AS (to_tsvector('es_unaccent', text)) STORED,
  PRIMARY KEY (translation, verse_id)
);
CREATE INDEX IF NOT EXISTS verse_texts_tsv_idx ON verse_texts USING gin (tsv);

CREATE TABLE IF NOT EXISTS edges (
  from_verse_id   integer NOT NULL REFERENCES verses,
  to_verse_id     integer NOT NULL REFERENCES verses,
  to_end_verse_id integer REFERENCES verses,
  weight          integer NOT NULL,
  kind            text NOT NULL DEFAULT 'openbible',
  PRIMARY KEY (kind, from_verse_id, to_verse_id)
);
CREATE INDEX IF NOT EXISTS edges_from_idx ON edges (from_verse_id, weight DESC);
CREATE INDEX IF NOT EXISTS edges_to_idx ON edges (to_verse_id, weight DESC);

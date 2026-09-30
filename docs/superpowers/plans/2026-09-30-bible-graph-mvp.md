# bible-graph MVP: plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Objetivo:** una web app que busca un término bíblico en la Reina-Valera 1909 y muestra un grafo interactivo de los versículos que lo contienen y de sus referencias cruzadas.

**Arquitectura:** Postgres guarda los versículos (nodos) y las referencias cruzadas de OpenBible (aristas). Una API FastAPI busca semillas con full-text search en español y expande el grafo con una CTE recursiva. Un frontend React dibuja el grafo con Cytoscape.js. Todo corre en local con Docker Compose.

**Stack:** Python 3.12, FastAPI, psycopg 3 (SQL a mano, sin ORM), PostgreSQL 17, React 19, Vite, TypeScript, Cytoscape.js con `cytoscape-fcose`, Vitest, pytest, Docker Compose.

**Spec:** `docs/superpowers/specs/2026-09-30-bible-graph-mvp-design.md`. Léela antes de empezar.

**Procedencia del código:** todo el código de este plan se ha ejecutado ya de punta a punta en un entorno desechable (ingesta real, 105 tests de backend, 13 de frontend, build de las imágenes). Cópialo tal cual. Si un test no da el resultado que indica el plan, para e investiga antes de cambiar el código.

## Global Constraints

- Se trabaja en la rama `mvp`. No se hace commit en `main`.
- Todos los comandos se ejecutan desde la raíz del repo y dentro de Docker. No hace falta Python ni Node en la máquina.
- Los puertos 5432, 8000 y 5173 deben estar libres.
- Python 3.12. SQL a mano con psycopg 3. Sin ORM y sin Alembic.
- Texto bíblico: solo Reina-Valera 1909 (dominio público). Traducción fija `RV1909`.
- La atribución "Referencias cruzadas de OpenBible.info (CC-BY)" debe verse en el pie de la web.
- Interfaz, mensajes de error y comentarios del código en español.
- Los tests de la API usan la base de datos `bible_test`, nunca `bible`.
- ID de versículo: `libro × 1.000.000 + capítulo × 1.000 + versículo` (Juan 3:16 = `43003016`).
- Valores por defecto de la búsqueda: `seeds=25`, `neighbors=8`, `min_weight=1`, `hops=1`. Máximo 600 nodos por respuesta y 200 versículos por pasaje.
- Datos esperados tras la ingesta: 66 libros, 31.084 versículos, 344.542 aristas, 257 aristas descartadas.
- Cada commit termina con la línea `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Fuera de alcance: embeddings, filtros por libro o testamento, otras traducciones, cuentas de usuario, integración continua, y ejecutar el despliegue.

## Review Focus

Entradas y fallos que la spec implica y que más fácilmente afectarían a quien use la app. Cada uno tiene su comprobación en la tarea indicada.

1. **Términos con comillas, operadores, NUL o SQL.** La búsqueda debe devolver resultados o un 422, nunca un 500. Tests en la tarea 8 (`test_search_operators_and_quotes_do_not_break_the_query`, `test_invalid_parameters_are_rejected`).
2. **Base de datos dormida o inaccesible.** La API debe arrancar igualmente, `/health` debe responder 200 y el resto 503. Tests en la tarea 7 (`test_without_database_the_api_starts_and_health_db_is_503`).
3. **Ingesta repetida o interrumpida.** Repetirla deja el mismo resultado; si falla a mitad, la BD queda como estaba. Tests en la tarea 5 (`test_apply_schema_and_load_are_idempotent`, `test_load_rolls_back_everything_when_it_fails`).
4. **URLs de configuración con barra final o espacios.** `ALLOWED_ORIGINS` y `VITE_API_URL` deben funcionar igual. Tests en la tarea 1 (`test_settings_from_env_cleans_the_origin_list`) y en la tarea 10 (`uses the configured base without trailing slashes`).
5. **Respuestas que llegan desordenadas.** Al mover un slider varias veces seguidas, el grafo final debe corresponder al último valor, y el versículo seleccionado debe cerrarse si ya no está en el grafo. Comprobación manual en la tarea 11 (paso 7).

## Estructura de ficheros

```
bible-graph/
├── .gitignore                       tarea 1
├── docker-compose.yml               tarea 1 (db, api, ingest); tarea 10 (frontend)
├── .env.example                     tarea 12
├── render.yaml                      tarea 12
├── README.md                        tarea 12
├── docs/deploy.md                   tarea 12
├── backend/
│   ├── Dockerfile, .dockerignore    tarea 1
│   ├── requirements.txt             tarea 1
│   ├── requirements-dev.txt         tarea 1
│   ├── pyproject.toml               tarea 1   configuración de pytest
│   ├── sql/schema.sql               tarea 5   esquema idempotente
│   ├── app/
│   │   ├── config.py                tarea 1   Settings desde el entorno
│   │   ├── main.py                  tareas 1, 7, 8   create_app, /health, /health/db
│   │   ├── db.py                    tarea 7   pool y conexión con timeout
│   │   ├── refs.py                  tarea 8   formato de referencias
│   │   ├── schemas.py               tareas 8, 9   modelos de respuesta
│   │   ├── search.py                tareas 8, 9   SQL de búsqueda y pasajes
│   │   └── routes.py                tareas 8, 9   /api/search, /api/verses/{id}
│   ├── ingest/
│   │   ├── books.py                 tarea 2   los 66 libros e IDs de versículo
│   │   ├── bible_text.py            tarea 3   parseo de RV1909
│   │   ├── cross_refs.py            tarea 4   parseo de OpenBible
│   │   ├── load.py                  tarea 5   esquema y COPY
│   │   ├── download.py              tarea 6   descarga con caché
│   │   └── __main__.py              tarea 6   CLI
│   └── tests/                       un fichero de tests por módulo
└── frontend/
    ├── Dockerfile, .dockerignore    tarea 10
    ├── package.json, tsconfig.json, vite.config.ts, index.html   tarea 10
    └── src/
        ├── api.ts                   tarea 10  tipos y llamadas a la API
        ├── graph.ts                 tarea 10  respuesta → elementos de Cytoscape
        ├── graph.test.ts            tarea 10
        ├── cytoscape-fcose.d.ts     tarea 10
        ├── main.tsx, styles.css     tarea 10
        ├── App.tsx                  tarea 10 (provisional); tarea 11 (definitivo)
        └── components/              tarea 11  SearchBar, LimitControls, GraphView, VersePanel
```

---

### Task 1: Esqueleto del backend con Docker y `/health`

**Files:**
- Create: `.gitignore`
- Create: `docker-compose.yml`
- Create: `backend/Dockerfile`, `backend/.dockerignore`
- Create: `backend/requirements.txt`, `backend/requirements-dev.txt`, `backend/pyproject.toml`
- Create: `backend/app/__init__.py` (vacío), `backend/app/config.py`, `backend/app/main.py`
- Create: `backend/tests/__init__.py` (vacío), `backend/tests/conftest.py`
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Consumes: nada.
- Produces:
  - `app.config.Settings(database_url: str, allowed_origins: list[str])`, dataclass inmutable, con `Settings.from_env() -> Settings`.
  - `app.main.create_app(settings: Settings | None = None) -> FastAPI`. Guarda los ajustes en `app.state.settings`.
  - Fixture de pytest `client` (un `TestClient`).
  - Servicios de compose `db`, `api` e `ingest`. Comando de tests: `docker compose run --rm api pytest`.

- [ ] **Step 1: Crear `.gitignore`**

```text
.env
__pycache__/
*.pyc
.pytest_cache/
.venv/
backend/data/
node_modules/
dist/
```

- [ ] **Step 2: Crear los ficheros de dependencias y de pytest**

`backend/requirements.txt`:

```text
fastapi>=0.142,<1
uvicorn[standard]>=0.54,<1
psycopg[binary,pool]>=3.3,<4
```

`backend/requirements-dev.txt`:

```text
-r requirements.txt
pytest>=8.4,<9
httpx2>=2.13,<3
```

`httpx2` es el cliente HTTP que necesita `fastapi.testclient` en las versiones actuales de Starlette.

`backend/pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-p no:cacheprovider"
```

`-p no:cacheprovider` evita que pytest escriba `.pytest_cache` en el código montado desde el host.

- [ ] **Step 3: Crear `backend/Dockerfile` y `backend/.dockerignore`**

`backend/Dockerfile`:

```dockerfile
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    INGEST_CACHE_DIR=/cache

WORKDIR /app

# En local, compose pasa requirements-dev.txt para tener también pytest.
ARG REQUIREMENTS=requirements.txt
COPY requirements.txt requirements-dev.txt ./
RUN pip install -r ${REQUIREMENTS}

COPY . .

RUN useradd --create-home appuser && mkdir /cache && chown appuser /cache
USER appuser

EXPOSE 8000
# Render inyecta PORT; en local se usa 8000.
CMD ["sh", "-c", "exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
```

`backend/.dockerignore`:

```text
__pycache__/
*.pyc
.pytest_cache/
.venv/
data/
```

- [ ] **Step 4: Crear `docker-compose.yml`**

```yaml
x-backend: &backend
  build:
    context: ./backend
    args:
      REQUIREMENTS: requirements-dev.txt
  image: bible-graph-backend
  depends_on:
    db:
      condition: service_healthy

services:
  db:
    image: pgvector/pgvector:pg17
    environment:
      POSTGRES_USER: bible
      POSTGRES_PASSWORD: bible
      POSTGRES_DB: bible
    ports:
      - "5432:5432"
    volumes:
      - db-data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U bible -d bible"]
      interval: 2s
      timeout: 3s
      retries: 30

  api:
    <<: *backend
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
    environment:
      DATABASE_URL: postgresql://bible:bible@db:5432/bible
      ALLOWED_ORIGINS: http://localhost:5173
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app

  # Se lanza a demanda: docker compose run --rm ingest
  # Para cargar otra BD (Neon): INGEST_DATABASE_URL="postgresql://..." docker compose run --rm ingest
  ingest:
    <<: *backend
    profiles: ["tools"]
    command: python -m ingest
    environment:
      DATABASE_URL: ${INGEST_DATABASE_URL:-postgresql://bible:bible@db:5432/bible}
    volumes:
      - ./backend:/app
      - ingest-cache:/cache

volumes:
  db-data:
  ingest-cache:
```

El servicio `frontend` se añade en la tarea 10.

- [ ] **Step 5: Escribir los tests que fallan**

Crea `backend/app/__init__.py` y `backend/tests/__init__.py` vacíos.

`backend/tests/conftest.py`:

```python
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture
def client():
    app = create_app(Settings(database_url="", allowed_origins=["http://localhost:5173"]))
    with TestClient(app) as test_client:
        yield test_client
```

`backend/tests/test_health.py`:

```python
from app.config import Settings


def test_health_is_ok(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_cors_allows_only_configured_origins(client):
    allowed = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:5173"
    other = client.get("/health", headers={"Origin": "https://example.com"})
    assert "access-control-allow-origin" not in other.headers


def test_settings_from_env_cleans_the_origin_list(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.setenv("ALLOWED_ORIGINS", " https://a.pages.dev/ , http://localhost:5173,, ")
    settings = Settings.from_env()
    assert settings.database_url == "postgresql://x"
    assert settings.allowed_origins == ["https://a.pages.dev", "http://localhost:5173"]


def test_settings_from_env_defaults(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ALLOWED_ORIGINS", raising=False)
    settings = Settings.from_env()
    assert settings.database_url == ""
    assert settings.allowed_origins == ["http://localhost:5173"]
```

- [ ] **Step 6: Ejecutar los tests y comprobar que fallan**

Run: `docker compose build api && docker compose run --rm api pytest -q`
Expected: error al cargar `conftest.py` con `ModuleNotFoundError: No module named 'app.config'`.

- [ ] **Step 7: Implementar `config.py` y `main.py`**

`backend/app/config.py`:

```python
"""Configuración de la API a partir de variables de entorno."""

import os
from dataclasses import dataclass

DEFAULT_ORIGINS = "http://localhost:5173"


@dataclass(frozen=True)
class Settings:
    database_url: str
    allowed_origins: list[str]

    @classmethod
    def from_env(cls) -> "Settings":
        origins = os.environ.get("ALLOWED_ORIGINS", DEFAULT_ORIGINS)
        return cls(
            database_url=os.environ.get("DATABASE_URL", ""),
            allowed_origins=[o.strip().rstrip("/") for o in origins.split(",") if o.strip()],
        )
```

`backend/app/main.py`:

```python
"""Aplicación FastAPI."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="bible-graph")
    app.state.settings = settings or Settings.from_env()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app.state.settings.allowed_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 8: Ejecutar los tests y comprobar que pasan**

Run: `docker compose run --rm api pytest -q`
Expected: `4 passed`.

- [ ] **Step 9: Comprobar la API en marcha**

Run: `docker compose up -d api && sleep 3 && curl -s localhost:8000/health`
Expected: `{"status":"ok"}`

- [ ] **Step 10: Commit**

```bash
git add .gitignore docker-compose.yml backend
git commit -m "Add backend skeleton with Docker and health endpoint

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Tabla de los 66 libros e IDs de versículo

**Files:**
- Create: `backend/ingest/__init__.py` (vacío), `backend/ingest/books.py`
- Test: `backend/tests/test_books.py`

**Interfaces:**
- Consumes: nada.
- Produces, en `ingest.books`:
  - `Book(id: int, osis: str, ebible: str, name_es: str, abbr_es: str, testament: str)`, dataclass inmutable. `testament` es `"AT"` o `"NT"`.
  - `BOOKS: tuple[Book, ...]`, los 66 libros en orden canónico, con `id` de 1 a 66.
  - `BY_OSIS: dict[str, Book]` (códigos de OpenBible, como `"1John"`) y `BY_EBIBLE: dict[str, Book]` (códigos de eBible, como `"1JO"`).
  - `verse_id(book_id: int, chapter: int, verse: int) -> int`. Lanza `ValueError` si algún valor está fuera de rango.

Contexto: el fichero de eBible usa códigos de libro propios que no son los USFM estándar (`SOL`, `EZE`, `JOE`, `NAH`, `MAR`, `JOH`, `PHI`, `JAM`, `1JO`, `2JO`, `3JO`). Por eso la tabla los lleva escritos uno a uno.

- [ ] **Step 1: Escribir los tests que fallan**

Crea `backend/ingest/__init__.py` vacío.

`backend/tests/test_books.py`:

```python
import pytest

from ingest.books import BOOKS, BY_EBIBLE, BY_OSIS, verse_id


def test_there_are_66_books_with_unique_codes_and_names():
    assert len(BOOKS) == 66
    assert [b.id for b in BOOKS] == list(range(1, 67))
    for field in ("osis", "ebible", "name_es", "abbr_es"):
        assert len({getattr(b, field) for b in BOOKS}) == 66, field


def test_testament_boundary_is_between_malachi_and_matthew():
    assert BY_OSIS["Mal"].testament == "AT"
    assert BY_OSIS["Matt"].testament == "NT"
    assert sum(b.testament == "AT" for b in BOOKS) == 39


def test_ebible_codes_that_differ_from_usfm_map_to_the_right_book():
    assert BY_EBIBLE["SOL"].osis == "Song"
    assert BY_EBIBLE["EZE"].osis == "Ezek"
    assert BY_EBIBLE["JOH"].osis == "John"
    assert BY_EBIBLE["1JO"].osis == "1John"
    assert BY_EBIBLE["JAM"].name_es == "Santiago"


def test_verse_id_is_bbcccvvv():
    assert verse_id(43, 3, 16) == 43003016
    assert verse_id(1, 1, 1) == 1001001
    assert verse_id(19, 119, 176) == 19119176


@pytest.mark.parametrize("args", [(0, 1, 1), (67, 1, 1), (1, 0, 1), (1, 1, 0), (1, 1000, 1)])
def test_verse_id_rejects_out_of_range_parts(args):
    with pytest.raises(ValueError):
        verse_id(*args)
```

- [ ] **Step 2: Ejecutar los tests y comprobar que fallan**

Run: `docker compose run --rm api pytest tests/test_books.py -q`
Expected: `ModuleNotFoundError: No module named 'ingest.books'`.

- [ ] **Step 3: Implementar `backend/ingest/books.py`**

```python
"""Tabla fija de los 66 libros: códigos de OpenBible (OSIS) y de eBible, y nombres en español."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Book:
    id: int
    osis: str
    ebible: str
    name_es: str
    abbr_es: str
    testament: str


_ROWS = [
    ("Gen", "GEN", "Génesis", "Gn"),
    ("Exod", "EXO", "Éxodo", "Éx"),
    ("Lev", "LEV", "Levítico", "Lv"),
    ("Num", "NUM", "Números", "Nm"),
    ("Deut", "DEU", "Deuteronomio", "Dt"),
    ("Josh", "JOS", "Josué", "Jos"),
    ("Judg", "JDG", "Jueces", "Jue"),
    ("Ruth", "RUT", "Rut", "Rt"),
    ("1Sam", "1SA", "1 Samuel", "1 S"),
    ("2Sam", "2SA", "2 Samuel", "2 S"),
    ("1Kgs", "1KI", "1 Reyes", "1 R"),
    ("2Kgs", "2KI", "2 Reyes", "2 R"),
    ("1Chr", "1CH", "1 Crónicas", "1 Cr"),
    ("2Chr", "2CH", "2 Crónicas", "2 Cr"),
    ("Ezra", "EZR", "Esdras", "Esd"),
    ("Neh", "NEH", "Nehemías", "Neh"),
    ("Esth", "EST", "Ester", "Est"),
    ("Job", "JOB", "Job", "Job"),
    ("Ps", "PSA", "Salmos", "Sal"),
    ("Prov", "PRO", "Proverbios", "Pr"),
    ("Eccl", "ECC", "Eclesiastés", "Ec"),
    ("Song", "SOL", "Cantares", "Cnt"),
    ("Isa", "ISA", "Isaías", "Is"),
    ("Jer", "JER", "Jeremías", "Jer"),
    ("Lam", "LAM", "Lamentaciones", "Lm"),
    ("Ezek", "EZE", "Ezequiel", "Ez"),
    ("Dan", "DAN", "Daniel", "Dn"),
    ("Hos", "HOS", "Oseas", "Os"),
    ("Joel", "JOE", "Joel", "Jl"),
    ("Amos", "AMO", "Amós", "Am"),
    ("Obad", "OBA", "Abdías", "Abd"),
    ("Jonah", "JON", "Jonás", "Jon"),
    ("Mic", "MIC", "Miqueas", "Mi"),
    ("Nah", "NAH", "Nahúm", "Nah"),
    ("Hab", "HAB", "Habacuc", "Hab"),
    ("Zeph", "ZEP", "Sofonías", "Sof"),
    ("Hag", "HAG", "Hageo", "Hag"),
    ("Zech", "ZEC", "Zacarías", "Zac"),
    ("Mal", "MAL", "Malaquías", "Mal"),
    ("Matt", "MAT", "Mateo", "Mt"),
    ("Mark", "MAR", "Marcos", "Mr"),
    ("Luke", "LUK", "Lucas", "Lc"),
    ("John", "JOH", "Juan", "Jn"),
    ("Acts", "ACT", "Hechos", "Hch"),
    ("Rom", "ROM", "Romanos", "Ro"),
    ("1Cor", "1CO", "1 Corintios", "1 Co"),
    ("2Cor", "2CO", "2 Corintios", "2 Co"),
    ("Gal", "GAL", "Gálatas", "Gá"),
    ("Eph", "EPH", "Efesios", "Ef"),
    ("Phil", "PHI", "Filipenses", "Fil"),
    ("Col", "COL", "Colosenses", "Col"),
    ("1Thess", "1TH", "1 Tesalonicenses", "1 Ts"),
    ("2Thess", "2TH", "2 Tesalonicenses", "2 Ts"),
    ("1Tim", "1TI", "1 Timoteo", "1 Ti"),
    ("2Tim", "2TI", "2 Timoteo", "2 Ti"),
    ("Titus", "TIT", "Tito", "Tit"),
    ("Phlm", "PHM", "Filemón", "Flm"),
    ("Heb", "HEB", "Hebreos", "He"),
    ("Jas", "JAM", "Santiago", "Stg"),
    ("1Pet", "1PE", "1 Pedro", "1 P"),
    ("2Pet", "2PE", "2 Pedro", "2 P"),
    ("1John", "1JO", "1 Juan", "1 Jn"),
    ("2John", "2JO", "2 Juan", "2 Jn"),
    ("3John", "3JO", "3 Juan", "3 Jn"),
    ("Jude", "JUD", "Judas", "Jud"),
    ("Rev", "REV", "Apocalipsis", "Ap"),
]

FIRST_NT_BOOK = 40  # Mateo

BOOKS: tuple[Book, ...] = tuple(
    Book(i, osis, ebible, name, abbr, "AT" if i < FIRST_NT_BOOK else "NT")
    for i, (osis, ebible, name, abbr) in enumerate(_ROWS, start=1)
)
BY_OSIS: dict[str, Book] = {b.osis: b for b in BOOKS}
BY_EBIBLE: dict[str, Book] = {b.ebible: b for b in BOOKS}


def verse_id(book_id: int, chapter: int, verse: int) -> int:
    """ID BBCCCVVV: Juan 3:16 -> 43003016."""
    if not (1 <= book_id <= 66 and 1 <= chapter <= 999 and 1 <= verse <= 999):
        raise ValueError(f"referencia fuera de rango: {book_id} {chapter}:{verse}")
    return book_id * 1_000_000 + chapter * 1_000 + verse
```

- [ ] **Step 4: Ejecutar los tests y comprobar que pasan**

Run: `docker compose run --rm api pytest tests/test_books.py -q`
Expected: `9 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/ingest backend/tests/test_books.py
git commit -m "Add table of the 66 books and verse ids

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Parser del texto de RV1909

**Files:**
- Create: `backend/ingest/bible_text.py`
- Test: `backend/tests/test_bible_text.py`

**Interfaces:**
- Consumes: `ingest.books.BY_EBIBLE`, `ingest.books.verse_id`.
- Produces, en `ingest.bible_text`:
  - `URL`, `ZIP_MEMBER = "spaRV1909_vpl.txt"`, `TRANSLATION = "RV1909"`.
  - `VerseText(id: int, book_id: int, chapter: int, verse: int, text: str)`, dataclass inmutable.
  - `parse_line(line: str) -> VerseText | None`. Devuelve `None` para líneas vacías y para versículos sin texto. Lanza `ValueError` si la línea está mal formada.
  - `parse_vpl(lines: Iterable[str]) -> list[VerseText]`.

Contexto: cada línea del fichero es `COD cap:vers texto`, por ejemplo `GEN 1:1 EN el principio crió Dios...`. El fichero empieza con BOM. Dieciocho líneas traen la referencia sin texto (por ejemplo `NUM 12:16 `), porque la numeración de RV1909 difiere de la KJV en esos puntos. Esas líneas se omiten.

- [ ] **Step 1: Escribir los tests que fallan**

`backend/tests/test_bible_text.py`:

```python
import pytest

from ingest.bible_text import VerseText, parse_line, parse_vpl


def test_parse_line_reads_book_chapter_verse_and_text():
    assert parse_line("GEN 1:1 EN el principio crió Dios los cielos y la tierra.") == VerseText(
        1001001, 1, 1, 1, "EN el principio crió Dios los cielos y la tierra."
    )


def test_parse_line_strips_bom_and_newline():
    verse = parse_line("﻿GEN 1:1 EN el principio\r\n")
    assert verse is not None
    assert verse.id == 1001001
    assert verse.text == "EN el principio"


def test_parse_line_uses_ebible_book_codes():
    verse = parse_line("JOH 3:16 Porque de tal manera amó Dios al mundo")
    assert verse is not None
    assert verse.id == 43003016


def test_parse_line_keeps_spaces_inside_the_text():
    verse = parse_line("PSA 23:1 JEHOVÁ es mi pastor; nada me faltará.")
    assert verse is not None
    assert verse.text == "JEHOVÁ es mi pastor; nada me faltará."


@pytest.mark.parametrize("line", ["", "   ", "\n", "NUM 12:16", "NUM 12:16 ", "NUM 12:16   \n"])
def test_parse_line_skips_blank_lines_and_verses_without_text(line):
    assert parse_line(line) is None


@pytest.mark.parametrize("line", ["XXX 1:1 texto", "GEN 1-1 texto", "GEN uno:1 texto", "GEN"])
def test_parse_line_rejects_malformed_lines(line):
    with pytest.raises(ValueError):
        parse_line(line)


def test_parse_vpl_returns_only_verses_with_text():
    lines = ["﻿GEN 1:1 EN el principio", "NUM 12:16 ", "", "REV 22:21 La gracia sea con todos. Amén."]
    assert [v.id for v in parse_vpl(lines)] == [1001001, 66022021]
```

- [ ] **Step 2: Ejecutar los tests y comprobar que fallan**

Run: `docker compose run --rm api pytest tests/test_bible_text.py -q`
Expected: `ModuleNotFoundError: No module named 'ingest.bible_text'`.

- [ ] **Step 3: Implementar `backend/ingest/bible_text.py`**

```python
"""Parseo del fichero VPL de la Reina-Valera 1909 de eBible.org."""

from collections.abc import Iterable
from dataclasses import dataclass

from ingest.books import BY_EBIBLE, verse_id

URL = "https://ebible.org/Scriptures/spaRV1909_vpl.zip"
ZIP_MEMBER = "spaRV1909_vpl.txt"
TRANSLATION = "RV1909"


@dataclass(frozen=True)
class VerseText:
    id: int
    book_id: int
    chapter: int
    verse: int
    text: str


def parse_line(line: str) -> VerseText | None:
    """Convierte 'GEN 1:1 EN el principio...' en un VerseText.

    Devuelve None si la línea está vacía o si el versículo no tiene texto: el fichero
    trae 18 referencias sin texto allí donde la numeración de RV1909 difiere de la KJV.
    """
    line = line.lstrip("﻿").strip()
    if not line:
        return None
    parts = line.split(" ", 2)
    if len(parts) < 2:
        raise ValueError(f"línea de RV1909 mal formada: {line!r}")
    code, chapter_verse = parts[0], parts[1]
    text = parts[2].strip() if len(parts) == 3 else ""
    book = BY_EBIBLE.get(code)
    if book is None:
        raise ValueError(f"código de libro desconocido {code!r} en: {line!r}")
    try:
        chapter_s, verse_s = chapter_verse.split(":")
        chapter, verse = int(chapter_s), int(verse_s)
    except ValueError:
        raise ValueError(f"referencia mal formada {chapter_verse!r} en: {line!r}") from None
    if not text:
        return None
    return VerseText(verse_id(book.id, chapter, verse), book.id, chapter, verse, text)


def parse_vpl(lines: Iterable[str]) -> list[VerseText]:
    return [v for v in map(parse_line, lines) if v is not None]
```

- [ ] **Step 4: Ejecutar los tests y comprobar que pasan**

Run: `docker compose run --rm api pytest tests/test_bible_text.py -q`
Expected: `15 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/ingest/bible_text.py backend/tests/test_bible_text.py
git commit -m "Add RV1909 text parser

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Parser de las referencias cruzadas de OpenBible

**Files:**
- Create: `backend/ingest/cross_refs.py`
- Test: `backend/tests/test_cross_refs.py`

**Interfaces:**
- Consumes: `ingest.books.BY_OSIS`, `ingest.books.verse_id`.
- Produces, en `ingest.cross_refs`:
  - `URL`, `ZIP_MEMBER = "cross_references.txt"`, `KIND = "openbible"`.
  - `CrossRef(from_id: int, to_id: int, to_end_id: int | None, weight: int)`, dataclass inmutable. `to_end_id` es `None` si el destino es un solo versículo.
  - `parse_ref(ref: str) -> int`. Convierte `"Gen.1.1"` en `1001001`. Lanza `ValueError`.
  - `parse_line(line: str) -> CrossRef | None`. Devuelve `None` para la cabecera y las líneas vacías.
  - `parse_tsv(lines: Iterable[str]) -> list[CrossRef]`.

Contexto: el fichero es un TSV con cabecera `From Verse`, `To Verse`, `Votes`. El destino puede ser un rango, como `Prov.8.22-Prov.8.30`. La arista apunta al primer versículo del rango y guarda el último en `to_end_id`. Los votos pueden ser negativos.

- [ ] **Step 1: Escribir los tests que fallan**

`backend/tests/test_cross_refs.py`:

```python
import pytest

from ingest.cross_refs import CrossRef, parse_line, parse_ref, parse_tsv


def test_parse_ref_converts_osis_to_verse_id():
    assert parse_ref("Gen.1.1") == 1001001
    assert parse_ref("1John.1.5") == 62001005
    assert parse_ref("Ps.119.176") == 19119176


@pytest.mark.parametrize("ref", ["Gen.1", "Gen 1:1", "Tob.1.1", "Gen.a.1", ""])
def test_parse_ref_rejects_malformed_references(ref):
    with pytest.raises(ValueError):
        parse_ref(ref)


def test_parse_line_single_verse_target():
    assert parse_line("Gen.1.1\tRom.11.36\t62") == CrossRef(1001001, 45011036, None, 62)


def test_parse_line_range_target_keeps_first_verse_and_end():
    assert parse_line("Gen.1.1\tProv.8.22-Prov.8.30\t76\n") == CrossRef(
        1001001, 20008022, 20008030, 76
    )


def test_parse_line_range_across_books():
    assert parse_line("Gen.1.1\tPs.150.6-Prov.1.2\t3") == CrossRef(1001001, 19150006, 20001002, 3)


def test_parse_line_range_of_one_verse_is_not_a_range():
    assert parse_line("Gen.1.1\tRom.11.36-Rom.11.36\t5") == CrossRef(1001001, 45011036, None, 5)


def test_parse_line_negative_votes():
    ref = parse_line("Gen.1.1\tRom.11.36\t-4")
    assert ref is not None
    assert ref.weight == -4


@pytest.mark.parametrize(
    "line", ["", "\n", "From Verse\tTo Verse\tVotes\t#www.openbible.info CC-BY 2026-09-28"]
)
def test_parse_line_skips_header_and_blank_lines(line):
    assert parse_line(line) is None


@pytest.mark.parametrize("line", ["Gen.1.1\tRom.11.36", "Gen.1.1\tRom.11.36\tmuchos"])
def test_parse_line_rejects_malformed_rows(line):
    with pytest.raises(ValueError):
        parse_line(line)


def test_parse_tsv_skips_the_header():
    lines = ["From Verse\tTo Verse\tVotes\t#comment", "Gen.1.1\tRom.11.36\t62", ""]
    assert parse_tsv(lines) == [CrossRef(1001001, 45011036, None, 62)]
```

- [ ] **Step 2: Ejecutar los tests y comprobar que fallan**

Run: `docker compose run --rm api pytest tests/test_cross_refs.py -q`
Expected: `ModuleNotFoundError: No module named 'ingest.cross_refs'`.

- [ ] **Step 3: Implementar `backend/ingest/cross_refs.py`**

```python
"""Parseo del TSV de referencias cruzadas de OpenBible.info."""

from collections.abc import Iterable
from dataclasses import dataclass

from ingest.books import BY_OSIS, verse_id

URL = "https://a.openbible.info/data/cross-references.zip"
ZIP_MEMBER = "cross_references.txt"
KIND = "openbible"


@dataclass(frozen=True)
class CrossRef:
    from_id: int
    to_id: int
    to_end_id: int | None
    weight: int


def parse_ref(ref: str) -> int:
    """Convierte 'Gen.1.1' en 1001001."""
    parts = ref.split(".")
    if len(parts) != 3:
        raise ValueError(f"referencia mal formada: {ref!r}")
    osis, chapter, verse = parts
    book = BY_OSIS.get(osis)
    if book is None:
        raise ValueError(f"libro desconocido en la referencia: {ref!r}")
    return verse_id(book.id, int(chapter), int(verse))


def parse_line(line: str) -> CrossRef | None:
    """Convierte una fila del TSV. Devuelve None para la cabecera y las líneas vacías."""
    line = line.strip()
    if not line or line.startswith("From Verse"):
        return None
    fields = line.split("\t")
    if len(fields) < 3:
        raise ValueError(f"fila de referencias mal formada: {line!r}")
    source, target, votes = fields[0], fields[1], fields[2]
    start, _, end = target.partition("-")
    to_id = parse_ref(start)
    to_end_id = parse_ref(end) if end else None
    if to_end_id == to_id:
        to_end_id = None
    return CrossRef(parse_ref(source), to_id, to_end_id, int(votes))


def parse_tsv(lines: Iterable[str]) -> list[CrossRef]:
    return [r for r in map(parse_line, lines) if r is not None]
```

- [ ] **Step 4: Ejecutar los tests y comprobar que pasan**

Run: `docker compose run --rm api pytest tests/test_cross_refs.py -q`
Expected: `17 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/ingest/cross_refs.py backend/tests/test_cross_refs.py
git commit -m "Add OpenBible cross-references parser

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Esquema de la base de datos y carga

**Files:**
- Create: `backend/sql/schema.sql`
- Create: `backend/ingest/load.py`
- Create: `backend/tests/data.py`
- Modify: `backend/tests/conftest.py` (se reemplaza entero)
- Test: `backend/tests/test_load.py`

**Interfaces:**
- Consumes: `ingest.books.BOOKS`, `ingest.bible_text.VerseText`, `ingest.bible_text.TRANSLATION`, `ingest.cross_refs.CrossRef`, `ingest.cross_refs.KIND`.
- Produces:
  - Tablas `books`, `verses`, `verse_texts` (con la columna generada `tsv`) y `edges`, y la configuración de búsqueda `es_unaccent`.
  - `ingest.load.apply_schema(conn: psycopg.Connection) -> None`.
  - `ingest.load.resolve_edges(refs: list[CrossRef], verse_ids: set[int]) -> tuple[list[CrossRef], list[CrossRef]]`. Devuelve `(cargables, descartadas)`.
  - `ingest.load.load(conn: psycopg.Connection, verses: list[VerseText], edges: list[CrossRef]) -> None`. Reemplaza todo el contenido en una sola transacción.
  - `tests.data`: constantes de ID (`ROM_3_24`, `EPH_2_8`, `TIT_3_5`…), `VERSES: list[VerseText]` y `EDGES: list[CrossRef]`.
  - Fixtures de pytest `database_url` (de sesión; crea y carga `bible_test`) y `client` (ahora depende de `database_url`).

- [ ] **Step 1: Crear el dataset de tests**

`backend/tests/data.py`:

```python
"""Dataset mínimo para los tests de la API."""

from ingest.bible_text import VerseText
from ingest.books import BY_OSIS, verse_id
from ingest.cross_refs import CrossRef


def vid(osis: str, chapter: int, verse: int) -> int:
    return verse_id(BY_OSIS[osis].id, chapter, verse)


GEN_1_1 = vid("Gen", 1, 1)
GEN_1_3 = vid("Gen", 1, 3)
PS_32_1 = vid("Ps", 32, 1)
JOHN_1_14 = vid("John", 1, 14)
JOHN_1_16 = vid("John", 1, 16)
ROM_3_24 = vid("Rom", 3, 24)
ROM_8_32 = vid("Rom", 8, 32)
EPH_2_8 = vid("Eph", 2, 8)
EPH_2_9 = vid("Eph", 2, 9)
TIT_3_5 = vid("Titus", 3, 5)
TIT_3_6 = vid("Titus", 3, 6)
TIT_3_7 = vid("Titus", 3, 7)

# "gracia" aparece en Juan 1:14, Juan 1:16 (dos veces), Romanos 3:24 y Efesios 2:8.
# El texto de Tito 3:7 está alterado a propósito para que no la contenga.
_TEXTS = {
    GEN_1_1: "EN el principio crió Dios los cielos y la tierra.",
    GEN_1_3: "Y dijo Dios: Sea la luz: y fué la luz.",
    PS_32_1: "BIENAVENTURADO aquel cuyas iniquidades son perdonadas, y borrados sus pecados.",
    JOHN_1_14: "Y aquel Verbo fué hecho carne, y habitó entre nosotros, lleno de gracia y de verdad.",
    JOHN_1_16: "Porque de su plenitud tomamos todos, y gracia por gracia.",
    ROM_3_24: "Siendo justificados gratuitamente por su gracia, por la redención que es en Cristo Jesús;",
    ROM_8_32: "El que aun á su propio Hijo no perdonó, antes le entregó por todos nosotros.",
    EPH_2_8: "Porque por gracia sois salvos por la fe; y esto no de vosotros, pues es don de Dios:",
    EPH_2_9: "No por obras, para que nadie se gloríe.",
    TIT_3_5: "No por obras de justicia que nosotros habíamos hecho, mas por su misericordia nos salvó,",
    TIT_3_6: "El cual derramó en nosotros abundantemente por Jesucristo nuestro Salvador,",
    TIT_3_7: "Para que, justificados por su bondad, seamos hechos herederos de la vida eterna.",
}

VERSES = [
    VerseText(id_, id_ // 1_000_000, id_ // 1_000 % 1_000, id_ % 1_000, text)
    for id_, text in sorted(_TEXTS.items())
]

EDGES = [
    CrossRef(ROM_3_24, EPH_2_8, None, 40),
    CrossRef(EPH_2_8, ROM_3_24, None, 35),      # arista inversa de la anterior
    CrossRef(ROM_3_24, TIT_3_5, TIT_3_7, 30),   # destino con rango
    CrossRef(EPH_2_8, TIT_3_5, None, 15),       # arista entre dos vecinos de Romanos 3:24
    CrossRef(TIT_3_5, EPH_2_9, None, 20),       # Efesios 2:9 queda a dos saltos de Romanos 3:24
    CrossRef(GEN_1_1, JOHN_1_14, None, 50),     # arista entrante a una semilla
    CrossRef(JOHN_1_16, GEN_1_3, None, 0),      # peso 0: fuera con min_weight=1
    CrossRef(ROM_3_24, PS_32_1, None, 5),
    CrossRef(PS_32_1, ROM_8_32, None, 10),      # Romanos 8:32 queda a dos saltos
]
```

Las tareas 8 y 9 dependen de estos datos exactos. No los cambies.

- [ ] **Step 2: Reemplazar `backend/tests/conftest.py`**

```python
import os

import psycopg
import pytest
from fastapi.testclient import TestClient
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from app.config import Settings
from app.main import create_app
from ingest.load import apply_schema, load
from tests.data import EDGES, VERSES

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql://bible:bible@db:5432/bible_test"
)


@pytest.fixture(scope="session")
def database_url() -> str:
    """Crea (si hace falta) la BD de tests y la carga con el dataset mínimo."""
    dbname = conninfo_to_dict(TEST_DATABASE_URL)["dbname"]
    if not dbname.endswith("_test"):
        raise RuntimeError(f"La BD de tests debe acabar en '_test' y es {dbname!r}")
    admin = make_conninfo(TEST_DATABASE_URL, dbname="postgres")
    with psycopg.connect(admin, autocommit=True) as conn:
        exists = conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (dbname,)).fetchone()
        if not exists:
            conn.execute(f'CREATE DATABASE "{dbname}"')
    with psycopg.connect(TEST_DATABASE_URL) as conn:
        apply_schema(conn)
        load(conn, VERSES, EDGES)
    return TEST_DATABASE_URL


@pytest.fixture
def client(database_url: str):
    app = create_app(Settings(database_url=database_url, allowed_origins=["http://localhost:5173"]))
    with TestClient(app) as test_client:
        yield test_client
```

La comprobación del sufijo `_test` impide que los tests vacíen por error la base de datos de desarrollo.

- [ ] **Step 3: Escribir los tests que fallan**

`backend/tests/test_load.py`:

```python
import psycopg

from ingest.cross_refs import CrossRef
from ingest.load import apply_schema, load, resolve_edges
from tests.data import EDGES, ROM_3_24, TIT_3_5, TIT_3_7, VERSES

KNOWN = {1001001, 1001002, 1001003}


def test_resolve_edges_keeps_edges_between_known_verses():
    edge = CrossRef(1001001, 1001002, 1001003, 7)
    assert resolve_edges([edge], KNOWN) == ([edge], [])


def test_resolve_edges_drops_edges_with_unknown_source_or_target():
    unknown_source = CrossRef(9, 1001001, None, 1)
    unknown_target = CrossRef(1001001, 9, None, 1)
    kept, dropped = resolve_edges([unknown_source, unknown_target], KNOWN)
    assert kept == []
    assert dropped == [unknown_source, unknown_target]


def test_resolve_edges_keeps_edge_but_clears_unknown_range_end():
    kept, dropped = resolve_edges([CrossRef(1001001, 1001002, 9, 7)], KNOWN)
    assert kept == [CrossRef(1001001, 1001002, None, 7)]
    assert dropped == []


def test_apply_schema_and_load_are_idempotent(database_url):
    with psycopg.connect(database_url) as conn:
        for _ in range(2):
            apply_schema(conn)
            load(conn, VERSES, EDGES)
        counts = conn.execute(
            "SELECT (SELECT count(*) FROM books), (SELECT count(*) FROM verses),"
            " (SELECT count(*) FROM verse_texts), (SELECT count(*) FROM edges)"
        ).fetchone()
        assert counts == (66, len(VERSES), len(VERSES), len(EDGES))
        range_end = conn.execute(
            "SELECT to_end_verse_id FROM edges WHERE from_verse_id = %s AND to_verse_id = %s",
            (ROM_3_24, TIT_3_5),
        ).fetchone()
        assert range_end == (TIT_3_7,)


def test_load_rolls_back_everything_when_it_fails(database_url):
    broken = [*EDGES, CrossRef(ROM_3_24, 99, None, 1)]  # 99 no existe: viola la clave foránea
    with psycopg.connect(database_url) as conn:
        try:
            load(conn, VERSES[:2], broken)
        except psycopg.Error:
            conn.rollback()
        else:
            raise AssertionError("load debería haber fallado")
        assert conn.execute("SELECT count(*) FROM verses").fetchone() == (len(VERSES),)
        assert conn.execute("SELECT count(*) FROM edges").fetchone() == (len(EDGES),)
```

- [ ] **Step 4: Ejecutar los tests y comprobar que fallan**

Run: `docker compose run --rm api pytest tests/test_load.py -q`
Expected: error al cargar `conftest.py` con `ModuleNotFoundError: No module named 'ingest.load'`.

- [ ] **Step 5: Crear `backend/sql/schema.sql`**

```sql
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
```

`CREATE TEXT SEARCH CONFIGURATION` no admite `IF NOT EXISTS`, por eso va dentro del bloque `DO`.

- [ ] **Step 6: Implementar `backend/ingest/load.py`**

```python
"""Carga de libros, versículos y aristas en Postgres."""

from pathlib import Path

import psycopg

from ingest.bible_text import TRANSLATION, VerseText
from ingest.books import BOOKS
from ingest.cross_refs import KIND, CrossRef

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "sql" / "schema.sql"


def apply_schema(conn: psycopg.Connection) -> None:
    conn.execute(SCHEMA_PATH.read_text(encoding="utf-8"))
    conn.commit()


def resolve_edges(
    refs: list[CrossRef], verse_ids: set[int]
) -> tuple[list[CrossRef], list[CrossRef]]:
    """Separa las aristas cargables de las que apuntan a versículos inexistentes.

    Una arista se descarta si falta su origen o el primer versículo de su destino.
    Si solo falta el final del rango, se conserva como arista a un único versículo.
    """
    kept: list[CrossRef] = []
    dropped: list[CrossRef] = []
    for ref in refs:
        if ref.from_id not in verse_ids or ref.to_id not in verse_ids:
            dropped.append(ref)
        elif ref.to_end_id is not None and ref.to_end_id not in verse_ids:
            kept.append(CrossRef(ref.from_id, ref.to_id, None, ref.weight))
        else:
            kept.append(ref)
    return kept, dropped


def load(conn: psycopg.Connection, verses: list[VerseText], edges: list[CrossRef]) -> None:
    """Reemplaza todo el contenido de las cuatro tablas en una sola transacción."""
    with conn.transaction(), conn.cursor() as cur:
        cur.execute("TRUNCATE edges, verse_texts, verses, books")
        with cur.copy("COPY books (id, osis, name_es, abbr_es, testament) FROM STDIN") as copy:
            for b in BOOKS:
                copy.write_row((b.id, b.osis, b.name_es, b.abbr_es, b.testament))
        with cur.copy("COPY verses (id, book_id, chapter, verse) FROM STDIN") as copy:
            for v in verses:
                copy.write_row((v.id, v.book_id, v.chapter, v.verse))
        with cur.copy("COPY verse_texts (verse_id, translation, text) FROM STDIN") as copy:
            for v in verses:
                copy.write_row((v.id, TRANSLATION, v.text))
        with cur.copy(
            "COPY edges (from_verse_id, to_verse_id, to_end_verse_id, weight, kind) FROM STDIN"
        ) as copy:
            for e in edges:
                copy.write_row((e.from_id, e.to_id, e.to_end_id, e.weight, KIND))
        cur.execute("ANALYZE books, verses, verse_texts, edges")
```

- [ ] **Step 7: Ejecutar todos los tests y comprobar que pasan**

Run: `docker compose run --rm api pytest -q`
Expected: `50 passed`.

- [ ] **Step 8: Commit**

```bash
git add backend/sql backend/ingest/load.py backend/tests
git commit -m "Add database schema and loader

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Descarga y CLI de ingesta

**Files:**
- Create: `backend/ingest/download.py`
- Create: `backend/ingest/__main__.py`
- Test: `backend/tests/test_download.py`, `backend/tests/test_ingest_cli.py`

**Interfaces:**
- Consumes: `ingest.bible_text` (`URL`, `ZIP_MEMBER`, `parse_vpl`), `ingest.cross_refs` (`URL`, `ZIP_MEMBER`, `parse_tsv`), `ingest.load` (`apply_schema`, `load`, `resolve_edges`), `ingest.books.BOOKS`.
- Produces:
  - `ingest.download.fetch(url: str, cache_dir: Path, force: bool = False) -> Path`.
  - `ingest.download.read_zip_lines(zip_path: Path, member: str) -> list[str]`.
  - `ingest.__main__.check_counts(books: int, verses: int, edges: int) -> list[str]`.
  - `ingest.__main__.describe_target(database_url: str) -> str`.
  - `ingest.__main__.main(argv: list[str] | None = None) -> int`. Códigos de salida: 0 bien, 1 datos inesperados, 2 falta `DATABASE_URL`.
  - Comando `docker compose run --rm ingest`, que deja la BD `bible` cargada.

- [ ] **Step 1: Escribir los tests que fallan**

`backend/tests/test_download.py`:

```python
import zipfile

from ingest.download import fetch, read_zip_lines

UNREACHABLE_URL = "http://127.0.0.1:1/datos.zip"


def test_fetch_reuses_a_cached_file_without_downloading(tmp_path):
    cached = tmp_path / "datos.zip"
    cached.write_bytes(b"contenido")
    assert fetch(UNREACHABLE_URL, tmp_path) == cached
    assert cached.read_bytes() == b"contenido"


def test_failed_download_leaves_no_partial_file(tmp_path):
    cache_dir = tmp_path / "no" / "existe"
    try:
        fetch(UNREACHABLE_URL, cache_dir)
    except OSError:
        pass
    else:
        raise AssertionError("fetch debería haber fallado")
    assert cache_dir.is_dir()
    assert list(cache_dir.iterdir()) == []


def test_read_zip_lines_decodes_utf8_and_drops_the_bom(tmp_path):
    path = tmp_path / "texto.zip"
    content = "﻿GEN 1:1 EN el principio crió\r\nGEN 1:2 Y la tierra\n"
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("texto.txt", content.encode("utf-8"))
    assert read_zip_lines(path, "texto.txt") == [
        "GEN 1:1 EN el principio crió",
        "GEN 1:2 Y la tierra",
    ]
```

`backend/tests/test_ingest_cli.py`:

```python
from ingest.__main__ import check_counts, describe_target, main


def test_check_counts_accepts_the_expected_dataset():
    assert check_counts(books=66, verses=31_084, edges=344_542) == []


def test_check_counts_reports_each_problem():
    problems = check_counts(books=65, verses=100, edges=10)
    assert len(problems) == 3


def test_describe_target_hides_credentials():
    target = describe_target("postgresql://user:secreto@ep-x.eu-central-1.aws.neon.tech/neondb")
    assert target == "ep-x.eu-central-1.aws.neon.tech/neondb"
    assert "secreto" not in target


def test_main_needs_database_url(monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert main([]) == 2
    assert "DATABASE_URL" in capsys.readouterr().err
```

- [ ] **Step 2: Ejecutar los tests y comprobar que fallan**

Run: `docker compose run --rm api pytest tests/test_download.py tests/test_ingest_cli.py -q`
Expected: `ModuleNotFoundError: No module named 'ingest.download'` y `No module named 'ingest.__main__'`.

- [ ] **Step 3: Implementar `backend/ingest/download.py`**

```python
"""Descarga con caché en disco y lectura de un fichero dentro de un zip."""

import io
import urllib.request
import zipfile
from pathlib import Path

USER_AGENT = "bible-graph-ingest/1.0"


def fetch(url: str, cache_dir: Path, force: bool = False) -> Path:
    """Descarga `url` a `cache_dir` y devuelve la ruta. Reutiliza el fichero si ya existe."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    target = cache_dir / url.rsplit("/", 1)[-1]
    if target.exists() and not force:
        return target
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    partial = target.with_suffix(target.suffix + ".part")
    with urllib.request.urlopen(request, timeout=60) as response:
        partial.write_bytes(response.read())
    partial.replace(target)
    return target


def read_zip_lines(zip_path: Path, member: str) -> list[str]:
    """Lee un fichero de texto UTF-8 (con o sin BOM) de dentro de un zip."""
    with zipfile.ZipFile(zip_path) as archive:
        with archive.open(member) as raw:
            return io.TextIOWrapper(raw, encoding="utf-8-sig").read().splitlines()
```

- [ ] **Step 4: Implementar `backend/ingest/__main__.py`**

```python
"""CLI de ingesta: python -m ingest [--force-download] [--cache-dir DIR]."""

import argparse
import os
import sys
from pathlib import Path

import psycopg
from psycopg.conninfo import conninfo_to_dict

from ingest import bible_text, cross_refs
from ingest.books import BOOKS
from ingest.download import fetch, read_zip_lines
from ingest.load import apply_schema, load, resolve_edges

EXPECTED_BOOKS = 66
EXPECTED_VERSES = 31_084
MIN_EDGES = 340_000
MAX_DROPPED_SHOWN = 20


def check_counts(books: int, verses: int, edges: int) -> list[str]:
    """Devuelve los motivos por los que los datos no son los esperados (vacío si todo cuadra)."""
    problems = []
    if books != EXPECTED_BOOKS:
        problems.append(f"se esperaban {EXPECTED_BOOKS} libros y hay {books}")
    if verses != EXPECTED_VERSES:
        problems.append(f"se esperaban {EXPECTED_VERSES} versículos y hay {verses}")
    if edges < MIN_EDGES:
        problems.append(f"se esperaban al menos {MIN_EDGES} aristas y hay {edges}")
    return problems


def describe_target(database_url: str) -> str:
    """Servidor y base de datos de destino, sin credenciales, para mostrarlo antes de cargar."""
    info = conninfo_to_dict(database_url)
    return f"{info.get('host', 'localhost')}/{info.get('dbname', '')}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ingest")
    parser.add_argument("--force-download", action="store_true")
    parser.add_argument(
        "--cache-dir", type=Path, default=Path(os.environ.get("INGEST_CACHE_DIR", "data"))
    )
    args = parser.parse_args(argv)

    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        print("Falta la variable de entorno DATABASE_URL", file=sys.stderr)
        return 2
    print(f"Destino: {describe_target(database_url)}")

    print("Descargando RV1909...")
    text_zip = fetch(bible_text.URL, args.cache_dir, args.force_download)
    print("Descargando referencias cruzadas de OpenBible...")
    refs_zip = fetch(cross_refs.URL, args.cache_dir, args.force_download)

    verses = bible_text.parse_vpl(read_zip_lines(text_zip, bible_text.ZIP_MEMBER))
    refs = cross_refs.parse_tsv(read_zip_lines(refs_zip, cross_refs.ZIP_MEMBER))
    edges, dropped = resolve_edges(refs, {v.id for v in verses})
    books_with_text = len({v.book_id for v in verses})

    problems = check_counts(books_with_text, len(verses), len(edges))
    if problems:
        for problem in problems:
            print(f"ERROR: {problem}", file=sys.stderr)
        print("No se ha cargado nada.", file=sys.stderr)
        return 1

    with psycopg.connect(database_url) as conn:
        apply_schema(conn)
        load(conn, verses, edges)

    print(f"Libros:              {len(BOOKS)}")
    print(f"Versículos:          {len(verses)}")
    print(f"Aristas cargadas:    {len(edges)}")
    print(f"Aristas descartadas: {len(dropped)} (apuntan a versículos que no existen en RV1909)")
    for ref in dropped[:MAX_DROPPED_SHOWN]:
        print(f"  {ref.from_id} -> {ref.to_id}")
    if len(dropped) > MAX_DROPPED_SHOWN:
        print(f"  ... y {len(dropped) - MAX_DROPPED_SHOWN} más")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Las comprobaciones de `check_counts` se hacen antes de abrir la conexión: una descarga corrupta no llega a tocar la BD.

- [ ] **Step 5: Ejecutar todos los tests y comprobar que pasan**

Run: `docker compose run --rm api pytest -q`
Expected: `57 passed`.

- [ ] **Step 6: Ejecutar la ingesta real**

Run: `docker compose run --rm ingest`
Expected: tarda menos de un minuto y la salida contiene estas líneas:

```
Destino: db/bible
Libros:              66
Versículos:          31084
Aristas cargadas:    344542
Aristas descartadas: 257 (apuntan a versículos que no existen en RV1909)
```

- [ ] **Step 7: Comprobar los datos y que la ingesta se puede repetir**

Run:

```bash
docker compose run --rm ingest | grep -E "Versículos|cargadas"
docker compose exec db psql -U bible -d bible -Atc "SELECT count(*) FROM verses; SELECT count(*) FROM edges; SELECT to_tsvector('es_unaccent', 'perdón perdonó redención');"
```

Expected: la segunda ingesta imprime los mismos números, y `psql` devuelve:

```
31084
344542
'perdon':1,2 'redencion':3
```

- [ ] **Step 8: Commit**

```bash
git add backend/ingest backend/tests
git commit -m "Add ingest CLI with cached downloads

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Pool de conexiones y `/health/db`

**Files:**
- Create: `backend/app/db.py`
- Modify: `backend/app/main.py` (se reemplaza entero)
- Test: `backend/tests/test_database.py`

**Interfaces:**
- Consumes: `app.config.Settings`.
- Produces:
  - `app.db.create_pool(database_url: str) -> AsyncConnectionPool`. Lo devuelve sin abrir. Las filas son diccionarios (`dict_row`).
  - `app.db.get_pool(request: Request) -> AsyncConnectionPool`, dependencia de FastAPI.
  - `app.db.query_connection(pool)`, gestor de contexto asíncrono que entrega una conexión dentro de una transacción con `statement_timeout` de 5 s.
  - `app.state.pool`, abierto en el `lifespan`.
  - `GET /health/db`: 200 `{"status": "ok"}` o 503.
  - Cualquier `psycopg.OperationalError` que salga de un endpoint se convierte en 503 `{"detail": "Base de datos no disponible"}`.

Contexto: la API irá en producción detrás del pooler de Neon (PgBouncer en modo transacción). Por eso se desactivan las sentencias preparadas y el `statement_timeout` se fija con `SET LOCAL` y no como opción de conexión. `PoolTimeout` y `QueryCanceled` son subclases de `OperationalError`, así que un solo manejador cubre BD caída, pool agotado y consulta cancelada por tiempo.

- [ ] **Step 1: Escribir los tests que fallan**

`backend/tests/test_database.py`:

```python
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app

UNREACHABLE = "postgresql://bible:bible@127.0.0.1:1/bible?connect_timeout=1"


def test_health_db_is_ok_when_the_database_answers(client):
    response = client.get("/health/db")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_without_database_the_api_starts_and_health_db_is_503():
    app = create_app(Settings(database_url=UNREACHABLE, allowed_origins=[]))
    with TestClient(app) as client:
        assert client.get("/health").status_code == 200
        response = client.get("/health/db")
        assert response.status_code == 503
        assert response.json() == {"detail": "Base de datos no disponible"}


def test_missing_database_url_fails_at_startup():
    app = create_app(Settings(database_url="", allowed_origins=[]))
    try:
        with TestClient(app):
            pass
    except RuntimeError as error:
        assert "DATABASE_URL" in str(error)
    else:
        raise AssertionError("la API debería negarse a arrancar sin DATABASE_URL")
```

- [ ] **Step 2: Ejecutar los tests y comprobar que fallan**

Run: `docker compose run --rm api pytest tests/test_database.py -q`
Expected: `3 failed`. Dos por `assert 404 == ...` (no existe `/health/db`) y uno con `la API debería negarse a arrancar sin DATABASE_URL`.

- [ ] **Step 3: Implementar `backend/app/db.py`**

```python
"""Pool de conexiones a Postgres."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import Request
from psycopg import AsyncConnection
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

POOL_MAX_SIZE = 5
POOL_TIMEOUT_SECONDS = 10
STATEMENT_TIMEOUT = "5s"


def create_pool(database_url: str) -> AsyncConnectionPool:
    """Crea el pool sin abrirlo.

    `prepare_threshold=None` desactiva las sentencias preparadas, que no funcionan a
    través del pooler de Neon (PgBouncer en modo transacción).
    """
    return AsyncConnectionPool(
        conninfo=database_url,
        min_size=1,
        max_size=POOL_MAX_SIZE,
        timeout=POOL_TIMEOUT_SECONDS,
        open=False,
        kwargs={"row_factory": dict_row, "prepare_threshold": None},
        check=AsyncConnectionPool.check_connection,
    )


def get_pool(request: Request) -> AsyncConnectionPool:
    return request.app.state.pool


@asynccontextmanager
async def query_connection(pool: AsyncConnectionPool) -> AsyncIterator[AsyncConnection]:
    """Conexión dentro de una transacción con `statement_timeout`.

    Se usa `SET LOCAL` y no un parámetro de conexión porque el pooler de Neon rechaza
    `statement_timeout` como opción de arranque.
    """
    async with pool.connection() as conn:
        async with conn.transaction():
            await conn.execute(f"SET LOCAL statement_timeout = '{STATEMENT_TIMEOUT}'")
            yield conn
```

- [ ] **Step 4: Reemplazar `backend/app/main.py`**

```python
"""Aplicación FastAPI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings
from app.db import create_pool

HEALTH_DB_TIMEOUT_SECONDS = 3


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings: Settings = app.state.settings
    if not settings.database_url:
        raise RuntimeError("Falta la variable de entorno DATABASE_URL")
    pool = create_pool(settings.database_url)
    # wait=False: la API arranca aunque la BD esté dormida o caída; /health no depende de ella.
    await pool.open(wait=False)
    app.state.pool = pool
    yield
    await pool.close()


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="bible-graph", lifespan=lifespan)
    app.state.settings = settings or Settings.from_env()
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app.state.settings.allowed_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    @app.exception_handler(psycopg.OperationalError)
    async def database_unavailable(request: Request, exc: psycopg.OperationalError) -> JSONResponse:
        # Cubre BD inaccesible, pool agotado (PoolTimeout) y statement_timeout (QueryCanceled).
        return JSONResponse(status_code=503, content={"detail": "Base de datos no disponible"})

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/db")
    async def health_db(request: Request) -> dict[str, str]:
        async with request.app.state.pool.connection(timeout=HEALTH_DB_TIMEOUT_SECONDS) as conn:
            await conn.execute("SELECT 1")
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 5: Ejecutar todos los tests y comprobar que pasan**

Run: `docker compose run --rm api pytest -q`
Expected: `60 passed`. El test de la BD inaccesible tarda unos 3 segundos.

- [ ] **Step 6: Comprobar la API en marcha**

Run: `sleep 2 && curl -s localhost:8000/health/db`
Expected: `{"status":"ok"}` (la API se recarga sola al guardar los ficheros).

- [ ] **Step 7: Commit**

```bash
git add backend/app backend/tests/test_database.py
git commit -m "Add connection pool and database health check

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Búsqueda léxica con expansión del grafo

**Files:**
- Create: `backend/app/refs.py`, `backend/app/schemas.py`, `backend/app/search.py`, `backend/app/routes.py`
- Modify: `backend/app/main.py` (dos líneas)
- Test: `backend/tests/test_refs.py`, `backend/tests/test_search.py`

**Interfaces:**
- Consumes: `app.db.get_pool`, `app.db.query_connection`, las tablas de la tarea 5, `tests.data`.
- Produces:
  - `app.refs.format_ref(book: str, chapter: int, verse: int, end_book: str | None = None, end_chapter: int | None = None, end_verse: int | None = None) -> str`.
  - `app.schemas.Node`, `Edge` y `SearchResponse` (modelos Pydantic; campos en el código).
  - `app.search.TRANSLATION = "RV1909"`, `app.search.MAX_NODES = 600`.
  - `app.search.search_graph(conn: AsyncConnection, q: str, seeds: int, neighbors: int, min_weight: int, hops: int) -> SearchResponse`.
  - `app.routes.router` (prefijo `/api`) y el alias `app.routes.Pool`.
  - `GET /api/search?q=&seeds=&neighbors=&min_weight=&hops=`.

Contexto sobre la consulta:
- `websearch_to_tsquery` nunca da error de sintaxis, escriba lo que escriba el usuario.
- Las semillas se ordenan por `ts_rank_cd` y, a igualdad, por los votos positivos que recibe el versículo como destino. Sin ese desempate, una palabra que aparece una vez por versículo devolvería siempre los primeros versículos del Génesis.
- La expansión mira las aristas en los dos sentidos. El `GROUP BY e.other` hace que un vecino unido por aristas en ambos sentidos cuente una sola vez.
- `MAX_NODES` se lee en cada llamada, y los tests lo cambian con `monkeypatch`. No lo conviertas en un valor incrustado en el SQL.

- [ ] **Step 1: Escribir los tests de `format_ref` que fallan**

`backend/tests/test_refs.py`:

```python
from app.refs import format_ref


def test_single_verse():
    assert format_ref("Tito", 3, 5) == "Tito 3:5"


def test_range_in_the_same_chapter():
    assert format_ref("Tit", 3, 5, "Tit", 3, 7) == "Tit 3:5-7"


def test_range_across_chapters():
    assert format_ref("Tit", 2, 14, "Tit", 3, 2) == "Tit 2:14-3:2"


def test_range_across_books():
    assert format_ref("Sal", 150, 6, "Pr", 1, 2) == "Sal 150:6-Pr 1:2"


def test_range_that_ends_where_it_starts_is_a_single_verse():
    assert format_ref("Tit", 3, 5, "Tit", 3, 5) == "Tit 3:5"
```

- [ ] **Step 2: Ejecutar y comprobar que fallan**

Run: `docker compose run --rm api pytest tests/test_refs.py -q`
Expected: `ModuleNotFoundError: No module named 'app.refs'`.

- [ ] **Step 3: Implementar `backend/app/refs.py`**

```python
"""Formato de referencias bíblicas: 'Tito 3:5', 'Tit 3:5-7'."""


def format_ref(
    book: str,
    chapter: int,
    verse: int,
    end_book: str | None = None,
    end_chapter: int | None = None,
    end_verse: int | None = None,
) -> str:
    """Formatea un versículo o un rango. `book` es el nombre o la abreviatura a mostrar."""
    start = f"{book} {chapter}:{verse}"
    if end_book is None or end_chapter is None or end_verse is None:
        return start
    if end_book != book:
        return f"{start}-{end_book} {end_chapter}:{end_verse}"
    if end_chapter != chapter:
        return f"{start}-{end_chapter}:{end_verse}"
    if end_verse != verse:
        return f"{start}-{end_verse}"
    return start
```

- [ ] **Step 4: Ejecutar y comprobar que pasan**

Run: `docker compose run --rm api pytest tests/test_refs.py -q`
Expected: `5 passed`.

- [ ] **Step 5: Escribir los tests de la búsqueda que fallan**

`backend/tests/test_search.py`:

```python
import pytest

from app import search
from tests.data import (
    EPH_2_8,
    EPH_2_9,
    GEN_1_1,
    GEN_1_3,
    JOHN_1_14,
    JOHN_1_16,
    PS_32_1,
    ROM_3_24,
    ROM_8_32,
    TIT_3_5,
    TIT_3_7,
)


def get(client, **params):
    response = client.get("/api/search", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def ids(body, *, seeds_only=False):
    return {n["id"] for n in body["nodes"] if n["is_seed"] or not seeds_only}


def edge_pairs(body):
    return {(e["source"], e["target"]) for e in body["edges"]}


def test_default_search_returns_seeds_and_direct_neighbors(client):
    body = get(client, q="gracia")
    assert body["query"] == "gracia"
    assert body["total_matches"] == 4
    assert body["truncated"] is False
    assert ids(body, seeds_only=True) == {JOHN_1_14, JOHN_1_16, ROM_3_24, EPH_2_8}
    assert ids(body) == {JOHN_1_14, JOHN_1_16, ROM_3_24, EPH_2_8, GEN_1_1, TIT_3_5, PS_32_1}


def test_node_fields(client):
    body = get(client, q="gracia")
    node = next(n for n in body["nodes"] if n["id"] == ROM_3_24)
    assert node == {
        "id": ROM_3_24,
        "ref": "Romanos 3:24",
        "label": "Ro 3:24",
        "book": "Romanos",
        "testament": "NT",
        "text": "Siendo justificados gratuitamente por su gracia, por la redención que es en Cristo Jesús;",
        "is_seed": True,
        "hop": 0,
    }
    neighbor = next(n for n in body["nodes"] if n["id"] == GEN_1_1)
    assert (neighbor["is_seed"], neighbor["hop"], neighbor["testament"]) == (False, 1, "AT")


def test_seeds_are_ranked_by_occurrences_then_by_incoming_votes(client):
    # Juan 1:16 dice "gracia" dos veces. Después: Juan 1:14 (50 votos entrantes),
    # Efesios 2:8 (40) y Romanos 3:24 (35).
    assert ids(get(client, q="gracia", seeds=1, neighbors=0)) == {JOHN_1_16}
    assert ids(get(client, q="gracia", seeds=2, neighbors=0)) == {JOHN_1_16, JOHN_1_14}
    assert ids(get(client, q="gracia", seeds=3, neighbors=0)) == {JOHN_1_16, JOHN_1_14, EPH_2_8}
    assert get(client, q="gracia", seeds=1, neighbors=0)["total_matches"] == 4


def test_search_ignores_accents_and_case(client):
    assert ids(get(client, q="REDENCION", neighbors=0)) == {ROM_3_24}


def test_search_matches_other_forms_of_the_word(client):
    # "perdón" encuentra "perdonadas" y "perdonó".
    assert ids(get(client, q="perdón", neighbors=0)) == {PS_32_1, ROM_8_32}


def test_neighbors_limits_each_node_to_its_heaviest_connections(client):
    # Romanos 3:24 <-> Efesios 2:8 existe en los dos sentidos y cuenta como un solo vecino.
    assert ids(get(client, q="redención", neighbors=1)) == {ROM_3_24, EPH_2_8}
    assert ids(get(client, q="redención", neighbors=2)) == {ROM_3_24, EPH_2_8, TIT_3_5}


def test_expansion_follows_edges_in_both_directions(client):
    # Génesis 1:1 -> Juan 1:14: desde Juan 1:14 se llega a Génesis 1:1 por la arista entrante.
    body = get(client, q="Verbo")
    assert ids(body) == {JOHN_1_14, GEN_1_1}
    assert edge_pairs(body) == {(GEN_1_1, JOHN_1_14)}


def test_min_weight_filters_nodes_and_edges(client):
    default = get(client, q="plenitud")
    assert ids(default) == {JOHN_1_16}
    assert default["edges"] == []
    with_zero = get(client, q="plenitud", min_weight=0)
    assert ids(with_zero) == {JOHN_1_16, GEN_1_3}
    assert edge_pairs(with_zero) == {(JOHN_1_16, GEN_1_3)}
    heavy = get(client, q="redención", min_weight=30)
    assert ids(heavy) == {ROM_3_24, EPH_2_8, TIT_3_5}
    assert edge_pairs(heavy) == {(ROM_3_24, EPH_2_8), (EPH_2_8, ROM_3_24), (ROM_3_24, TIT_3_5)}


def test_two_hops(client):
    body = get(client, q="redención", hops=2)
    hops = {n["id"]: n["hop"] for n in body["nodes"]}
    assert hops == {
        ROM_3_24: 0,
        EPH_2_8: 1,
        TIT_3_5: 1,
        PS_32_1: 1,
        EPH_2_9: 2,
        ROM_8_32: 2,
    }


def test_edges_between_neighbors_are_included(client):
    body = get(client, q="redención")
    assert (EPH_2_8, TIT_3_5) in edge_pairs(body)
    assert edge_pairs(body) == {
        (ROM_3_24, EPH_2_8),
        (EPH_2_8, ROM_3_24),
        (ROM_3_24, TIT_3_5),
        (EPH_2_8, TIT_3_5),
        (ROM_3_24, PS_32_1),
    }


def test_edge_fields_for_single_verse_and_range_targets(client):
    edges = {(e["source"], e["target"]): e for e in get(client, q="redención")["edges"]}
    assert edges[(ROM_3_24, EPH_2_8)] == {
        "source": ROM_3_24,
        "target": EPH_2_8,
        "weight": 40,
        "target_end_id": None,
        "target_label": "Ef 2:8",
    }
    assert edges[(ROM_3_24, TIT_3_5)]["target_end_id"] == TIT_3_7
    assert edges[(ROM_3_24, TIT_3_5)]["target_label"] == "Tit 3:5-7"


@pytest.mark.parametrize("q", ["xyzzy", "de la", "((("])
def test_no_matches_returns_an_empty_graph(client, q):
    assert get(client, q=q) == {
        "query": q,
        "total_matches": 0,
        "truncated": False,
        "nodes": [],
        "edges": [],
    }


def test_truncation_keeps_the_lowest_hops(client, monkeypatch):
    monkeypatch.setattr(search, "MAX_NODES", 3)
    body = get(client, q="gracia")
    assert body["truncated"] is True
    assert len(body["nodes"]) == 3
    assert all(n["is_seed"] for n in body["nodes"])
    node_ids = ids(body)
    assert all(s in node_ids and t in node_ids for s, t in edge_pairs(body))


def test_query_is_trimmed(client):
    assert get(client, q="  redención  ")["query"] == "redención"


@pytest.mark.parametrize(
    "params",
    [
        {},
        {"q": "a"},
        {"q": "   "},
        {"q": " a "},
        {"q": "x" * 101},
        {"q": "gra\x00cia"},
        {"q": "gracia", "seeds": 0},
        {"q": "gracia", "seeds": 101},
        {"q": "gracia", "neighbors": -1},
        {"q": "gracia", "neighbors": 21},
        {"q": "gracia", "min_weight": -1},
        {"q": "gracia", "hops": 0},
        {"q": "gracia", "hops": 3},
        {"q": "gracia", "seeds": "muchas"},
    ],
)
def test_invalid_parameters_are_rejected(client, params):
    assert client.get("/api/search", params=params).status_code == 422


def test_search_operators_and_quotes_do_not_break_the_query(client):
    assert ids(get(client, q='"gracia por gracia"', neighbors=0)) == {JOHN_1_16}
    assert get(client, q="'; DROP TABLE edges; --")["nodes"] == []
    assert get(client, q="gracia")["total_matches"] == 4
```

- [ ] **Step 6: Ejecutar y comprobar que fallan**

Run: `docker compose run --rm api pytest tests/test_search.py -q`
Expected: error de colección con `ImportError: cannot import name 'search' from 'app'`.

- [ ] **Step 7: Crear `backend/app/schemas.py`**

```python
"""Modelos de respuesta de la API."""

from typing import Literal

from pydantic import BaseModel


class Node(BaseModel):
    id: int
    ref: str
    label: str
    book: str
    testament: Literal["AT", "NT"]
    text: str
    is_seed: bool
    hop: int


class Edge(BaseModel):
    source: int
    target: int
    weight: int
    target_end_id: int | None
    target_label: str


class SearchResponse(BaseModel):
    query: str
    total_matches: int
    truncated: bool
    nodes: list[Node]
    edges: list[Edge]
```

- [ ] **Step 8: Crear `backend/app/search.py`**

```python
"""Búsqueda léxica, expansión del grafo y lectura de pasajes."""

from psycopg import AsyncConnection

from app.refs import format_ref
from app.schemas import Edge, Node, SearchResponse

TRANSLATION = "RV1909"
MAX_NODES = 600

# Las semillas se ordenan por relevancia léxica y, a igualdad, por los votos que
# reciben como destino de referencias cruzadas: sin ese desempate, una palabra que
# aparece una vez por versículo devolvería siempre los primeros versículos del Génesis.
NODES_SQL = """
WITH RECURSIVE query AS (
  SELECT websearch_to_tsquery('es_unaccent', %(q)s) AS tsq
),
matches AS (
  SELECT vt.verse_id AS id,
         ts_rank_cd(vt.tsv, query.tsq) AS rank,
         (SELECT coalesce(sum(e.weight), 0) FROM edges e
           WHERE e.to_verse_id = vt.verse_id AND e.weight > 0) AS votes
  FROM verse_texts vt, query
  WHERE vt.translation = %(translation)s AND vt.tsv @@ query.tsq
),
seeds AS (
  SELECT id FROM matches ORDER BY rank DESC, votes DESC, id LIMIT %(seeds)s
),
walk(id, hop) AS (
  SELECT id, 0 FROM seeds
  UNION
  SELECT n.id, w.hop + 1
  FROM walk w
  CROSS JOIN LATERAL (
    SELECT e.other AS id
    FROM (
      SELECT to_verse_id AS other, weight FROM edges WHERE from_verse_id = w.id
      UNION ALL
      SELECT from_verse_id AS other, weight FROM edges WHERE to_verse_id = w.id
    ) e
    WHERE e.weight >= %(min_weight)s AND e.other <> w.id
    GROUP BY e.other
    ORDER BY max(e.weight) DESC, e.other
    LIMIT %(neighbors)s
  ) n
  WHERE w.hop < %(hops)s
),
reached AS (
  SELECT id, min(hop) AS hop FROM walk GROUP BY id
),
capped AS (
  SELECT id, hop FROM reached ORDER BY hop, id LIMIT %(max_nodes)s
)
SELECT c.id, c.hop, b.name_es, b.abbr_es, b.testament, v.chapter, v.verse, vt.text,
       (SELECT count(*) FROM matches) AS total_matches,
       (SELECT count(*) FROM reached) AS total_reached
FROM capped c
JOIN verses v ON v.id = c.id
JOIN books b ON b.id = v.book_id
JOIN verse_texts vt ON vt.verse_id = c.id AND vt.translation = %(translation)s
ORDER BY c.hop, c.id
"""

EDGES_SQL = """
SELECT e.from_verse_id AS source, e.to_verse_id AS target, e.weight,
       e.to_end_verse_id AS target_end_id,
       tb.abbr_es AS abbr, tv.chapter, tv.verse,
       eb.abbr_es AS end_abbr, ev.chapter AS end_chapter, ev.verse AS end_verse
FROM edges e
JOIN verses tv ON tv.id = e.to_verse_id
JOIN books tb ON tb.id = tv.book_id
LEFT JOIN verses ev ON ev.id = e.to_end_verse_id
LEFT JOIN books eb ON eb.id = ev.book_id
WHERE e.from_verse_id = ANY(%(ids)s) AND e.to_verse_id = ANY(%(ids)s)
  AND e.weight >= %(min_weight)s
ORDER BY e.weight DESC, e.from_verse_id, e.to_verse_id
"""

async def search_graph(
    conn: AsyncConnection, q: str, seeds: int, neighbors: int, min_weight: int, hops: int
) -> SearchResponse:
    cur = await conn.execute(
        NODES_SQL,
        {
            "q": q,
            "translation": TRANSLATION,
            "seeds": seeds,
            "neighbors": neighbors,
            "min_weight": min_weight,
            "hops": hops,
            "max_nodes": MAX_NODES,
        },
    )
    node_rows = await cur.fetchall()
    if not node_rows:
        return SearchResponse(query=q, total_matches=0, truncated=False, nodes=[], edges=[])

    nodes = [
        Node(
            id=r["id"],
            ref=format_ref(r["name_es"], r["chapter"], r["verse"]),
            label=format_ref(r["abbr_es"], r["chapter"], r["verse"]),
            book=r["name_es"],
            testament=r["testament"],
            text=r["text"],
            is_seed=r["hop"] == 0,
            hop=r["hop"],
        )
        for r in node_rows
    ]
    cur = await conn.execute(
        EDGES_SQL, {"ids": [n.id for n in nodes], "min_weight": min_weight}
    )
    edges = [
        Edge(
            source=r["source"],
            target=r["target"],
            weight=r["weight"],
            target_end_id=r["target_end_id"],
            target_label=format_ref(
                r["abbr"], r["chapter"], r["verse"],
                r["end_abbr"], r["end_chapter"], r["end_verse"],
            ),
        )
        for r in await cur.fetchall()
    ]
    return SearchResponse(
        query=q,
        total_matches=node_rows[0]["total_matches"],
        truncated=node_rows[0]["total_reached"] > len(nodes),
        nodes=nodes,
        edges=edges,
    )
```

- [ ] **Step 9: Crear `backend/app/routes.py`**

```python
"""Endpoints de la API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query
from psycopg_pool import AsyncConnectionPool

from app import search
from app.db import get_pool, query_connection
from app.schemas import SearchResponse

router = APIRouter(prefix="/api")

Pool = Annotated[AsyncConnectionPool, Depends(get_pool)]


@router.get("/search")
async def search_endpoint(
    pool: Pool,
    q: Annotated[str, Query(max_length=100)],
    seeds: Annotated[int, Query(ge=1, le=100)] = 25,
    neighbors: Annotated[int, Query(ge=0, le=20)] = 8,
    min_weight: Annotated[int, Query(ge=0, le=100_000)] = 1,
    hops: Annotated[int, Query(ge=1, le=2)] = 1,
) -> SearchResponse:
    q = q.strip()
    if len(q) < 2:
        raise HTTPException(422, "El término de búsqueda debe tener al menos 2 caracteres")
    if "\x00" in q:
        raise HTTPException(422, "El término de búsqueda contiene caracteres no válidos")
    async with query_connection(pool) as conn:
        return await search.search_graph(conn, q, seeds, neighbors, min_weight, hops)
```

- [ ] **Step 10: Registrar el router en `backend/app/main.py`**

Añade el import debajo de `from app.db import create_pool`:

```python
from app.routes import router
```

Y registra el router justo después del bloque `app.add_middleware(...)`, antes del manejador de excepciones:

```python
    app.include_router(router)
```

- [ ] **Step 11: Ejecutar todos los tests y comprobar que pasan**

Run: `docker compose run --rm api pytest -q`
Expected: `96 passed`.

- [ ] **Step 12: Probar con los datos reales**

Run:

```bash
sleep 2
curl -s "localhost:8000/api/search?q=gracia" | python3 -c "
import json, sys
body = json.load(sys.stdin)
seeds = [n['ref'] for n in body['nodes'] if n['is_seed']]
print(body['total_matches'], len(body['nodes']), len(body['edges']), seeds[:3])"
```

Expected: `275 194 690 ['Éxodo 33:13', 'Levítico 7:12', 'Salmos 84:11']`. Los nodos salen en orden canónico, por eso las primeras semillas mostradas son del Antiguo Testamento.

- [ ] **Step 13: Commit**

```bash
git add backend/app backend/tests/test_refs.py backend/tests/test_search.py
git commit -m "Add lexical search with graph expansion

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Lectura de versículos y pasajes

**Files:**
- Modify: `backend/app/schemas.py`, `backend/app/search.py`, `backend/app/routes.py`
- Test: `backend/tests/test_verses.py`

**Interfaces:**
- Consumes: `app.refs.format_ref`, `app.routes.router`, `app.routes.Pool`, `app.db.query_connection`, `app.search.TRANSLATION`.
- Produces:
  - `app.schemas.Verse(id: int, ref: str, text: str)` y `PassageResponse(ref: str, verses: list[Verse])`.
  - `app.search.MAX_PASSAGE_VERSES = 200`, `app.search.PassageTooLong` (excepción).
  - `app.search.get_passage(conn: AsyncConnection, start: int, end: int) -> PassageResponse | None`. Devuelve `None` si `start` no existe. Lanza `PassageTooLong`.
  - `GET /api/verses/{verse_id}?end={id}`: 200, 404 o 422.

- [ ] **Step 1: Escribir los tests que fallan**

`backend/tests/test_verses.py`:

```python
from app import search
from tests.data import ROM_3_24, TIT_3_5, TIT_3_6, TIT_3_7


def test_single_verse(client):
    response = client.get(f"/api/verses/{ROM_3_24}")
    assert response.status_code == 200
    assert response.json() == {
        "ref": "Romanos 3:24",
        "verses": [
            {
                "id": ROM_3_24,
                "ref": "Romanos 3:24",
                "text": "Siendo justificados gratuitamente por su gracia, por la redención que es en Cristo Jesús;",
            }
        ],
    }


def test_range(client):
    response = client.get(f"/api/verses/{TIT_3_5}", params={"end": TIT_3_7})
    assert response.status_code == 200
    body = response.json()
    assert body["ref"] == "Tito 3:5-7"
    assert [v["id"] for v in body["verses"]] == [TIT_3_5, TIT_3_6, TIT_3_7]
    assert [v["ref"] for v in body["verses"]] == ["Tito 3:5", "Tito 3:6", "Tito 3:7"]


def test_end_equal_to_start_is_a_single_verse(client):
    body = client.get(f"/api/verses/{TIT_3_5}", params={"end": TIT_3_5}).json()
    assert body["ref"] == "Tito 3:5"
    assert len(body["verses"]) == 1


def test_range_whose_end_does_not_exist_stops_at_the_last_existing_verse(client):
    body = client.get(f"/api/verses/{TIT_3_5}", params={"end": TIT_3_7 + 5}).json()
    assert body["ref"] == "Tito 3:5-7"


def test_unknown_verse_is_404(client):
    assert client.get("/api/verses/1001002").status_code == 404


def test_range_starting_at_unknown_verse_is_404(client):
    assert client.get("/api/verses/56003004", params={"end": TIT_3_7}).status_code == 404


def test_end_before_start_is_422(client):
    assert client.get(f"/api/verses/{TIT_3_7}", params={"end": TIT_3_5}).status_code == 422


def test_range_longer_than_the_limit_is_422(client, monkeypatch):
    monkeypatch.setattr(search, "MAX_PASSAGE_VERSES", 2)
    assert client.get(f"/api/verses/{TIT_3_5}", params={"end": TIT_3_7}).status_code == 422


def test_non_numeric_or_out_of_range_ids_are_422(client):
    assert client.get("/api/verses/abc").status_code == 422
    assert client.get("/api/verses/0").status_code == 422
    assert client.get("/api/verses/99999999999999999999").status_code == 422
```

- [ ] **Step 2: Ejecutar y comprobar que fallan**

Run: `docker compose run --rm api pytest tests/test_verses.py -q`
Expected: `9 failed`. La mayoría por `assert 404 == ...` y uno por `AttributeError` (no existe `MAX_PASSAGE_VERSES`).

- [ ] **Step 3: Añadir los modelos al final de `backend/app/schemas.py`**

```python
class Verse(BaseModel):
    id: int
    ref: str
    text: str


class PassageResponse(BaseModel):
    ref: str
    verses: list[Verse]
```

- [ ] **Step 4: Ampliar `backend/app/search.py`**

Cambia el import de los modelos por este:

```python
from app.schemas import Edge, Node, PassageResponse, SearchResponse, Verse
```

Y añade al final del fichero:

```python
MAX_PASSAGE_VERSES = 200

PASSAGE_SQL = """
SELECT v.id, b.name_es, v.chapter, v.verse, vt.text
FROM verses v
JOIN books b ON b.id = v.book_id
JOIN verse_texts vt ON vt.verse_id = v.id AND vt.translation = %(translation)s
WHERE v.id BETWEEN %(start)s AND %(end)s
ORDER BY v.id
LIMIT %(limit)s
"""


class PassageTooLong(Exception):
    pass


async def get_passage(conn: AsyncConnection, start: int, end: int) -> PassageResponse | None:
    """Devuelve los versículos entre `start` y `end`, o None si `start` no existe."""
    cur = await conn.execute(
        PASSAGE_SQL,
        {"translation": TRANSLATION, "start": start, "end": end, "limit": MAX_PASSAGE_VERSES + 1},
    )
    rows = await cur.fetchall()
    if not rows or rows[0]["id"] != start:
        return None
    if len(rows) > MAX_PASSAGE_VERSES:
        raise PassageTooLong
    first, last = rows[0], rows[-1]
    return PassageResponse(
        ref=format_ref(
            first["name_es"], first["chapter"], first["verse"],
            last["name_es"], last["chapter"], last["verse"],
        ),
        verses=[
            Verse(id=r["id"], ref=format_ref(r["name_es"], r["chapter"], r["verse"]), text=r["text"])
            for r in rows
        ],
    )
```

- [ ] **Step 5: Ampliar `backend/app/routes.py`**

Cambia estos dos imports:

```python
from fastapi import APIRouter, Depends, HTTPException, Path, Query
```

```python
from app.schemas import PassageResponse, SearchResponse
```

Y añade al final del fichero:

```python
MAX_VERSE_ID = 66_999_999


@router.get("/verses/{verse_id}")
async def verses_endpoint(
    pool: Pool,
    verse_id: Annotated[int, Path(ge=1, le=MAX_VERSE_ID)],
    end: Annotated[int | None, Query(ge=1, le=MAX_VERSE_ID)] = None,
) -> PassageResponse:
    if end is None:
        end = verse_id
    if end < verse_id:
        raise HTTPException(422, "El final del rango no puede ser anterior al inicio")
    async with query_connection(pool) as conn:
        try:
            passage = await search.get_passage(conn, verse_id, end)
        except search.PassageTooLong:
            raise HTTPException(
                422, f"El rango no puede abarcar más de {search.MAX_PASSAGE_VERSES} versículos"
            ) from None
    if passage is None:
        raise HTTPException(404, "Versículo no encontrado")
    return passage
```

- [ ] **Step 6: Ejecutar todos los tests y comprobar que pasan**

Run: `docker compose run --rm api pytest -q`
Expected: `105 passed`.

- [ ] **Step 7: Probar con los datos reales**

Run: `sleep 2 && curl -s "localhost:8000/api/verses/56003005?end=56003007" | python3 -c "import json,sys; b=json.load(sys.stdin); print(b['ref'], len(b['verses']))"`
Expected: `Tito 3:5-7 3`

- [ ] **Step 8: Commit**

```bash
git add backend/app backend/tests/test_verses.py
git commit -m "Add verse and passage endpoint

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Esqueleto del frontend, cliente de la API y conversión a Cytoscape

**Files:**
- Create: `frontend/Dockerfile`, `frontend/.dockerignore`
- Create: `frontend/package.json`, `frontend/tsconfig.json`, `frontend/vite.config.ts`, `frontend/index.html`
- Create: `frontend/src/api.ts`, `frontend/src/graph.ts`, `frontend/src/cytoscape-fcose.d.ts`
- Create: `frontend/src/main.tsx`, `frontend/src/styles.css`, `frontend/src/App.tsx` (provisional)
- Create: `frontend/package-lock.json` (lo genera `npm install`)
- Modify: `docker-compose.yml` (servicio `frontend`)
- Test: `frontend/src/graph.test.ts`

**Interfaces:**
- Consumes: la API de las tareas 8 y 9.
- Produces, en `src/api.ts`:
  - Tipos `GraphNode`, `GraphEdge`, `SearchResponse`, `PassageVerse`, `Passage`, `SearchParams { q: string; seeds: number; neighbors: number }`.
  - `apiBase(configured: string | undefined): string`, `searchUrl(base: string, params: SearchParams): string`, `passageUrl(base: string, id: number, endId: number | null): string`.
  - `searchGraph(params: SearchParams, signal: AbortSignal): Promise<SearchResponse>`.
  - `fetchPassage(id: number, endId: number | null, signal: AbortSignal): Promise<Passage>`.
- Produces, en `src/graph.ts`:
  - `edgeWidth(weight: number): number`, `edgeId(edge): string`.
  - `toElements(response: SearchResponse): ElementDefinition[]`. Clases de nodo: `seed` o `neighbor`, y `at` o `nt`.
  - `Connection { key: string; nodeId: number; label: string; weight: number; direction: "out" | "in"; rangeEndId: number | null }`.
  - `connectionsOf(nodeId: number, response: SearchResponse): Connection[]`, de mayor a menor peso.
- Produces: servicio de compose `frontend` en el puerto 5173. Comandos: `docker compose exec frontend npm test` y `docker compose exec frontend npm run build`.

Contexto: el contenedor de desarrollo monta `frontend/` desde el host y ejecuta `npm install` al arrancar, así que `node_modules` queda en el host y el editor encuentra los tipos. `cytoscape-fcose` no trae tipos; por eso existe `cytoscape-fcose.d.ts`.

- [ ] **Step 1: Crear los ficheros de configuración**

`frontend/package.json`:

```json
{
  "name": "bible-graph-frontend",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc --noEmit && vite build",
    "preview": "vite preview",
    "test": "vitest run",
    "typecheck": "tsc --noEmit"
  },
  "dependencies": {
    "cytoscape": "^3.34.3",
    "cytoscape-fcose": "^2.2.0",
    "react": "^19.3.0",
    "react-dom": "^19.3.0"
  },
  "devDependencies": {
    "@types/react": "^19.3.0",
    "@types/react-dom": "^19.3.0",
    "@vitejs/plugin-react": "^6.1.1",
    "typescript": "^7.0.2",
    "vite": "^8.3.1",
    "vitest": "^4.1.11"
  }
}
```

`frontend/tsconfig.json`:

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2022", "DOM", "DOM.Iterable"],
    "module": "ESNext",
    "moduleResolution": "bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noEmit": true,
    "skipLibCheck": true,
    "isolatedModules": true,
    "types": ["vite/client"]
  },
  "include": ["src", "vite.config.ts"]
}
```

`frontend/vite.config.ts`:

```ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: { host: true, port: 5173 },
  // Cytoscape ocupa unos 750 kB sin comprimir; el aviso por defecto salta a los 500.
  build: { chunkSizeWarningLimit: 1000 },
  test: { environment: "node" },
});
```

`frontend/index.html`:

```html
<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>Grafo bíblico</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

- [ ] **Step 2: Crear `frontend/Dockerfile` y `frontend/.dockerignore`**

`frontend/Dockerfile`:

```dockerfile
# Etapa dev: servidor de Vite con el código montado desde el host (docker compose).
FROM node:24-alpine AS dev
WORKDIR /app
USER node
EXPOSE 5173
CMD ["sh", "-c", "npm install && npm run dev"]

# Etapa build: genera el estático. Cloudflare Pages no usa este Dockerfile.
FROM node:24-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=${VITE_API_URL}
RUN npm run build

# Etapa static: sirve el build con nginx para probarlo en local.
FROM nginx:alpine AS static
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
```

`frontend/.dockerignore`:

```text
node_modules/
dist/
```

- [ ] **Step 3: Añadir el servicio `frontend` a `docker-compose.yml`**

Insértalo después del servicio `ingest` y antes de la sección `volumes:` del final:

```yaml
  frontend:
    build:
      context: ./frontend
      target: dev
    environment:
      VITE_API_URL: http://localhost:8000
    ports:
      - "5173:5173"
    volumes:
      - ./frontend:/app
```

- [ ] **Step 4: Arrancar el contenedor e instalar dependencias**

Run:

```bash
docker compose up -d --build frontend
until docker compose exec frontend test -f node_modules/.bin/vitest; do sleep 3; done; echo instalado
```

Expected: `instalado` en menos de dos minutos, y aparece `frontend/package-lock.json`.

- [ ] **Step 5: Escribir los tests que fallan**

`frontend/src/graph.test.ts`:

```ts
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
```

- [ ] **Step 6: Ejecutar los tests y comprobar que fallan**

Run: `docker compose exec frontend npm test`
Expected: FAIL. No se puede resolver `./api` ni `./graph`.

- [ ] **Step 7: Implementar `frontend/src/api.ts`**

```ts
export interface GraphNode {
  id: number;
  ref: string;
  label: string;
  book: string;
  testament: "AT" | "NT";
  text: string;
  is_seed: boolean;
  hop: number;
}

export interface GraphEdge {
  source: number;
  target: number;
  weight: number;
  target_end_id: number | null;
  target_label: string;
}

export interface SearchResponse {
  query: string;
  total_matches: number;
  truncated: boolean;
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface PassageVerse {
  id: number;
  ref: string;
  text: string;
}

export interface Passage {
  ref: string;
  verses: PassageVerse[];
}

export interface SearchParams {
  q: string;
  seeds: number;
  neighbors: number;
}

const DEFAULT_API_URL = "http://localhost:8000";

export function apiBase(configured: string | undefined): string {
  return (configured?.trim() || DEFAULT_API_URL).replace(/\/+$/, "");
}

export function searchUrl(base: string, params: SearchParams): string {
  const query = new URLSearchParams({
    q: params.q,
    seeds: String(params.seeds),
    neighbors: String(params.neighbors),
  });
  return `${base}/api/search?${query}`;
}

export function passageUrl(base: string, id: number, endId: number | null): string {
  return endId === null ? `${base}/api/verses/${id}` : `${base}/api/verses/${id}?end=${endId}`;
}

const API_BASE = apiBase(import.meta.env?.VITE_API_URL);

async function getJson<T>(url: string, signal: AbortSignal): Promise<T> {
  const response = await fetch(url, { signal });
  if (!response.ok) {
    throw new Error(`La API respondió ${response.status}`);
  }
  return (await response.json()) as T;
}

export function searchGraph(params: SearchParams, signal: AbortSignal): Promise<SearchResponse> {
  return getJson<SearchResponse>(searchUrl(API_BASE, params), signal);
}

export function fetchPassage(
  id: number,
  endId: number | null,
  signal: AbortSignal,
): Promise<Passage> {
  return getJson<Passage>(passageUrl(API_BASE, id, endId), signal);
}
```

- [ ] **Step 8: Implementar `frontend/src/graph.ts` y la declaración de tipos**

`frontend/src/graph.ts`:

```ts
import type { ElementDefinition } from "cytoscape";
import type { GraphEdge, GraphNode, SearchResponse } from "./api";

const MIN_EDGE_WIDTH = 1;
const MAX_EDGE_WIDTH = 8;

/** Grosor de la arista: crece con el logaritmo del peso, porque los votos van de 1 a varios cientos. */
export function edgeWidth(weight: number): number {
  const width = MIN_EDGE_WIDTH + 2 * Math.log10(Math.max(weight, 1));
  return Math.min(MAX_EDGE_WIDTH, Math.round(width * 10) / 10);
}

export function edgeId(edge: Pick<GraphEdge, "source" | "target">): string {
  return `e${edge.source}-${edge.target}`;
}

function nodeClasses(node: GraphNode): string {
  return [node.is_seed ? "seed" : "neighbor", node.testament === "AT" ? "at" : "nt"].join(" ");
}

/** Convierte la respuesta de la API en elementos de Cytoscape. Los IDs de Cytoscape son cadenas. */
export function toElements(response: SearchResponse): ElementDefinition[] {
  const nodeIds = new Set(response.nodes.map((node) => node.id));
  const nodes: ElementDefinition[] = response.nodes.map((node) => ({
    group: "nodes",
    data: { id: String(node.id), label: node.label },
    classes: nodeClasses(node),
  }));
  const edges: ElementDefinition[] = response.edges
    .filter((edge) => nodeIds.has(edge.source) && nodeIds.has(edge.target))
    .map((edge) => ({
      group: "edges",
      data: {
        id: edgeId(edge),
        source: String(edge.source),
        target: String(edge.target),
        width: edgeWidth(edge.weight),
      },
    }));
  return [...nodes, ...edges];
}

export interface Connection {
  /** Identificador único de la conexión dentro del panel. */
  key: string;
  /** El nodo del otro extremo. */
  nodeId: number;
  /** Texto a mostrar: la referencia del otro extremo, con rango si la arista lo tiene. */
  label: string;
  weight: number;
  /** "out": el versículo seleccionado cita al otro. "in": el otro lo cita a él. */
  direction: "out" | "in";
  /** Último versículo del rango al que apunta la arista, o null si apunta a un solo versículo. */
  rangeEndId: number | null;
}

/** Conexiones de un nodo dentro del grafo mostrado, de mayor a menor peso. */
export function connectionsOf(nodeId: number, response: SearchResponse): Connection[] {
  const labels = new Map(response.nodes.map((node) => [node.id, node.label]));
  const connections: Connection[] = [];
  for (const edge of response.edges) {
    if (edge.source === nodeId && labels.has(edge.target)) {
      connections.push({
        key: `out-${edgeId(edge)}`,
        nodeId: edge.target,
        label: edge.target_label,
        weight: edge.weight,
        direction: "out",
        rangeEndId: edge.target_end_id,
      });
    } else if (edge.target === nodeId && labels.has(edge.source)) {
      connections.push({
        key: `in-${edgeId(edge)}`,
        nodeId: edge.source,
        label: labels.get(edge.source) ?? String(edge.source),
        weight: edge.weight,
        direction: "in",
        rangeEndId: null,
      });
    }
  }
  return connections.sort((a, b) => b.weight - a.weight || a.nodeId - b.nodeId);
}
```

`frontend/src/cytoscape-fcose.d.ts`:

```ts
declare module "cytoscape-fcose" {
  import type { Ext } from "cytoscape";
  const fcose: Ext;
  export default fcose;
}
```

- [ ] **Step 9: Ejecutar los tests y comprobar que pasan**

Run: `docker compose exec frontend npm test`
Expected: `Tests  13 passed (13)`.

- [ ] **Step 10: Crear el punto de entrada, los estilos y un `App` provisional**

`frontend/src/main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

`frontend/src/styles.css`:

```css
:root {
  --bg: #f7f5f0;
  --surface: #ffffff;
  --border: #ddd8cc;
  --text: #1f2933;
  --muted: #6b7280;
  --accent: #d97706;
  --at: #4f7cac;
  --nt: #5a9a6e;
  font-family: system-ui, -apple-system, "Segoe UI", sans-serif;
  color: var(--text);
}

* {
  box-sizing: border-box;
}

html,
body,
#root {
  height: 100%;
  margin: 0;
}

body {
  background: var(--bg);
}

.app {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.top-bar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 12px 24px;
  padding: 10px 16px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}

.top-bar h1 {
  margin: 0;
  font-size: 1.1rem;
}

.search-bar {
  display: flex;
  flex: 1 1 260px;
  gap: 8px;
}

.search-bar input {
  flex: 1;
  min-width: 0;
  padding: 8px 10px;
  font-size: 1rem;
  border: 1px solid var(--border);
  border-radius: 6px;
}

button {
  padding: 8px 14px;
  font-size: 0.95rem;
  color: #fff;
  background: var(--accent);
  border: 0;
  border-radius: 6px;
  cursor: pointer;
}

button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.limit-controls {
  display: flex;
  flex-wrap: wrap;
  gap: 6px 18px;
  font-size: 0.85rem;
}

.limit-controls label {
  display: flex;
  align-items: center;
  gap: 8px;
}

.limit-controls output {
  min-width: 2.2em;
  font-variant-numeric: tabular-nums;
}

.workspace {
  display: flex;
  flex: 1;
  min-height: 0;
}

.graph-area {
  position: relative;
  flex: 1;
  min-width: 0;
  min-height: 0;
}

.graph-view {
  position: absolute;
  inset: 0;
}

.message {
  max-width: 34rem;
  margin: 20vh auto 0;
  padding: 0 16px;
  color: var(--muted);
  text-align: center;
}

.verse-panel {
  width: 340px;
  padding: 16px;
  overflow-y: auto;
  background: var(--surface);
  border-left: 1px solid var(--border);
}

.verse-panel header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.verse-panel h2 {
  margin: 0;
  font-size: 1.15rem;
}

.verse-panel h3 {
  margin: 20px 0 8px;
  font-size: 0.9rem;
  color: var(--muted);
}

.verse-panel header button {
  padding: 2px 10px;
  font-size: 1.2rem;
  color: var(--muted);
  background: none;
}

.verse-text,
.passage p {
  line-height: 1.55;
  font-family: Georgia, "Times New Roman", serif;
}

.passage {
  padding: 2px 12px;
  background: var(--bg);
  border-radius: 6px;
}

.passage sup {
  color: var(--muted);
}

.muted {
  color: var(--muted);
  font-size: 0.9rem;
}

.connections {
  margin: 0;
  padding: 0;
  list-style: none;
}

.connections li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 3px 0;
  border-bottom: 1px solid var(--border);
}

.connections button {
  padding: 4px 0;
  color: var(--text);
  text-align: left;
  background: none;
}

.connections button:hover {
  color: var(--accent);
}

.connections button.link {
  font-size: 0.8rem;
  color: var(--accent);
  text-decoration: underline;
}

.connections .weight {
  margin-left: auto;
  color: var(--muted);
  font-size: 0.85rem;
  font-variant-numeric: tabular-nums;
}

.status-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 20px;
  padding: 8px 16px;
  font-size: 0.8rem;
  color: var(--muted);
  background: var(--surface);
  border-top: 1px solid var(--border);
}

.status-bar a {
  color: inherit;
}

.dot {
  display: inline-block;
  width: 9px;
  height: 9px;
  margin-left: 6px;
  border-radius: 50%;
}

.dot.seed {
  background: var(--accent);
}

.dot.at {
  background: var(--at);
}

.dot.nt {
  background: var(--nt);
}

@media (max-width: 760px) {
  .workspace {
    flex-direction: column;
  }

  .verse-panel {
    width: auto;
    max-height: 45%;
    border-top: 1px solid var(--border);
    border-left: 0;
  }
}
```

`frontend/src/App.tsx` (provisional; la tarea 11 lo reemplaza):

```tsx
export function App() {
  return <h1>Grafo bíblico</h1>;
}
```

- [ ] **Step 11: Comprobar tipos, build y servidor de desarrollo**

Run: `docker compose exec frontend npm run build && curl -s localhost:5173 | grep -c "Grafo bíblico"`
Expected: el build termina con `✓ built` sin errores de TypeScript, y `grep` imprime `1`.

- [ ] **Step 12: Commit**

```bash
git add docker-compose.yml frontend
git commit -m "Add frontend skeleton, API client and graph mapping

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Interfaz: búsqueda, grafo y panel del versículo

**Files:**
- Create: `frontend/src/components/SearchBar.tsx`
- Create: `frontend/src/components/LimitControls.tsx`
- Create: `frontend/src/components/GraphView.tsx`
- Create: `frontend/src/components/VersePanel.tsx`
- Modify: `frontend/src/App.tsx` (se reemplaza entero)

**Interfaces:**
- Consumes: todo lo que produce la tarea 10 (`searchGraph`, `fetchPassage`, `toElements`, `connectionsOf`, `Connection` y los tipos de `api.ts`), y las clases CSS de `styles.css`.
- Produces:
  - `SearchBar({ query: string; onSearch: (query: string) => void })`, y las constantes `MIN_QUERY_LENGTH = 2` y `MAX_QUERY_LENGTH = 100`.
  - `LimitControls({ limits: Limits; onChange: (limits: Limits) => void })`, el tipo `Limits { seeds: number; neighbors: number }` y `DEFAULT_LIMITS = { seeds: 25, neighbors: 8 }`.
  - `GraphView({ response: SearchResponse; selectedId: number | null; onSelect: (id: number | null) => void })`.
  - `VersePanel({ node, connections, passage, onSelectNode, onOpenPassage, onClose })` y el tipo `PassageState`.
  - `App`, la pantalla completa.

Esta tarea no tiene tests automáticos: la lógica con tests vive en `graph.ts` y `api.ts`. Se verifica con el compilador y a mano en el navegador.

- [ ] **Step 1: Crear `frontend/src/components/SearchBar.tsx`**

```tsx
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
```

- [ ] **Step 2: Crear `frontend/src/components/LimitControls.tsx`**

```tsx
export interface Limits {
  seeds: number;
  neighbors: number;
}

export const DEFAULT_LIMITS: Limits = { seeds: 25, neighbors: 8 };

interface Props {
  limits: Limits;
  onChange: (limits: Limits) => void;
}

export function LimitControls({ limits, onChange }: Props) {
  return (
    <div className="limit-controls">
      <label>
        Semillas
        <input
          type="range"
          min={1}
          max={100}
          value={limits.seeds}
          onChange={(event) => onChange({ ...limits, seeds: Number(event.target.value) })}
        />
        <output>{limits.seeds}</output>
      </label>
      <label>
        Vecinos
        <input
          type="range"
          min={0}
          max={20}
          value={limits.neighbors}
          onChange={(event) => onChange({ ...limits, neighbors: Number(event.target.value) })}
        />
        <output>{limits.neighbors}</output>
      </label>
    </div>
  );
}
```

- [ ] **Step 3: Crear `frontend/src/components/GraphView.tsx`**

```tsx
import cytoscape, { type Core, type LayoutOptions, type StylesheetJson } from "cytoscape";
import fcose from "cytoscape-fcose";
import { useEffect, useRef } from "react";
import type { SearchResponse } from "../api";
import { toElements } from "../graph";

cytoscape.use(fcose);

const STYLE: StylesheetJson = [
  {
    selector: "node",
    style: {
      label: "data(label)",
      "font-size": 9,
      color: "#1f2933",
      "text-valign": "bottom",
      "text-margin-y": 3,
      width: 14,
      height: 14,
    },
  },
  { selector: "node.at", style: { "background-color": "#4f7cac" } },
  { selector: "node.nt", style: { "background-color": "#5a9a6e" } },
  {
    selector: "node.seed",
    style: {
      "background-color": "#d97706",
      width: 24,
      height: 24,
      "font-size": 11,
      "font-weight": "bold",
    },
  },
  {
    selector: "edge",
    style: {
      width: "data(width)",
      "line-color": "#9aa5b1",
      "target-arrow-color": "#9aa5b1",
      "target-arrow-shape": "triangle",
      "arrow-scale": 0.7,
      "curve-style": "bezier",
      opacity: 0.55,
    },
  },
  { selector: ".faded", style: { opacity: 0.1, "text-opacity": 0 } },
  {
    selector: "node.selected",
    style: { "border-width": 3, "border-color": "#111827" },
  },
];

const LAYOUT = {
  name: "fcose",
  animate: false,
  quality: "default",
  nodeSeparation: 60,
  idealEdgeLength: 70,
  nodeRepulsion: 6000,
  padding: 30,
} as LayoutOptions;

interface Props {
  response: SearchResponse;
  selectedId: number | null;
  onSelect: (id: number | null) => void;
}

export function GraphView({ response, selectedId, onSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    const cy = cytoscape({
      container: containerRef.current,
      elements: toElements(response),
      style: STYLE,
      layout: LAYOUT,
      minZoom: 0.2,
      maxZoom: 3,
    });
    cy.on("tap", "node", (event) => onSelectRef.current(Number(event.target.id())));
    cy.on("tap", (event) => {
      if (event.target === cy) onSelectRef.current(null);
    });
    cyRef.current = cy;
    return () => {
      cyRef.current = null;
      cy.destroy();
    };
  }, [response]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().removeClass("faded selected");
    if (selectedId === null) return;
    const node = cy.getElementById(String(selectedId));
    if (node.empty()) return;
    cy.elements().not(node.closedNeighborhood()).addClass("faded");
    node.addClass("selected");
  }, [response, selectedId]);

  return <div ref={containerRef} className="graph-view" />;
}
```

El grafo se reconstruye solo cuando cambia `response`. La selección se aplica en un efecto aparte para que hacer click en un nodo no recalcule el layout.

- [ ] **Step 4: Crear `frontend/src/components/VersePanel.tsx`**

```tsx
import type { GraphNode, Passage } from "../api";
import type { Connection } from "../graph";

export type PassageState =
  | { status: "loading"; label: string }
  | { status: "error"; label: string }
  | { status: "done"; label: string; passage: Passage };

interface Props {
  node: GraphNode;
  connections: Connection[];
  passage: PassageState | null;
  onSelectNode: (id: number) => void;
  onOpenPassage: (connection: Connection) => void;
  onClose: () => void;
}

export function VersePanel({
  node,
  connections,
  passage,
  onSelectNode,
  onOpenPassage,
  onClose,
}: Props) {
  return (
    <aside className="verse-panel">
      <header>
        <h2>{node.ref}</h2>
        <button type="button" onClick={onClose} aria-label="Cerrar">
          ×
        </button>
      </header>
      <p className="verse-text">{node.text}</p>

      {passage && (
        <section className="passage">
          <h3>{passage.status === "done" ? passage.passage.ref : passage.label}</h3>
          {passage.status === "loading" && <p className="muted">Cargando pasaje…</p>}
          {passage.status === "error" && <p className="muted">No se pudo cargar el pasaje.</p>}
          {passage.status === "done" &&
            passage.passage.verses.map((verse) => (
              <p key={verse.id}>
                <sup>{verse.ref.split(":").pop()}</sup> {verse.text}
              </p>
            ))}
        </section>
      )}

      <h3>Conexiones ({connections.length})</h3>
      {connections.length === 0 && <p className="muted">Sin conexiones en este grafo.</p>}
      <ul className="connections">
        {connections.map((connection) => (
          <li key={connection.key}>
            <button
              type="button"
              onClick={() => onSelectNode(connection.nodeId)}
              title={
                connection.direction === "out"
                  ? `${node.ref} remite a ${connection.label}`
                  : `${connection.label} remite a ${node.ref}`
              }
            >
              <span aria-hidden="true">{connection.direction === "out" ? "→" : "←"}</span>{" "}
              {connection.label}
            </button>
            {connection.rangeEndId !== null && (
              <button type="button" className="link" onClick={() => onOpenPassage(connection)}>
                leer pasaje
              </button>
            )}
            <span className="weight" title="Votos en OpenBible">
              {connection.weight}
            </span>
          </li>
        ))}
      </ul>
    </aside>
  );
}
```

- [ ] **Step 5: Reemplazar `frontend/src/App.tsx`**

```tsx
import { useEffect, useMemo, useRef, useState } from "react";
import { fetchPassage, searchGraph, type SearchResponse } from "./api";
import { GraphView } from "./components/GraphView";
import { DEFAULT_LIMITS, LimitControls, type Limits } from "./components/LimitControls";
import { MIN_QUERY_LENGTH, SearchBar } from "./components/SearchBar";
import { type PassageState, VersePanel } from "./components/VersePanel";
import { type Connection, connectionsOf } from "./graph";

const LIMITS_DEBOUNCE_MS = 300;
const SLOW_AFTER_MS = 5000;

type Search =
  | { status: "idle" }
  | { status: "loading"; slow: boolean }
  | { status: "error" }
  | { status: "done"; response: SearchResponse };

function initialQuery(): string {
  return new URLSearchParams(window.location.search).get("q")?.trim() ?? "";
}

function useDebounced<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(timer);
  }, [value, delayMs]);
  return debounced;
}

export function App() {
  const [query, setQuery] = useState(initialQuery);
  const [limits, setLimits] = useState<Limits>(DEFAULT_LIMITS);
  const debouncedLimits = useDebounced(limits, LIMITS_DEBOUNCE_MS);
  const [attempt, setAttempt] = useState(0);
  const [search, setSearch] = useState<Search>({ status: "idle" });
  const [selectedId, setSelectedId] = useState<number | null>(null);
  const [passage, setPassage] = useState<PassageState | null>(null);
  const passageRequest = useRef<AbortController | null>(null);

  useEffect(() => {
    if (query.length < MIN_QUERY_LENGTH) {
      setSearch({ status: "idle" });
      return;
    }
    // Abortar la petición anterior evita que una respuesta lenta pise a una más reciente.
    const controller = new AbortController();
    setSearch({ status: "loading", slow: false });
    const slowTimer = window.setTimeout(() => {
      if (!controller.signal.aborted) setSearch({ status: "loading", slow: true });
    }, SLOW_AFTER_MS);

    searchGraph({ q: query, ...debouncedLimits }, controller.signal)
      .then((response) => {
        if (controller.signal.aborted) return;
        setSearch({ status: "done", response });
        // El nodo seleccionado puede no estar en el grafo nuevo.
        setSelectedId((current) =>
          current !== null && response.nodes.some((node) => node.id === current) ? current : null,
        );
      })
      .catch(() => {
        if (!controller.signal.aborted) setSearch({ status: "error" });
      })
      .finally(() => window.clearTimeout(slowTimer));

    return () => {
      controller.abort();
      window.clearTimeout(slowTimer);
    };
  }, [query, debouncedLimits, attempt]);

  // El pasaje abierto pertenece al nodo seleccionado: al cambiar de nodo se cierra.
  useEffect(() => {
    passageRequest.current?.abort();
    setPassage(null);
  }, [selectedId]);

  function runSearch(next: string) {
    const url = new URL(window.location.href);
    url.searchParams.set("q", next);
    window.history.replaceState(null, "", url);
    setSelectedId(null);
    setQuery(next);
    setAttempt((n) => n + 1);
  }

  function openPassage(connection: Connection) {
    passageRequest.current?.abort();
    const controller = new AbortController();
    passageRequest.current = controller;
    setPassage({ status: "loading", label: connection.label });
    fetchPassage(connection.nodeId, connection.rangeEndId, controller.signal)
      .then((result) => {
        if (!controller.signal.aborted) {
          setPassage({ status: "done", label: connection.label, passage: result });
        }
      })
      .catch(() => {
        if (!controller.signal.aborted) setPassage({ status: "error", label: connection.label });
      });
  }

  const response = search.status === "done" ? search.response : null;
  const selectedNode = useMemo(
    () => response?.nodes.find((node) => node.id === selectedId) ?? null,
    [response, selectedId],
  );
  const connections = useMemo(
    () => (response && selectedId !== null ? connectionsOf(selectedId, response) : []),
    [response, selectedId],
  );
  const seedCount = response?.nodes.filter((node) => node.is_seed).length ?? 0;

  return (
    <div className="app">
      <header className="top-bar">
        <h1>Grafo bíblico</h1>
        <SearchBar query={query} onSearch={runSearch} />
        <LimitControls limits={limits} onChange={setLimits} />
      </header>

      <main className="workspace">
        <section className="graph-area">
          {search.status === "idle" && (
            <p className="message">
              Escribe un término o concepto para ver los versículos relacionados y sus conexiones.
            </p>
          )}
          {search.status === "loading" && (
            <p className="message">
              Buscando…
              {search.slow && <span> La API puede tardar hasta un minuto en despertar.</span>}
            </p>
          )}
          {search.status === "error" && (
            <p className="message">
              No se pudo completar la búsqueda.{" "}
              <button type="button" onClick={() => setAttempt((n) => n + 1)}>
                Reintentar
              </button>
            </p>
          )}
          {response && response.nodes.length === 0 && (
            <p className="message">No hay versículos que contengan «{response.query}».</p>
          )}
          {response && response.nodes.length > 0 && (
            <GraphView response={response} selectedId={selectedId} onSelect={setSelectedId} />
          )}
        </section>

        {selectedNode && (
          <VersePanel
            node={selectedNode}
            connections={connections}
            passage={passage}
            onSelectNode={setSelectedId}
            onOpenPassage={openPassage}
            onClose={() => setSelectedId(null)}
          />
        )}
      </main>

      <footer className="status-bar">
        {response && response.nodes.length > 0 && (
          <span>
            {seedCount} de {response.total_matches} coincidencias · {response.nodes.length} nodos
            {response.truncated && " · Grafo recortado a 600 nodos"}
          </span>
        )}
        <span className="legend">
          <i className="dot seed" /> Coincidencia <i className="dot at" /> AT{" "}
          <i className="dot nt" /> NT
        </span>
        <span>
          Referencias cruzadas de{" "}
          <a
            href="https://www.openbible.info/labs/cross-references/"
            target="_blank"
            rel="noreferrer"
          >
            OpenBible.info
          </a>{" "}
          (CC-BY) · Texto: Reina-Valera 1909 (dominio público)
        </span>
      </footer>
    </div>
  );
}
```

- [ ] **Step 6: Comprobar tipos, tests y build**

Run: `docker compose exec frontend npm test && docker compose exec frontend npm run build`
Expected: `Tests  13 passed (13)` y `✓ built`, sin errores de TypeScript.

- [ ] **Step 7: Verificación manual en el navegador**

Con `docker compose up -d` en marcha y la ingesta hecha, abre <http://localhost:5173> y comprueba cada punto:

1. Sin buscar nada, el área del grafo muestra el texto de ayuda.
2. Busca `gracia`. Aparece un grafo con nodos naranjas grandes (semillas) y nodos azules y verdes (vecinos del AT y del NT). El pie dice `25 de 275 coincidencias` y el número de nodos. La URL pasa a `?q=gracia`.
3. Haz click en un nodo naranja. Se abre el panel con la referencia, el texto y la lista de conexiones, y el resto del grafo se atenúa.
4. Haz click en una conexión de la lista. La selección pasa a ese nodo.
5. Busca una conexión con el enlace `leer pasaje` y púlsalo. Aparece el pasaje completo con sus números de versículo.
6. Haz click en el fondo del grafo. El panel se cierra y el grafo recupera la opacidad.
7. **Respuestas desordenadas (Review Focus 5).** En las herramientas del navegador, pestaña Red, activa la limitación `3G lento`. Selecciona un nodo vecino (no naranja). Arrastra el slider **Vecinos** de 8 a 0 y, sin esperar, de vuelta a 12. Cuando termine de cargar, el grafo debe corresponder a 12 vecinos (muchos nodos), no a 0. Después pon **Vecinos** a 0 y espera: el nodo vecino seleccionado ya no está en el grafo y el panel debe cerrarse solo. Quita la limitación.
8. Busca `xyzzy`. Aparece `No hay versículos que contengan «xyzzy»`.
9. Para la API con `docker compose stop api` y busca `fe`. Aparece `No se pudo completar la búsqueda` con el botón `Reintentar`. Arráncala con `docker compose start api`, espera unos segundos y pulsa `Reintentar`: aparece el grafo.
10. Recarga la página con `?q=perdón` en la URL. La búsqueda se lanza sola y el campo muestra `perdón`.
11. El pie muestra `Referencias cruzadas de OpenBible.info (CC-BY) · Texto: Reina-Valera 1909 (dominio público)` y la leyenda de colores.
12. Estrecha la ventana por debajo de 760 px con un nodo seleccionado. El panel pasa debajo del grafo.

Si algún punto falla, corrígelo antes de seguir y anota qué cambiaste.

- [ ] **Step 8: Commit**

```bash
git add frontend/src
git commit -m "Add search UI, graph view and verse panel

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 12: Preparación del despliegue y documentación

**Files:**
- Create: `render.yaml`
- Create: `.env.example`
- Create: `docs/deploy.md`
- Modify: `README.md` (se reemplaza entero)

**Interfaces:**
- Consumes: `backend/Dockerfile`, `frontend/Dockerfile`, los endpoints `/health` y `/health/db`, las variables `DATABASE_URL`, `ALLOWED_ORIGINS`, `PORT`, `VITE_API_URL` e `INGEST_DATABASE_URL`.
- Produces: todo lo necesario para desplegar en Render, Neon y Cloudflare Pages. El despliegue en sí no se ejecuta.

- [ ] **Step 1: Crear `render.yaml`**

```yaml
services:
  - type: web
    name: bible-graph-api
    runtime: docker
    plan: free
    region: frankfurt
    dockerfilePath: ./backend/Dockerfile
    dockerContext: ./backend
    healthCheckPath: /health
    envVars:
      - key: DATABASE_URL
        sync: false
      - key: ALLOWED_ORIGINS
        sync: false
```

`sync: false` hace que Render pida el valor en su panel y no lo guarde en el repo.

- [ ] **Step 2: Crear `.env.example`**

```text
# Referencia de las variables de entorno del proyecto.
# En local no hace falta ningún .env: docker-compose.yml ya trae estos valores.

# --- API (Render) ---
# En producción: cadena de conexión de Neon CON pooling (el host lleva "-pooler").
DATABASE_URL=postgresql://bible:bible@db:5432/bible
# Orígenes permitidos por CORS, separados por comas. En producción: la URL de Cloudflare Pages.
ALLOWED_ORIGINS=http://localhost:5173
# PORT lo pone Render. En local la API escucha en el 8000.

# --- Ingesta ---
# Solo para cargar una BD que no sea la local. Cadena de Neon DIRECTA (sin "-pooler").
# INGEST_DATABASE_URL=postgresql://usuario:clave@ep-xxxx.eu-central-1.aws.neon.tech/neondb?sslmode=require

# --- Frontend (Cloudflare Pages, en tiempo de build) ---
VITE_API_URL=http://localhost:8000
```

- [ ] **Step 3: Crear `docs/deploy.md`**

````markdown
# Despliegue

Tres servicios gratuitos y sin tarjeta:

| Pieza | Servicio | Qué despliega |
|---|---|---|
| Base de datos | Neon | Postgres con los versículos y las referencias |
| API | Render | El contenedor de `backend/Dockerfile` |
| Frontend | Cloudflare Pages | El build estático de `frontend/` |

Hay que hacerlo en este orden, porque cada paso necesita una URL del anterior.

## 1. Base de datos en Neon

1. Crea un proyecto en <https://neon.tech>. Elige una región europea (Frankfurt) y
   Postgres 17.
2. En **Connect**, copia las dos cadenas de conexión:
   - **Directa**: con "Connection pooling" desactivado. El host no lleva `-pooler`.
   - **Con pooling**: con "Connection pooling" activado. El host lleva `-pooler`.

La directa es para la ingesta y la de pooling es para la API.

## 2. Cargar los datos

Desde la raíz del repo, en tu máquina:

```bash
INGEST_DATABASE_URL="<cadena directa de Neon>" docker compose run --rm ingest
```

La primera línea de la salida muestra el servidor de destino: comprueba que es el de
Neon. Tarda alrededor de un minuto y debe terminar así:

```
Libros:              66
Versículos:          31084
Aristas cargadas:    344542
Aristas descartadas: 257 (apuntan a versículos que no existen en RV1909)
```

La ingesta se puede repetir las veces que haga falta: reemplaza todo el contenido.

## 3. API en Render

1. En <https://dashboard.render.com>, **New → Blueprint** y selecciona este repo.
   Render lee `render.yaml` y propone el servicio `bible-graph-api`.
2. Rellena las dos variables que pide:
   - `DATABASE_URL`: la cadena **con pooling** de Neon.
   - `ALLOWED_ORIGINS`: de momento `http://localhost:5173`. Se cambia en el paso 5.
3. Cuando termine el despliegue, copia la URL del servicio
   (`https://bible-graph-api-xxxx.onrender.com`) y comprueba:

```bash
curl https://bible-graph-api-xxxx.onrender.com/health      # {"status":"ok"}
curl https://bible-graph-api-xxxx.onrender.com/health/db   # {"status":"ok"}
```

Si `/health/db` devuelve 503, la `DATABASE_URL` está mal o la BD no tiene los datos.

## 4. Frontend en Cloudflare Pages

1. En <https://dash.cloudflare.com>, **Workers & Pages → Create → Pages → Connect to
   Git** y selecciona este repo.
2. Configuración del build:
   - **Root directory**: `frontend`
   - **Build command**: `npm run build`
   - **Build output directory**: `dist`
3. Variables de entorno (de producción):
   - `VITE_API_URL`: la URL de Render del paso 3, sin barra final.
   - `NODE_VERSION`: `24`
4. Despliega y copia la URL (`https://bible-graph-xxx.pages.dev`).

`VITE_API_URL` se incrusta al construir. Si la cambias, hay que volver a desplegar.

## 5. Cerrar el círculo: CORS

1. En Render, cambia `ALLOWED_ORIGINS` a la URL de Pages, sin barra final. Si quieres
   seguir usando el frontend local contra la API de producción, pon las dos separadas
   por una coma: `https://bible-graph-xxx.pages.dev,http://localhost:5173`.
2. Render redespliega solo. Abre la URL de Pages y busca "gracia".

## Qué esperar del plan gratuito

- **Render** duerme la API tras 15 minutos sin tráfico. La primera búsqueda después
  tarda hasta un minuto; la web lo avisa.
- **Neon** suspende la BD tras unos minutos sin consultas y la despierta sola en
  menos de un segundo. `/health` no toca la BD precisamente para no impedirlo.
- Cada push a `main` redespliega la API y el frontend.

## Si algo falla

| Síntoma | Causa probable |
|---|---|
| La web dice "No se pudo completar la búsqueda" y la consola del navegador habla de CORS | `ALLOWED_ORIGINS` no coincide exactamente con la URL de Pages |
| La web busca en `localhost:8000` | Falta `VITE_API_URL` en Pages, o no se redesplegó tras ponerla |
| `/health/db` devuelve 503 | `DATABASE_URL` incorrecta en Render |
| La búsqueda no devuelve nada para ninguna palabra | La ingesta no se ejecutó contra esta BD |
| La ingesta falla con un error de `unaccent` o de permisos | Se usó la cadena con pooling; usa la directa |
````

- [ ] **Step 4: Reemplazar `README.md`**

````markdown
# bible-graph

Busca un término o concepto bíblico ("gracia", "perdón", "justicia") y explora un
grafo interactivo con los versículos que lo contienen y los que se conectan con ellos
por referencias cruzadas.

- **Texto:** Reina-Valera 1909 (dominio público), de [eBible.org](https://ebible.org).
- **Referencias cruzadas:** [OpenBible.info](https://www.openbible.info/labs/cross-references/)
  (CC-BY).
- **Stack:** FastAPI, PostgreSQL, React, Vite y Cytoscape.js.

## Arrancar en local

Solo hace falta Docker.

```bash
docker compose up -d --build        # BD, API y frontend
docker compose run --rm ingest      # carga los datos (solo la primera vez)
```

Abre <http://localhost:5173> y busca "gracia".

| Servicio | URL |
|---|---|
| Frontend | <http://localhost:5173> |
| API | <http://localhost:8000> (documentación en `/docs`) |
| Postgres | `localhost:5432`, usuario, clave y base de datos `bible` |

## Cómo se busca

- Se ignoran mayúsculas y acentos: "redencion" encuentra "redención".
- Se encuentran otras formas de la palabra: "perdón" encuentra "perdonó" y
  "perdonados".
- Varias palabras deben aparecer todas: `gracia fe`.
- Entre comillas se busca la frase exacta: `"vida eterna"`.
- `OR` busca cualquiera de las dos: `gracia OR misericordia`.
- Las palabras muy comunes ("de", "la", "fue") no se buscan.

Los versículos que contienen el término son las semillas. El grafo añade, para cada
una, sus versículos más conectados. Los deslizadores **Semillas** y **Vecinos**
controlan cuántos.

## Tests

```bash
docker compose run --rm api pytest          # backend (usa la BD aparte bible_test)
docker compose exec frontend npm test       # frontend
docker compose exec frontend npm run build  # tipos y build de producción
```

## Estructura

```
backend/app/      API: búsqueda, expansión del grafo, lectura de pasajes
backend/ingest/   Descarga y carga de los datos (python -m ingest)
backend/sql/      Esquema de la base de datos
frontend/src/     Interfaz: búsqueda, grafo y panel del versículo
docs/             Guía de despliegue, diseño y plan
```

## Despliegue

Render (API), Neon (base de datos) y Cloudflare Pages (frontend), todo en planes
gratuitos. Pasos en [docs/deploy.md](docs/deploy.md). Las variables de entorno están
descritas en [.env.example](.env.example).

## Limitación conocida

RV1909 y OpenBible numeran distinto los versículos en una docena de capítulos (por
ejemplo Números 13 o Job 39–41). En ellos, una referencia cruzada puede apuntar al
versículo contiguo al correcto.
````

- [ ] **Step 5: Comprobar la imagen de producción de la API**

Construye la imagen como lo hará Render (sin dependencias de desarrollo) y arráncala con un `PORT` distinto:

```bash
docker build -q -t bible-graph-api-prod backend
docker run -d --rm --name bible-graph-api-prod --network bible-graph_default \
  -e PORT=10000 -e DATABASE_URL=postgresql://bible:bible@db:5432/bible \
  -e ALLOWED_ORIGINS=https://ejemplo.pages.dev -p 10000:10000 bible-graph-api-prod
sleep 3
curl -s localhost:10000/health; curl -s localhost:10000/health/db; echo
docker exec bible-graph-api-prod sh -c 'whoami; pip list 2>/dev/null | grep -ci pytest'
docker stop bible-graph-api-prod
```

Expected:

```
{"status":"ok"}{"status":"ok"}
appuser
0
```

Si la red no se llama `bible-graph_default`, mira el nombre con `docker network ls`.

- [ ] **Step 6: Comprobar el build estático del frontend**

Run: `docker build -q --target static -t bible-graph-frontend-static frontend && echo construido`
Expected: `construido`. Es el mismo `npm run build` que ejecutará Cloudflare Pages.

- [ ] **Step 7: Verificación final de todo el proyecto**

Run:

```bash
docker compose run --rm api pytest -q
docker compose exec frontend npm test
docker compose exec frontend npm run build
docker compose config -q && echo compose-ok
```

Expected: `105 passed`, `Tests  13 passed (13)`, `✓ built` y `compose-ok`.

- [ ] **Step 8: Commit**

```bash
git add render.yaml .env.example docs/deploy.md README.md
git commit -m "Add deployment config and documentation

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

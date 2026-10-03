# Rediseño de la interfaz y frases de relación: plan de implementación

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Objetivo:** dar a la app el aspecto de la maqueta (tema oscuro, término en el centro, anillos luminosos, barra lateral y panel de detalle), colorear los nodos por tipo de libro y explicar cada relación con una frase generada por Ollama y guardada en la base de datos.

**Arquitectura:** una tabla nueva `relation_explanations` guarda una frase por par de versículos. Un endpoint `GET /api/explanations` devuelve las guardadas y, si hay `OLLAMA_URL`, genera las que faltan en una sola llamada a Ollama sin ocupar una conexión del pool. Un comando `python -m ingest.explain` las pregenera en lote. El frontend se rehace con componentes nuevos (barra superior, barra lateral, grafo con capa de etiquetas HTML, panel) y calcula los grupos de libros a partir del ID del versículo.

**Stack:** lo del MVP (FastAPI, psycopg 3, Postgres 17, React 19, Vite, Cytoscape.js con fcose), más Ollama con `gemma4:e4b`, `lucide-react` y `@fontsource-variable/inter`.

**Spec:** `docs/superpowers/specs/2026-09-30-ui-redesign-design.md`. Léela antes de empezar. El MVP del que parte está en `docs/superpowers/specs/2026-09-30-bible-graph-mvp-design.md`.

**Procedencia del código:** todo el código de este plan se ha ejecutado ya en un entorno desechable en esta misma máquina (Windows 11, Docker Desktop, Ollama 0.34.4 con `gemma4:e4b`): 162 tests de backend, 41 de frontend, build de producción, generación real de frases y 23 comprobaciones en navegador. Cópialo tal cual. Si un resultado no coincide con el `Expected`, para e investiga antes de cambiar el código.

## Global Constraints

- Se trabaja en la rama `ui-redesign`, que parte de `mvp`. No se hace commit en `main` ni en `mvp`.
- Los comandos se ejecutan en Git Bash desde la raíz del repo, salvo que se indique PowerShell. En esta máquina los puertos 5432, 8000 y 5173 están ocupados por otros proyectos: el paso 7 de la tarea 1 crea un `.env` local (no se sube) con `DB_PORT=5442`, `API_PORT=8010` y `FRONTEND_PORT=5180`, y todas las URLs del plan usan esos puertos.
- Las URLs del navegador y de las pruebas usan `localhost`, no `127.0.0.1`: CORS solo admite `http://localhost:5180`. Para `curl` a la API da igual.
- Ollama corre en el host (`http://localhost:11434`) con el modelo `gemma4:e4b` ya descargado. No se descargan modelos nuevos.
- Modelo por defecto: `gemma4:e4b`. Frases válidas: de 20 a 160 caracteres. Máximo 30 relaciones por petición. Espera máxima a Ollama: 60 s.
- Grupos de libros: Ley 1–5, Históricos 6–17, Poéticos 18–22, Profetas 23–39, Evangelios y Hechos 40–44, Cartas y Apocalipsis 45–66.
- Valores por defecto de los sliders: 5 semillas y 10 vecinos.
- Interfaz, mensajes y comentarios en español. Nombre visible de la app: "Biblia en red".
- Ficheros con finales de línea LF (lo garantiza `.gitattributes` desde la tarea 1).
- La atribución "Referencias cruzadas de OpenBible.info (CC-BY)" debe seguir visible.
- Cada commit termina con la línea `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Fuera de alcance: nombres de concepto por nodo, categorías Persona/Lugar/Tema, generar frases desde Render, desplegar.

## Review Focus

1. **Ollama lento, frío o apagado.** El endpoint debe responder 200 con `null` y el panel mostrar el comienzo del versículo, nunca un error. Tests en la tarea 3 (`test_generator_failure_answers_200_with_nulls`, `test_without_ollama_only_stored_phrases_are_returned`) y comprobación real en el paso 11 de la tarea 3.
2. **Una generación lenta no debe bloquear el resto de la API.** La llamada a Ollama se hace sin conexión del pool. Comprobación en el paso 12 de la tarea 3: una búsqueda responde mientras se generan frases en frío.
3. **La ingesta no puede borrar las frases.** Test `test_load_keeps_relation_explanations` en la tarea 3.
4. **Respuestas raras del modelo** (JSON roto, número de frases distinto, frases vacías, largas o que empiezan por "Ambos"). Tests de `parse_phrases` y `clean_phrase` en la tarea 2 y `test_invalid_phrases_are_returned_as_null_and_not_stored` en la tarea 3.
5. **Windows:** finales de línea CRLF dentro de los contenedores, puertos ocupados y cambios de ficheros que no llegan a los contenedores (sin recarga en caliente). Comprobaciones en la tarea 1 (pasos 3, 5 y 9) y en la tarea 6 (paso 11).

## Estructura de ficheros

```
.gitattributes                          tarea 1   LF en todo el repo
docker-compose.yml                      tarea 1   puertos, Ollama, sondeo de ficheros
.env.example                            tarea 1   variables nuevas
.env                                    tarea 1   solo local, no se sube
backend/
  sql/schema.sql                        tarea 3   tabla relation_explanations
  app/ollama.py                         tarea 2   prompt, parseo, limpieza, cliente HTTP
  app/explanations.py                   tarea 3   leer, generar y guardar frases
  app/config.py, schemas.py, main.py, routes.py   tarea 3
  ingest/explain.py                     tarea 4   pregeneración en lote
  tests/test_ollama.py                  tarea 2
  tests/fakes.py, test_explanations.py  tarea 3
  tests/test_load.py                    tarea 3   (se reemplaza)
  tests/test_explain_cli.py             tarea 4
frontend/
  package.json, package-lock.json       tarea 5   lucide-react, Inter
  src/groups.ts, text.ts, theme.ts      tarea 5
  src/graph.ts, api.ts                  tarea 5   (se reemplazan)
  src/graph.test.ts, support.test.ts    tarea 5
  index.html, public/favicon.svg        tarea 6
  src/main.tsx, styles.css, App.tsx     tarea 6   (se reemplazan)
  src/components/TopBar, SearchBar, Sidebar, Legend, GraphView, VersePanel   tarea 6
  src/components/LimitControls.tsx      tarea 6   (se borra)
README.md, docs/deploy.md               tarea 7
```

---

### Task 1: Entorno: finales de línea, puertos configurables y Ollama en compose

**Files:**
- Create: `.gitattributes`
- Modify: `docker-compose.yml` (se reemplaza entero), `.env.example` (se reemplaza entero)
- Create (local, no se sube): `.env`

**Interfaces:**
- Consumes: el `docker-compose.yml` del MVP.
- Produces:
  - Variables de compose `DB_PORT`, `API_PORT`, `FRONTEND_PORT`, `OLLAMA_URL`, `OLLAMA_MODEL`.
  - Variables de entorno de la API y de la ingesta: `OLLAMA_URL` (por defecto `http://host.docker.internal:11434`) y `OLLAMA_MODEL` (por defecto `gemma4:e4b`).
  - Recarga por sondeo: `WATCHFILES_FORCE_POLLING` en la API y `CHOKIDAR_USEPOLLING` en el frontend.

Contexto: en esta máquina `git config core.autocrlf` es `true`, así que los ficheros se han sacado con CRLF. Los contenedores son Linux y los montan tal cual. `.gitattributes` fija LF para todo el repo y el paso 2 vuelve a sacar los ficheros.

- [ ] **Step 1: Comprobar que el árbol está limpio**

Run: `git status --short && git branch --show-current`
Expected: ninguna línea de cambios y `ui-redesign`.

- [ ] **Step 2: Crear `.gitattributes` y volver a sacar los ficheros con LF**

`.gitattributes`:

```gitattributes
# Finales de línea LF en el repositorio y en la copia de trabajo, también en Windows:
# el código se monta en contenedores Linux.
* text=auto eol=lf
*.png binary
*.jpg binary
*.zip binary
```

Run:

```bash
git add .gitattributes
git commit -qm "Force LF line endings

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
git rm -rq --cached . && git reset -q --hard HEAD
git ls-files --eol | grep -c "w/crlf"
```

Expected: `0`. `git reset --hard` es seguro aquí porque el paso 1 confirmó que no había cambios sin guardar.

- [ ] **Step 3: Escribir la comprobación de compose y ver que falla**

Run:

```bash
DB_PORT=5442 API_PORT=8010 FRONTEND_PORT=5180 docker compose config --format json | python -c "
import json, sys
c = json.load(sys.stdin)['services']
ports = {n: [(p.get('host_ip'), p['published']) for p in s.get('ports', [])] for n, s in c.items()}
env = c['api']['environment']
ok = (ports == {'db': [('127.0.0.1', '5442')], 'api': [('127.0.0.1', '8010')], 'frontend': [('127.0.0.1', '5180')]}
      and env.get('OLLAMA_URL') == 'http://host.docker.internal:11434'
      and env.get('ALLOWED_ORIGINS') == 'http://localhost:5180'
      and env.get('WATCHFILES_FORCE_POLLING') == 'true'
      and c['frontend']['environment'].get('VITE_API_URL') == 'http://localhost:8010'
      and c['frontend']['environment'].get('CHOKIDAR_USEPOLLING') == 'true')
print('OK' if ok else 'FAIL', ports)"
```

Expected: `FAIL` con los puertos fijos del MVP (`5432`, `8000`, `5173`).

- [ ] **Step 4: Reemplazar `docker-compose.yml`**

```yaml
# Puertos del host configurables con DB_PORT, API_PORT y FRONTEND_PORT (por ejemplo en
# un fichero .env junto a este), por si 5432, 8000 o 5173 ya están ocupados.

x-backend: &backend
  build:
    context: ./backend
    args:
      REQUIREMENTS: requirements-dev.txt
  image: bible-graph-backend
  depends_on:
    db:
      condition: service_healthy
  # Permite llegar al Ollama del host como host.docker.internal también en Linux.
  extra_hosts:
    - "host.docker.internal:host-gateway"

services:
  db:
    image: pgvector/pgvector:pg17
    environment:
      POSTGRES_USER: bible
      POSTGRES_PASSWORD: bible
      POSTGRES_DB: bible
    ports:
      - "127.0.0.1:${DB_PORT:-5432}:5432"
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
      ALLOWED_ORIGINS: http://localhost:${FRONTEND_PORT:-5173}
      OLLAMA_URL: ${OLLAMA_URL:-http://host.docker.internal:11434}
      OLLAMA_MODEL: ${OLLAMA_MODEL:-gemma4:e4b}
      # Recarga al guardar también en Windows, donde el contenedor no recibe eventos de ficheros.
      WATCHFILES_FORCE_POLLING: "true"
    ports:
      - "127.0.0.1:${API_PORT:-8000}:8000"
    volumes:
      - ./backend:/app

  # Se lanza a demanda: docker compose run --rm ingest
  # Para cargar otra BD (Neon): INGEST_DATABASE_URL="postgresql://..." docker compose run --rm ingest
  # Frases en lote: docker compose run --rm ingest python -m ingest.explain --limit 5000
  ingest:
    <<: *backend
    profiles: ["tools"]
    command: python -m ingest
    environment:
      DATABASE_URL: ${INGEST_DATABASE_URL:-postgresql://bible:bible@db:5432/bible}
      OLLAMA_URL: ${OLLAMA_URL:-http://host.docker.internal:11434}
      OLLAMA_MODEL: ${OLLAMA_MODEL:-gemma4:e4b}
    volumes:
      - ./backend:/app
      - ingest-cache:/cache

  frontend:
    build:
      context: ./frontend
      target: dev
    environment:
      VITE_API_URL: http://localhost:${API_PORT:-8000}
      CHOKIDAR_USEPOLLING: "true"
    ports:
      - "127.0.0.1:${FRONTEND_PORT:-5173}:5173"
    volumes:
      - ./frontend:/app

volumes:
  db-data:
  ingest-cache:
```

- [ ] **Step 5: Repetir la comprobación**

Run: el mismo comando del paso 3.
Expected: `OK {'db': [('127.0.0.1', '5442')], 'api': [('127.0.0.1', '8010')], 'frontend': [('127.0.0.1', '5180')]}`

- [ ] **Step 6: Reemplazar `.env.example`**

```bash
# Referencia de las variables de entorno del proyecto.
# En local no hace falta ningún .env: docker-compose.yml ya trae estos valores.
# Si quieres cambiar alguno en local, copia las líneas que necesites a un fichero .env
# junto a docker-compose.yml.

# --- Puertos del host (solo docker compose) ---
# Cámbialos si 5432, 8000 o 5173 ya están ocupados en tu máquina.
# DB_PORT=5432
# API_PORT=8000
# FRONTEND_PORT=5173

# --- API (Render) ---
# En producción: cadena de conexión de Neon CON pooling (el host lleva "-pooler").
DATABASE_URL=postgresql://bible:bible@db:5432/bible
# Orígenes permitidos por CORS, separados por comas. En producción: la URL de Cloudflare Pages.
ALLOWED_ORIGINS=http://localhost:5173
# PORT lo pone Render. En local la API escucha en el 8000.

# --- Frases de relación (Ollama) ---
# Con OLLAMA_URL la API genera las frases que faltan. Sin ella (en Render) solo lee las
# ya guardadas. En compose apunta por defecto al Ollama del host.
# OLLAMA_URL=http://host.docker.internal:11434
# OLLAMA_MODEL=gemma4:e4b

# --- Ingesta ---
# Solo para cargar una BD que no sea la local. Cadena de Neon DIRECTA (sin "-pooler").
# INGEST_DATABASE_URL=postgresql://usuario:clave@ep-xxxx.eu-central-1.aws.neon.tech/neondb?sslmode=require

# --- Frontend (Cloudflare Pages, en tiempo de build) ---
VITE_API_URL=http://localhost:8000
```

- [ ] **Step 7: Crear el `.env` local de esta máquina**

```bash
printf 'DB_PORT=5442\nAPI_PORT=8010\nFRONTEND_PORT=5180\n' > .env
git check-ignore .env
```

Expected: `.env` (está ignorado por `.gitignore` y no se sube).

- [ ] **Step 8: Levantar el entorno, cargar los datos y pasar los tests del MVP**

Run:

```bash
docker compose up -d --build db api
docker compose run --rm ingest 2>&1 | grep -E "Destino|Versículos|cargadas"
docker compose run --rm api pytest -q | tail -1
```

Expected: `Destino: db/bible`, `Versículos: 31084`, `Aristas cargadas: 344542` y `112 passed`.

- [ ] **Step 9: Comprobar que la API recarga al guardar y que llega a Ollama**

Run:

```bash
echo "# sondeo" >> backend/app/refs.py; sleep 4
docker compose logs --since 8s api | grep -c "Reloading"
git checkout backend/app/refs.py
docker compose exec -T api python -c "import urllib.request; print(urllib.request.urlopen('http://host.docker.internal:11434/api/version').read().decode())"
```

Expected: un número mayor que 0 y `{"version":"0.34.4"}`.

- [ ] **Step 10: Commit**

```bash
git add docker-compose.yml .env.example
git commit -m "Make compose ports configurable and reach host Ollama

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Cliente de Ollama

**Files:**
- Create: `backend/app/ollama.py`
- Test: `backend/tests/test_ollama.py`

**Interfaces:**
- Consumes: nada del proyecto.
- Produces, en `app.ollama`:
  - `DEFAULT_MODEL = "gemma4:e4b"`, `MIN_PHRASE_LENGTH = 20`, `MAX_PHRASE_LENGTH = 160`.
  - `VersePair(a_ref: str, a_text: str, b_ref: str, b_text: str)`, dataclass inmutable.
  - `Generator` (Protocol): atributo `model: str` y método `generate(pairs: list[VersePair]) -> list[str]`, que devuelve una frase por par o lanza una excepción.
  - `OllamaError(Exception)`.
  - `build_prompt(pairs) -> str`, `parse_phrases(raw: str, expected: int) -> list[str]` (lanza `OllamaError`) y `clean_phrase(text: str) -> str | None`.
  - `OllamaGenerator(url: str, model: str = DEFAULT_MODEL, timeout: float = 60)`, que implementa `Generator`.

Contexto: el cliente usa `urllib` de la biblioteca estándar para no añadir dependencias. `clean_phrase` quita comillas, espacios de más y el arranque "Ambos textos…" que el modelo usa a menudo, y rechaza longitudes fuera de 20–160.

- [ ] **Step 1: Escribir los tests que fallan**

`backend/tests/test_ollama.py`:

```python
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

from app.ollama import (
    OllamaError,
    OllamaGenerator,
    VersePair,
    build_prompt,
    clean_phrase,
    parse_phrases,
)

PAIR = VersePair("Romanos 3:24", "Siendo justificados…", "Efesios 2:8", "Porque por gracia…")
OTHER = VersePair("Génesis 1:1", "EN el principio…", "Juan 1:1", "EN el principio era el Verbo…")


def test_build_prompt_numbers_every_pair_with_refs_and_texts():
    prompt = build_prompt([PAIR, OTHER])
    assert 'Par 1:\nA, Romanos 3:24: "Siendo justificados…"\nB, Efesios 2:8: "Porque por gracia…"' in prompt
    assert 'Par 2:\nA, Génesis 1:1: "EN el principio…"' in prompt
    assert '{"frases": [' in prompt


def test_parse_phrases_reads_the_json_list():
    raw = json.dumps({"frases": ["uno", "dos"]})
    assert parse_phrases(raw, 2) == ["uno", "dos"]


def test_parse_phrases_replaces_non_strings_with_empty_text():
    assert parse_phrases('{"frases": ["uno", 3]}', 2) == ["uno", ""]


@pytest.mark.parametrize(
    "raw",
    ["no es json", "[]", '{"otra": []}', '{"frases": "uno"}', '{"frases": ["uno"]}'],
)
def test_parse_phrases_rejects_unexpected_answers(raw):
    with pytest.raises(OllamaError):
        parse_phrases(raw, 2)


def test_clean_phrase_strips_quotes_and_extra_spaces():
    assert clean_phrase('  «La gracia   de Dios salva sin obras.»  ') == (
        "La gracia de Dios salva sin obras."
    )


@pytest.mark.parametrize(
    ("raw", "clean"),
    [
        ("Ambos textos hablan de la protección divina.", "Hablan de la protección divina."),
        ("ambos versículos celebran el perdón de los pecados.", "Celebran el perdón de los pecados."),
        ("Ambos prometen librar la ciudad del enemigo.", "Prometen librar la ciudad del enemigo."),
        ("Ambos pasajes definen el amor de Dios.", "Definen el amor de Dios."),
        ("Ambosidad no es una palabra pero no se toca.", "Ambosidad no es una palabra pero no se toca."),
    ],
)
def test_clean_phrase_drops_a_leading_ambos(raw, clean):
    assert clean_phrase(raw) == clean


def test_clean_phrase_capitalizes_the_first_letter():
    assert clean_phrase("la salvación es un regalo de Dios.") == "La salvación es un regalo de Dios."


@pytest.mark.parametrize("text", ["", "Muy corta.", "x" * 161, '""'])
def test_clean_phrase_rejects_unreasonable_lengths(text):
    assert clean_phrase(text) is None


class FakeOllama(BaseHTTPRequestHandler):
    received: list[dict] = []
    reply: dict = {}

    def do_POST(self):  # noqa: N802
        length = int(self.headers["Content-Length"])
        FakeOllama.received.append(json.loads(self.rfile.read(length)))
        body = json.dumps(FakeOllama.reply).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *args):
        pass


@pytest.fixture
def fake_ollama():
    FakeOllama.received = []
    server = HTTPServer(("127.0.0.1", 0), FakeOllama)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}/"
    server.shutdown()


def test_generator_sends_one_request_and_returns_the_phrases(fake_ollama):
    FakeOllama.reply = {"response": json.dumps({"frases": ["primera frase", "segunda frase"]})}
    generator = OllamaGenerator(fake_ollama, model="gemma4:e4b")
    assert generator.generate([PAIR, OTHER]) == ["primera frase", "segunda frase"]
    [request] = FakeOllama.received
    assert request["model"] == "gemma4:e4b"
    assert request["format"] == "json"
    assert request["stream"] is False
    assert "Romanos 3:24" in request["prompt"] and "Juan 1:1" in request["prompt"]


def test_generator_raises_when_the_answer_does_not_fit(fake_ollama):
    FakeOllama.reply = {"response": json.dumps({"frases": ["solo una"]})}
    with pytest.raises(OllamaError):
        OllamaGenerator(fake_ollama).generate([PAIR, OTHER])


def test_generator_raises_when_ollama_is_unreachable():
    with pytest.raises(OllamaError):
        OllamaGenerator("http://127.0.0.1:1", timeout=2).generate([PAIR])
```

- [ ] **Step 2: Ejecutar y comprobar que fallan**

Run: `docker compose run --rm api pytest tests/test_ollama.py -q 2>&1 | tail -3`
Expected: `ModuleNotFoundError: No module named 'app.ollama'`.

- [ ] **Step 3: Implementar `backend/app/ollama.py`**

```python
"""Cliente mínimo de Ollama para redactar frases que explican relaciones entre versículos."""

import json
import re
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol

DEFAULT_MODEL = "gemma4:e4b"
TIMEOUT_SECONDS = 60
MIN_PHRASE_LENGTH = 20
MAX_PHRASE_LENGTH = 160
QUOTES = "\"'«»“”‘’"
# "Ambos textos hablan de…" no aporta nada: se deja en "Hablan de…".
BOTH_PREFIX = re.compile(r"^ambos(?:\s+(?:textos|versículos|versiculos|pasajes))?\s+", re.IGNORECASE)

PROMPT = """Varios pares de versículos de la Biblia (Reina-Valera 1909) están unidos por referencias cruzadas.

{items}

Para cada par, escribe en español actual UNA frase de 6 a 12 palabras que explique qué relación hay entre los dos versículos. Di directamente la idea que los une, sin empezar por «Ambos». No repitas las referencias. No uses comillas.
Responde solo con un objeto JSON con la forma {{"frases": ["frase del par 1", "frase del par 2", ...]}}, con una frase por par y en el mismo orden."""


@dataclass(frozen=True)
class VersePair:
    a_ref: str
    a_text: str
    b_ref: str
    b_text: str


class Generator(Protocol):
    """Redacta una frase por par. Devuelve una lista del mismo tamaño o lanza una excepción."""

    model: str

    def generate(self, pairs: list[VersePair]) -> list[str]: ...


class OllamaError(Exception):
    pass


def build_prompt(pairs: list[VersePair]) -> str:
    items = "\n\n".join(
        f'Par {n}:\nA, {p.a_ref}: "{p.a_text}"\nB, {p.b_ref}: "{p.b_text}"'
        for n, p in enumerate(pairs, start=1)
    )
    return PROMPT.format(items=items)


def parse_phrases(raw: str, expected: int) -> list[str]:
    """Extrae la lista de frases de la respuesta del modelo. Lanza OllamaError si no cuadra."""
    try:
        phrases = json.loads(raw)["frases"]
    except (ValueError, TypeError, KeyError) as error:
        raise OllamaError(f"respuesta ilegible: {raw[:200]!r}") from error
    if not isinstance(phrases, list) or len(phrases) != expected:
        raise OllamaError(f"se esperaban {expected} frases y llegaron {phrases!r}"[:300])
    return [p if isinstance(p, str) else "" for p in phrases]


def clean_phrase(text: str) -> str | None:
    """Quita comillas y espacios de los extremos. Devuelve None si la longitud no es razonable."""
    text = " ".join(text.split()).strip(QUOTES + " ")
    text = BOTH_PREFIX.sub("", text)
    text = text[:1].upper() + text[1:]
    if not MIN_PHRASE_LENGTH <= len(text) <= MAX_PHRASE_LENGTH:
        return None
    return text


class OllamaGenerator:
    def __init__(self, url: str, model: str = DEFAULT_MODEL, timeout: float = TIMEOUT_SECONDS):
        self.url = url.rstrip("/")
        self.model = model
        self.timeout = timeout

    def generate(self, pairs: list[VersePair]) -> list[str]:
        body = json.dumps(
            {
                "model": self.model,
                "prompt": build_prompt(pairs),
                "stream": False,
                "think": False,
                "format": "json",
                "options": {"temperature": 0.2},
            }
        ).encode("utf-8")
        request = urllib.request.Request(
            f"{self.url}/api/generate", body, {"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                data = json.load(response)
        except (OSError, ValueError) as error:
            raise OllamaError(f"no se pudo consultar Ollama en {self.url}: {error}") from error
        return parse_phrases(data.get("response", ""), len(pairs))
```

- [ ] **Step 4: Ejecutar todos los tests y comprobar que pasan**

Run: `docker compose run --rm api pytest -q | tail -1`
Expected: `134 passed`.

- [ ] **Step 5: Commit**

```bash
git add backend/app/ollama.py backend/tests/test_ollama.py
git commit -m "Add Ollama client for relation phrases

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Tabla y endpoint de frases de relación

**Files:**
- Modify: `backend/sql/schema.sql`, `backend/app/config.py`, `backend/app/schemas.py`, `backend/app/main.py`, `backend/app/routes.py` (todos se reemplazan enteros)
- Create: `backend/app/explanations.py`
- Create: `backend/tests/fakes.py`
- Test: `backend/tests/test_explanations.py`, `backend/tests/test_load.py` (se reemplaza entero)

**Interfaces:**
- Consumes: `app.ollama` (tarea 2), `app.db.query_connection`, `app.refs.format_ref`, `app.search.TRANSLATION`, `tests.data`.
- Produces:
  - Tabla `relation_explanations(verse_a, verse_b, text, model, created_at)`, con `verse_a < verse_b`.
  - `Settings.ollama_url: str = ""` y `Settings.ollama_model: str = "gemma4:e4b"`, leídos de `OLLAMA_URL` y `OLLAMA_MODEL`.
  - `create_app(settings=None, generator=None)`. Sin `generator`, usa `OllamaGenerator` si hay `ollama_url` y `None` si no. Queda en `app.state.generator`.
  - `app.schemas.Explanation(other: int, text: str | None)` y `ExplanationsResponse(verse: int, explanations: list[Explanation])`.
  - `app.explanations`: `MAX_OTHERS = 30`, `pair_key(x, y)`, `verse_pair(key, texts) -> VersePair`, `explain(pool, generator, verse, others) -> ExplanationsResponse`, y las consultas `TEXTS_SQL` e `INSERT_SQL` (las reutiliza la tarea 4).
  - `GET /api/explanations?verse={id}&others={id},{id},…`.
  - `tests.fakes.FakeGenerator(phrase=..., error=None)`, con `model = "modelo-falso"` y la lista `calls`.

- [ ] **Step 1: Crear el generador falso de los tests**

`backend/tests/fakes.py`:

```python
"""Generador de frases falso para los tests: registra las llamadas y no usa ningún modelo."""

from collections.abc import Callable

from app.ollama import VersePair


def default_phrase(pair: VersePair) -> str:
    return f"Frase de prueba que une {pair.a_ref} con {pair.b_ref}."


class FakeGenerator:
    model = "modelo-falso"

    def __init__(
        self,
        phrase: Callable[[VersePair], str] = default_phrase,
        error: Exception | None = None,
    ):
        self.phrase = phrase
        self.error = error
        self.calls: list[list[VersePair]] = []

    def generate(self, pairs: list[VersePair]) -> list[str]:
        self.calls.append(pairs)
        if self.error is not None:
            raise self.error
        return [self.phrase(pair) for pair in pairs]
```

- [ ] **Step 2: Escribir los tests del endpoint**

`backend/tests/test_explanations.py`:

```python
import psycopg
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from tests.data import EPH_2_8, GEN_1_1, PS_32_1, ROM_3_24, TIT_3_5
from tests.fakes import FakeGenerator


@pytest.fixture(autouse=True)
def no_explanations(database_url):
    with psycopg.connect(database_url) as conn:
        conn.execute("TRUNCATE relation_explanations")


def make_client(database_url, generator):
    settings = Settings(database_url=database_url, allowed_origins=[])
    return TestClient(create_app(settings, generator=generator))


def stored(database_url):
    with psycopg.connect(database_url) as conn:
        return conn.execute(
            "SELECT verse_a, verse_b, text, model FROM relation_explanations ORDER BY 1, 2"
        ).fetchall()


def explain(client, verse, *others):
    response = client.get(
        "/api/explanations", params={"verse": verse, "others": ",".join(map(str, others))}
    )
    assert response.status_code == 200, response.text
    return {e["other"]: e["text"] for e in response.json()["explanations"]}


def test_missing_phrases_are_generated_in_one_call_and_stored(database_url):
    generator = FakeGenerator()
    with make_client(database_url, generator) as client:
        texts = explain(client, ROM_3_24, EPH_2_8, TIT_3_5)
    assert texts == {
        EPH_2_8: "Frase de prueba que une Romanos 3:24 con Efesios 2:8.",
        TIT_3_5: "Frase de prueba que une Romanos 3:24 con Tito 3:5.",
    }
    assert len(generator.calls) == 1
    assert len(generator.calls[0]) == 2
    assert [row[:2] for row in stored(database_url)] == [(ROM_3_24, EPH_2_8), (ROM_3_24, TIT_3_5)]
    assert {row[3] for row in stored(database_url)} == {"modelo-falso"}


def test_stored_phrases_are_not_generated_again(database_url):
    generator = FakeGenerator()
    with make_client(database_url, generator) as client:
        first = explain(client, ROM_3_24, EPH_2_8)
        second = explain(client, ROM_3_24, EPH_2_8)
    assert first == second
    assert len(generator.calls) == 1


def test_a_phrase_serves_both_directions(database_url):
    generator = FakeGenerator()
    with make_client(database_url, generator) as client:
        explain(client, ROM_3_24, EPH_2_8)
        texts = explain(client, EPH_2_8, ROM_3_24)
    assert texts[ROM_3_24] == "Frase de prueba que une Romanos 3:24 con Efesios 2:8."
    assert len(generator.calls) == 1


def test_verses_without_a_cross_reference_get_no_phrase(database_url):
    generator = FakeGenerator()
    with make_client(database_url, generator) as client:
        texts = explain(client, ROM_3_24, GEN_1_1, ROM_3_24)
    assert texts == {GEN_1_1: None, ROM_3_24: None}
    assert generator.calls == []


def test_answer_keeps_the_order_of_others(database_url):
    with make_client(database_url, FakeGenerator()) as client:
        response = client.get(
            "/api/explanations",
            params={"verse": ROM_3_24, "others": f"{TIT_3_5},{GEN_1_1},{EPH_2_8}"},
        )
    assert [e["other"] for e in response.json()["explanations"]] == [TIT_3_5, GEN_1_1, EPH_2_8]


def test_invalid_phrases_are_returned_as_null_and_not_stored(database_url):
    def phrase(pair):
        return "corta" if pair.b_ref == "Salmos 32:1" or pair.a_ref == "Salmos 32:1" else (
            "Una frase suficientemente larga para ser válida."
        )

    with make_client(database_url, FakeGenerator(phrase)) as client:
        texts = explain(client, ROM_3_24, PS_32_1, EPH_2_8)
    assert texts == {PS_32_1: None, EPH_2_8: "Una frase suficientemente larga para ser válida."}
    assert [row[:2] for row in stored(database_url)] == [(ROM_3_24, EPH_2_8)]


def test_generator_failure_answers_200_with_nulls(database_url):
    generator = FakeGenerator(error=RuntimeError("Ollama no responde"))
    with make_client(database_url, generator) as client:
        texts = explain(client, ROM_3_24, EPH_2_8)
    assert texts == {EPH_2_8: None}
    assert stored(database_url) == []


def test_without_ollama_only_stored_phrases_are_returned(database_url):
    with make_client(database_url, FakeGenerator()) as client:
        explain(client, ROM_3_24, EPH_2_8)
    with make_client(database_url, None) as client:
        assert client.app.state.generator is None
        texts = explain(client, ROM_3_24, EPH_2_8, TIT_3_5)
    assert texts == {
        EPH_2_8: "Frase de prueba que une Romanos 3:24 con Efesios 2:8.",
        TIT_3_5: None,
    }


@pytest.mark.parametrize(
    "params",
    [
        {"verse": ROM_3_24},
        {"others": str(EPH_2_8)},
        {"verse": ROM_3_24, "others": ""},
        {"verse": ROM_3_24, "others": "abc"},
        {"verse": ROM_3_24, "others": "1,,2"},
        {"verse": ROM_3_24, "others": ",".join(["1001001"] * 31)},
        {"verse": ROM_3_24, "others": "0"},
        {"verse": ROM_3_24, "others": "99999999999"},
        {"verse": 0, "others": str(EPH_2_8)},
    ],
)
def test_invalid_parameters_are_rejected(database_url, params):
    with make_client(database_url, FakeGenerator()) as client:
        assert client.get("/api/explanations", params=params).status_code == 422


def test_settings_read_ollama_from_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_URL", " http://host.docker.internal:11434 \n")
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    settings = Settings.from_env()
    assert settings.ollama_url == "http://host.docker.internal:11434"
    assert settings.ollama_model == "gemma4:e4b"


def test_app_uses_ollama_only_when_configured(database_url):
    with_ollama = create_app(
        Settings(database_url=database_url, allowed_origins=[], ollama_url="http://x:11434")
    )
    without = create_app(Settings(database_url=database_url, allowed_origins=[]))
    assert with_ollama.state.generator.model == "gemma4:e4b"
    assert without.state.generator is None
```

- [ ] **Step 3: Reemplazar `backend/tests/test_load.py`**

Añade al final el test que comprueba que la ingesta no borra las frases:

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


def test_load_keeps_relation_explanations(database_url):
    with psycopg.connect(database_url) as conn:
        apply_schema(conn)
        conn.execute("TRUNCATE relation_explanations")
        conn.execute(
            "INSERT INTO relation_explanations (verse_a, verse_b, text, model)"
            " VALUES (%s, %s, 'Una frase guardada antes de la ingesta.', 'm')",
            (ROM_3_24, TIT_3_5),
        )
        conn.commit()
        load(conn, VERSES, EDGES)
        assert conn.execute("SELECT count(*) FROM relation_explanations").fetchone() == (1,)
        conn.execute("TRUNCATE relation_explanations")
        conn.commit()
```

- [ ] **Step 4: Ejecutar y comprobar que fallan**

Run: `docker compose run --rm api pytest tests/test_explanations.py tests/test_load.py -q 2>&1 | tail -3`
Expected: `1 failed, 5 passed, 19 errors`. Los errores salen del fixture que vacía `relation_explanations` (`UndefinedTable`: la tabla aún no existe) y el fallo es `test_load_keeps_relation_explanations`, por lo mismo.

- [ ] **Step 5: Reemplazar `backend/sql/schema.sql`**

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

-- Frases que explican una relación entre dos versículos, generadas con un modelo de
-- lenguaje. Una por par sin dirección (verse_a < verse_b). Sin claves foráneas a
-- propósito: la ingesta vacía verses y edges, y no debe borrar estas frases.
CREATE TABLE IF NOT EXISTS relation_explanations (
  verse_a    integer NOT NULL,
  verse_b    integer NOT NULL,
  text       text NOT NULL,
  model      text NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (verse_a, verse_b),
  CHECK (verse_a < verse_b)
);
```

- [ ] **Step 6: Reemplazar `backend/app/config.py` y `backend/app/schemas.py`**

`backend/app/config.py`:

```python
"""Configuración de la API a partir de variables de entorno."""

import os
from dataclasses import dataclass

from app.ollama import DEFAULT_MODEL

DEFAULT_ORIGINS = "http://localhost:5173"


@dataclass(frozen=True)
class Settings:
    database_url: str
    allowed_origins: list[str]
    # Sin OLLAMA_URL la API solo lee las frases ya guardadas (así funciona en Render).
    ollama_url: str = ""
    ollama_model: str = DEFAULT_MODEL

    @classmethod
    def from_env(cls) -> "Settings":
        origins = os.environ.get("ALLOWED_ORIGINS", DEFAULT_ORIGINS)
        return cls(
            database_url=os.environ.get("DATABASE_URL", "").strip(),
            allowed_origins=[o.strip().rstrip("/") for o in origins.split(",") if o.strip()],
            ollama_url=os.environ.get("OLLAMA_URL", "").strip(),
            ollama_model=os.environ.get("OLLAMA_MODEL", "").strip() or DEFAULT_MODEL,
        )
```

`backend/app/schemas.py`:

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


class Explanation(BaseModel):
    other: int
    text: str | None


class ExplanationsResponse(BaseModel):
    verse: int
    explanations: list[Explanation]


class Verse(BaseModel):
    id: int
    ref: str
    text: str


class PassageResponse(BaseModel):
    ref: str
    verses: list[Verse]
```

- [ ] **Step 7: Implementar `backend/app/explanations.py`**

```python
"""Frases que explican las relaciones de un versículo: se leen de la BD o se generan con Ollama."""

import asyncio
import logging

from psycopg_pool import AsyncConnectionPool

from app.db import query_connection
from app.ollama import Generator, VersePair, clean_phrase
from app.refs import format_ref
from app.schemas import Explanation, ExplanationsResponse
from app.search import TRANSLATION

MAX_OTHERS = 30

log = logging.getLogger(__name__)

# Los `others` que forman una referencia cruzada con `verse`, en cualquier sentido.
LINKED_SQL = """
SELECT DISTINCT CASE WHEN from_verse_id = %(verse)s THEN to_verse_id ELSE from_verse_id END AS other
FROM edges
WHERE (from_verse_id = %(verse)s AND to_verse_id = ANY(%(others)s))
   OR (to_verse_id = %(verse)s AND from_verse_id = ANY(%(others)s))
"""

CACHED_SQL = """
SELECT verse_a, verse_b, text
FROM relation_explanations
WHERE verse_a = ANY(%(a)s) AND verse_b = ANY(%(b)s)
"""

TEXTS_SQL = """
SELECT v.id, b.name_es, v.chapter, v.verse, vt.text
FROM verses v
JOIN books b ON b.id = v.book_id
JOIN verse_texts vt ON vt.verse_id = v.id AND vt.translation = %(translation)s
WHERE v.id = ANY(%(ids)s)
"""

INSERT_SQL = """
INSERT INTO relation_explanations (verse_a, verse_b, text, model)
VALUES (%s, %s, %s, %s)
ON CONFLICT (verse_a, verse_b) DO NOTHING
"""


def pair_key(x: int, y: int) -> tuple[int, int]:
    """La relación no tiene dirección: se guarda con el ID menor primero."""
    return (x, y) if x < y else (y, x)


def verse_pair(key: tuple[int, int], texts: dict[int, dict]) -> VersePair:
    a, b = texts[key[0]], texts[key[1]]
    return VersePair(
        a_ref=format_ref(a["name_es"], a["chapter"], a["verse"]),
        a_text=a["text"],
        b_ref=format_ref(b["name_es"], b["chapter"], b["verse"]),
        b_text=b["text"],
    )


async def explain(
    pool: AsyncConnectionPool, generator: Generator | None, verse: int, others: list[int]
) -> ExplanationsResponse:
    async with query_connection(pool) as conn:
        cur = await conn.execute(LINKED_SQL, {"verse": verse, "others": others})
        linked = {row["other"] for row in await cur.fetchall()}
        keys = {pair_key(verse, other) for other in linked}
        cur = await conn.execute(
            CACHED_SQL, {"a": [k[0] for k in keys], "b": [k[1] for k in keys]}
        )
        known = {
            (row["verse_a"], row["verse_b"]): row["text"]
            for row in await cur.fetchall()
            if (row["verse_a"], row["verse_b"]) in keys
        }
        missing = sorted(keys - known.keys())
        texts: dict[int, dict] = {}
        if missing and generator is not None:
            ids = {verse, *(other for key in missing for other in key)}
            cur = await conn.execute(TEXTS_SQL, {"translation": TRANSLATION, "ids": list(ids)})
            texts = {row["id"]: row for row in await cur.fetchall()}

    # La llamada al modelo puede tardar decenas de segundos: se hace sin conexión del pool.
    if missing and generator is not None and all(i in texts for key in missing for i in key):
        try:
            raw = await asyncio.to_thread(
                generator.generate, [verse_pair(key, texts) for key in missing]
            )
        except Exception as error:  # noqa: BLE001 — sin modelo, el panel muestra el versículo
            log.warning("No se pudieron generar frases: %s", error)
            raw = []
        generated = {
            key: text
            for key, text in zip(missing, (clean_phrase(r) for r in raw))
            if text is not None
        }
        if generated:
            async with query_connection(pool) as conn:
                async with conn.cursor() as cur:
                    await cur.executemany(
                        INSERT_SQL,
                        [(a, b, text, generator.model) for (a, b), text in generated.items()],
                    )
            known.update(generated)

    return ExplanationsResponse(
        verse=verse,
        explanations=[
            Explanation(
                other=other,
                text=known.get(pair_key(verse, other)) if other in linked else None,
            )
            for other in others
        ],
    )
```

- [ ] **Step 8: Reemplazar `backend/app/routes.py` y `backend/app/main.py`**

`backend/app/routes.py`:

```python
"""Endpoints de la API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path, Query, Request
from psycopg_pool import AsyncConnectionPool

from app import explanations, search
from app.db import get_pool, query_connection
from app.schemas import ExplanationsResponse, PassageResponse, SearchResponse

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


def parse_ids(raw: str) -> list[int]:
    """Convierte "1001001,43003016" en una lista de IDs, o lanza un 422."""
    try:
        ids = [int(part) for part in raw.split(",")]
    except ValueError:
        raise HTTPException(422, "others debe ser una lista de IDs separados por comas") from None
    if not 1 <= len(ids) <= explanations.MAX_OTHERS:
        raise HTTPException(422, f"others admite de 1 a {explanations.MAX_OTHERS} IDs")
    if not all(1 <= i <= MAX_VERSE_ID for i in ids):
        raise HTTPException(422, "others contiene IDs fuera de rango")
    return ids


@router.get("/explanations")
async def explanations_endpoint(
    pool: Pool,
    request: Request,
    verse: Annotated[int, Query(ge=1, le=MAX_VERSE_ID)],
    others: Annotated[str, Query(max_length=400)],
) -> ExplanationsResponse:
    return await explanations.explain(
        pool, request.app.state.generator, verse, parse_ids(others)
    )
```

`backend/app/main.py`:

```python
"""Aplicación FastAPI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings
from app.db import create_pool
from app.ollama import Generator, OllamaGenerator
from app.routes import router

HEALTH_DB_TIMEOUT_SECONDS = 3
NOT_LOADED = "La base de datos no tiene los datos cargados"


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


def default_generator(settings: Settings) -> Generator | None:
    if not settings.ollama_url:
        return None
    return OllamaGenerator(settings.ollama_url, settings.ollama_model)


def create_app(settings: Settings | None = None, generator: Generator | None = None) -> FastAPI:
    """`generator` sustituye al de Ollama (en los tests). Si falta, se decide por OLLAMA_URL."""
    app = FastAPI(title="bible-graph", lifespan=lifespan)
    app.state.settings = settings or Settings.from_env()
    app.state.generator = generator or default_generator(app.state.settings)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=app.state.settings.allowed_origins,
        allow_methods=["GET"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.exception_handler(psycopg.OperationalError)
    async def database_unavailable(request: Request, exc: psycopg.OperationalError) -> JSONResponse:
        # Cubre BD inaccesible, pool agotado (PoolTimeout) y statement_timeout (QueryCanceled).
        return JSONResponse(status_code=503, content={"detail": "Base de datos no disponible"})

    @app.exception_handler(psycopg.errors.UndefinedTable)
    @app.exception_handler(psycopg.errors.UndefinedObject)
    async def database_not_loaded(request: Request, exc: psycopg.Error) -> JSONResponse:
        # Faltan las tablas o la configuración de búsqueda: no se ha ejecutado la ingesta.
        return JSONResponse(status_code=503, content={"detail": NOT_LOADED})

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/db")
    async def health_db(request: Request) -> dict[str, str]:
        async with request.app.state.pool.connection(timeout=HEALTH_DB_TIMEOUT_SECONDS) as conn:
            cur = await conn.execute("SELECT EXISTS (SELECT 1 FROM verses) AS loaded")
            row = await cur.fetchone()
        if not row["loaded"]:
            raise HTTPException(503, NOT_LOADED)
        return {"status": "ok"}

    return app


app = create_app()
```

- [ ] **Step 9: Ejecutar todos los tests y comprobar que pasan**

Run: `docker compose run --rm api pytest -q | tail -1`
Expected: `154 passed`.

- [ ] **Step 10: Aplicar el esquema nuevo a la BD de desarrollo**

Run: `docker compose run --rm ingest 2>&1 | grep cargadas && docker compose exec -T db psql -U bible -d bible -Atc "SELECT count(*) FROM relation_explanations"`
Expected: `Aristas cargadas: 344542` y `0`.

- [ ] **Step 11: Probar con Ollama real**

Run (dos veces seguidas):

```bash
curl -s -w "\n%{time_total}s\n" "http://127.0.0.1:8010/api/explanations?verse=46013004&others=46013007,43013034,45013010,48005022,62004008"
```

Expected: la primera vez, entre 5 y 20 segundos y frases en español para `46013007`, `43013034`, `45013010` y `48005022`; `62004008` sale `null` porque no tiene referencia cruzada con 1 Corintios 13:4. La segunda vez, las mismas frases en menos de medio segundo.

Después, con Ollama cerrado (en PowerShell: `Stop-Process -Name ollama`; se vuelve a abrir desde el menú Inicio), repite la llamada con otro versículo, por ejemplo `verse=45003024&others=49002008`: debe devolver 200 con `"text":null`.

- [ ] **Step 12: Comprobar que una generación no bloquea la API**

Con Ollama abierto, vacía las frases y lanza a la vez una generación en frío y una búsqueda:

```bash
docker compose exec -T db psql -U bible -d bible -c "TRUNCATE relation_explanations"
curl -s -o /dev/null "http://127.0.0.1:8010/api/explanations?verse=46013004&others=46013007,43013034" &
sleep 1; curl -s -o /dev/null -w "búsqueda: %{http_code} en %{time_total}s\n" "http://127.0.0.1:8010/api/search?q=gracia"; wait
```

Expected: `búsqueda: 200 en` menos de 1 segundo, aunque la generación siga en curso.

- [ ] **Step 13: Commit**

```bash
git add backend
git commit -m "Add relation explanations table and endpoint

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Pregeneración de frases en lote

**Files:**
- Create: `backend/ingest/explain.py`
- Test: `backend/tests/test_explain_cli.py`

**Interfaces:**
- Consumes: `app.explanations.INSERT_SQL`, `TEXTS_SQL`, `verse_pair`; `app.ollama` (`DEFAULT_MODEL`, `Generator`, `OllamaGenerator`, `clean_phrase`); `ingest.__main__.database_url_from_env`, `describe_target`; `tests.fakes.FakeGenerator`.
- Produces:
  - `ingest.explain.Progress(generated: int, discarded: int)`.
  - `ingest.explain.run(conn, generator, limit, batch, report=...) -> Progress`.
  - `ingest.explain.main(argv) -> int`. Códigos: 0 bien, 2 falta `DATABASE_URL` u `OLLAMA_URL`, 130 interrumpido con Ctrl+C.
  - Comando `docker compose run --rm ingest python -m ingest.explain [--limit N] [--batch B]`.

Contexto: los pares descartados (frase inválida o lote fallido) se recuerdan durante la ejecución para no reintentarlos en bucle; en una ejecución posterior se vuelven a intentar.

- [ ] **Step 1: Escribir los tests que fallan**

`backend/tests/test_explain_cli.py`:

```python
import psycopg
import pytest
from psycopg.rows import dict_row

from ingest.explain import main, run
from tests.data import EPH_2_8, GEN_1_1, JOHN_1_14, ROM_3_24
from tests.fakes import FakeGenerator


@pytest.fixture
def conn(database_url):
    with psycopg.connect(database_url, row_factory=dict_row) as connection:
        connection.execute("TRUNCATE relation_explanations")
        connection.commit()
        yield connection
        connection.execute("TRUNCATE relation_explanations")
        connection.commit()


def stored_pairs(conn):
    rows = conn.execute("SELECT verse_a, verse_b FROM relation_explanations ORDER BY 1, 2")
    return [(row["verse_a"], row["verse_b"]) for row in rows]


def test_run_generates_the_most_voted_pairs_first(conn):
    progress = run(conn, FakeGenerator(), limit=2, batch=8)
    # Génesis 1:1 - Juan 1:14 (50 votos) y Romanos 3:24 - Efesios 2:8 (40 en un sentido).
    assert progress.generated == 2
    assert stored_pairs(conn) == [(GEN_1_1, JOHN_1_14), (ROM_3_24, EPH_2_8)]


def test_run_respects_the_limit_across_batches(conn):
    generator = FakeGenerator()
    progress = run(conn, generator, limit=5, batch=2)
    assert progress.generated == 5
    assert [len(call) for call in generator.calls] == [2, 2, 1]


def test_run_skips_pairs_that_already_have_a_phrase(conn):
    run(conn, FakeGenerator(), limit=2, batch=8)
    generator = FakeGenerator()
    run(conn, generator, limit=1, batch=8)
    [[pair]] = generator.calls
    assert (pair.a_ref, pair.b_ref) != ("Génesis 1:1", "Juan 1:14")
    assert len(stored_pairs(conn)) == 3


def test_run_stops_when_every_pair_is_done(conn):
    # El dataset de tests tiene 8 pares sin dirección con peso >= 0.
    progress = run(conn, FakeGenerator(), limit=100, batch=3)
    assert progress.generated == 8
    assert len(stored_pairs(conn)) == 8


def test_run_discards_invalid_phrases_without_retrying_them(conn):
    generator = FakeGenerator(phrase=lambda pair: "corta")
    progress = run(conn, generator, limit=100, batch=4)
    assert progress.generated == 0
    assert progress.discarded == 8
    assert len(generator.calls) == 2
    assert stored_pairs(conn) == []


def test_run_survives_a_failing_batch(conn):
    progress = run(conn, FakeGenerator(error=RuntimeError("caído")), limit=4, batch=4)
    assert (progress.generated, progress.discarded) == (0, 8)


def test_main_needs_ollama_url(monkeypatch, capsys):
    monkeypatch.setenv("DATABASE_URL", "postgresql://x")
    monkeypatch.delenv("OLLAMA_URL", raising=False)
    assert main([]) == 2
    assert "OLLAMA_URL" in capsys.readouterr().err


def test_main_needs_database_url(monkeypatch, capsys):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    assert main([]) == 2
    assert "DATABASE_URL" in capsys.readouterr().err
```

- [ ] **Step 2: Ejecutar y comprobar que fallan**

Run: `docker compose run --rm api pytest tests/test_explain_cli.py -q 2>&1 | tail -3`
Expected: `ModuleNotFoundError: No module named 'ingest.explain'`.

- [ ] **Step 3: Implementar `backend/ingest/explain.py`**

```python
"""Pregenera frases de relación, de las referencias más votadas a las menos.

python -m ingest.explain [--limit N] [--batch B]

Se puede interrumpir con Ctrl+C y volver a lanzar: salta los pares que ya tienen frase.
"""

import argparse
import os
import sys
import time
from collections.abc import Callable
from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row

from app.explanations import INSERT_SQL, TEXTS_SQL, verse_pair
from app.ollama import DEFAULT_MODEL, Generator, OllamaGenerator, clean_phrase
from app.search import TRANSLATION
from ingest.__main__ import database_url_from_env, describe_target

# Pares sin dirección, con el mayor peso de los dos sentidos, que aún no tienen frase.
PENDING_SQL = """
SELECT p.verse_a, p.verse_b
FROM (
  SELECT least(from_verse_id, to_verse_id) AS verse_a,
         greatest(from_verse_id, to_verse_id) AS verse_b,
         max(weight) AS weight
  FROM edges
  WHERE from_verse_id <> to_verse_id
  GROUP BY 1, 2
) p
LEFT JOIN relation_explanations r ON r.verse_a = p.verse_a AND r.verse_b = p.verse_b
WHERE r.verse_a IS NULL
  AND NOT EXISTS (
    SELECT 1 FROM unnest(%(skip_a)s::integer[], %(skip_b)s::integer[]) AS s(verse_a, verse_b)
    WHERE s.verse_a = p.verse_a AND s.verse_b = p.verse_b
  )
ORDER BY p.weight DESC, p.verse_a, p.verse_b
LIMIT %(limit)s
"""


@dataclass
class Progress:
    generated: int = 0
    discarded: int = 0


def pending(conn: psycopg.Connection, skip: set[tuple[int, int]], limit: int) -> list[tuple[int, int]]:
    params = {"skip_a": [k[0] for k in skip], "skip_b": [k[1] for k in skip], "limit": limit}
    rows = conn.execute(PENDING_SQL, params).fetchall()
    return [(row["verse_a"], row["verse_b"]) for row in rows]


def run(
    conn: psycopg.Connection,
    generator: Generator,
    limit: int,
    batch: int,
    report: Callable[[Progress], None] = lambda progress: None,
) -> Progress:
    """Genera hasta `limit` frases. Los pares descartados no se reintentan en esta ejecución."""
    progress = Progress()
    skip: set[tuple[int, int]] = set()
    while progress.generated < limit:
        keys = pending(conn, skip, min(batch, limit - progress.generated))
        if not keys:
            break
        ids = list({i for key in keys for i in key})
        texts = {
            row["id"]: row
            for row in conn.execute(TEXTS_SQL, {"translation": TRANSLATION, "ids": ids})
        }
        try:
            raw = generator.generate([verse_pair(key, texts) for key in keys])
        except Exception as error:  # noqa: BLE001
            print(f"Lote descartado: {error}", file=sys.stderr)
            raw = [""] * len(keys)
        rows = []
        for key, text in zip(keys, (clean_phrase(r) for r in raw)):
            if text is None:
                skip.add(key)
                progress.discarded += 1
            else:
                rows.append((*key, text, generator.model))
        with conn.cursor() as cur:
            cur.executemany(INSERT_SQL, rows)
        conn.commit()
        progress.generated += len(rows)
        report(progress)
    return progress


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m ingest.explain")
    parser.add_argument("--limit", type=int, default=1000, help="frases a generar (1000)")
    parser.add_argument("--batch", type=int, default=8, help="pares por llamada al modelo (8)")
    args = parser.parse_args(argv)

    database_url = database_url_from_env()
    if not database_url:
        print("Falta la variable de entorno DATABASE_URL", file=sys.stderr)
        return 2
    ollama_url = os.environ.get("OLLAMA_URL", "").strip()
    if not ollama_url:
        print("Falta la variable de entorno OLLAMA_URL", file=sys.stderr)
        return 2
    model = os.environ.get("OLLAMA_MODEL", "").strip() or DEFAULT_MODEL
    generator = OllamaGenerator(ollama_url, model)
    print(f"Destino: {describe_target(database_url)} · modelo {model} en {ollama_url}")

    started = time.monotonic()

    def report(progress: Progress) -> None:
        hours = max(time.monotonic() - started, 1) / 3600
        print(
            f"Generadas {progress.generated} · descartadas {progress.discarded}"
            f" · {progress.generated / hours:.0f} frases/hora",
            flush=True,
        )

    with psycopg.connect(database_url, row_factory=dict_row) as conn:
        try:
            progress = run(conn, generator, args.limit, args.batch, report)
        except KeyboardInterrupt:
            print("Interrumpido. Lo generado hasta ahora queda guardado.")
            return 130
    print(f"Terminado: {progress.generated} frases nuevas, {progress.discarded} descartadas.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Ejecutar todos los tests y comprobar que pasan**

Run: `docker compose run --rm api pytest -q | tail -1`
Expected: `162 passed`.

- [ ] **Step 5: Probar con Ollama real**

Run: `docker compose run --rm ingest python -m ingest.explain --limit 24`
Expected: tres líneas de avance (`Generadas 8`, `16`, `24`), un ritmo del orden de 10.000 frases por hora y `Terminado: 24 frases nuevas, 0 descartadas.`

- [ ] **Step 6: Commit**

```bash
git add backend
git commit -m "Add batch pregeneration of relation phrases

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Frontend: grupos de libros, textos, tema y datos del grafo

**Files:**
- Modify: `frontend/package.json`, `frontend/package-lock.json` (con `npm install`)
- Create: `frontend/src/groups.ts`, `frontend/src/text.ts`, `frontend/src/theme.ts`
- Modify: `frontend/src/graph.ts`, `frontend/src/api.ts` (se reemplazan enteros)
- Test: `frontend/src/graph.test.ts` (se reemplaza entero), `frontend/src/support.test.ts`

**Interfaces:**
- Consumes: la API de las tareas 3 y del MVP.
- Produces:
  - `groups.ts`: `BookGroup { id, name, firstBook, lastBook }`, `BOOK_GROUPS`, `bookOf(id)`, `groupOf(id)`, `groupVar(group)` (`"--group-<id>"`).
  - `text.ts`: `SNIPPET_LENGTH = 40`, `snippet(text, max?)`, `capitalize(text)`.
  - `theme.ts`: `Theme = "dark" | "light"`, `readTheme(storage)`, `writeTheme(storage, theme)`, `applyTheme(storage, theme)`, `cssVar(name)`.
  - `graph.ts`: `TERM_ID = "term"`, `MAX_EXPLANATIONS = 30`, `edgeWidth`, `edgeId`, `colorClass(node)`, `toElements(response)` (con el nodo central, clases `seed`/`neighbor`, `c-<grupo|seed>` y aristas `to-<grupo|seed>`), `Connection`, `connectionsOf`, `relationsOf` (una fila por versículo) y `explanationTargets`.
  - `api.ts`: tipos `Explanation` y `ExplanationsResponse`, `explanationsUrl(base, verse, others)` y `fetchExplanations(verse, others, signal)`.

Contexto: la interfaz antigua sigue compilando con estos cambios; la tarea 6 la sustituye.

- [ ] **Step 1: Instalar las dependencias nuevas**

Run:

```bash
docker compose up -d --build frontend
until docker compose exec -T frontend test -f node_modules/.bin/vitest 2>/dev/null; do sleep 3; done
docker compose exec -T frontend npm install lucide-react @fontsource-variable/inter
grep -E '"lucide-react"|"@fontsource-variable/inter"' frontend/package.json
```

Expected: dos líneas con versiones `^1.` de `lucide-react` y `^5.` de `@fontsource-variable/inter` (o posteriores compatibles).

- [ ] **Step 2: Escribir los tests que fallan**

`frontend/src/graph.test.ts`:

```ts
import { describe, expect, it } from "vitest";
import { apiBase, explanationsUrl, passageUrl, searchUrl, type SearchResponse } from "./api";
import {
  connectionsOf,
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
```

`frontend/src/support.test.ts`:

```ts
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
```

- [ ] **Step 3: Ejecutar y comprobar que fallan**

Run: `docker compose exec -T -e NO_COLOR=1 frontend npx vitest run 2>&1 | grep -E "Error|Test Files"`
Expected: `support.test.ts` no carga (`Cannot find module './groups'`) y `graph.test.ts` tiene 13 tests fallidos (faltan el nodo central, las clases nuevas y las funciones nuevas).

- [ ] **Step 4: Crear `groups.ts`, `text.ts` y `theme.ts`**

`frontend/src/groups.ts`:

```ts
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
```

`frontend/src/text.ts`:

```ts
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
```

`frontend/src/theme.ts`:

```ts
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
```

- [ ] **Step 5: Reemplazar `frontend/src/graph.ts` y `frontend/src/api.ts`**

`frontend/src/graph.ts`:

```ts
import type { ElementDefinition } from "cytoscape";
import type { GraphEdge, GraphNode, SearchResponse } from "./api";
import { groupOf } from "./groups";
import { capitalize, snippet } from "./text";

/** ID del nodo central con el término buscado. Los versículos usan su ID numérico. */
export const TERM_ID = "term";
export const MAX_EXPLANATIONS = 30;

const MIN_EDGE_WIDTH = 0.6;
const MAX_EDGE_WIDTH = 4;

/** Grosor de la arista: crece con el logaritmo del peso, porque los votos van de 1 a varios cientos. */
export function edgeWidth(weight: number): number {
  const width = MIN_EDGE_WIDTH + 1.2 * Math.log10(Math.max(weight, 1));
  return Math.min(MAX_EDGE_WIDTH, Math.round(width * 10) / 10);
}

export function edgeId(edge: Pick<GraphEdge, "source" | "target">): string {
  return `e${edge.source}-${edge.target}`;
}

/** Color con que se ilumina una arista o se pinta un nodo: ámbar si es semilla, si no el de su grupo. */
export function colorClass(node: GraphNode): string {
  return node.is_seed ? "seed" : groupOf(node.id).id;
}

/** Convierte la respuesta de la API en elementos de Cytoscape, con el término en el centro. */
export function toElements(response: SearchResponse): ElementDefinition[] {
  const byId = new Map(response.nodes.map((node) => [node.id, node]));
  const seeds = response.nodes.filter((node) => node.is_seed);
  if (response.nodes.length === 0) return [];

  const term: ElementDefinition = {
    group: "nodes",
    data: {
      id: TERM_ID,
      label: capitalize(response.query),
      snippet: `${response.total_matches} ${response.total_matches === 1 ? "pasaje" : "pasajes"}`,
    },
    classes: "term",
  };
  const nodes: ElementDefinition[] = response.nodes.map((node) => ({
    group: "nodes",
    data: { id: String(node.id), label: node.label, snippet: snippet(node.text) },
    classes: `${node.is_seed ? "seed" : "neighbor"} c-${colorClass(node)}`,
  }));
  const termEdges: ElementDefinition[] = seeds.map((seed) => ({
    group: "edges",
    data: { id: `t${seed.id}`, source: TERM_ID, target: String(seed.id), width: 1 },
    classes: "term-edge to-seed",
  }));
  const edges: ElementDefinition[] = response.edges
    .filter((edge) => byId.has(edge.source) && byId.has(edge.target))
    .map((edge) => ({
      group: "edges",
      data: {
        id: edgeId(edge),
        source: String(edge.source),
        target: String(edge.target),
        width: edgeWidth(edge.weight),
      },
      classes: `to-${colorClass(byId.get(edge.target)!)}`,
    }));
  return [term, ...nodes, ...termEdges, ...edges];
}

export interface Connection {
  /** Identificador único de la conexión dentro del panel. */
  key: string;
  /** El nodo del otro extremo. */
  nodeId: number;
  /** Texto a mostrar: la referencia del otro extremo, con rango si la arista lo tiene. */
  label: string;
  weight: number;
  /** "out": el versículo seleccionado remite al otro. "in": el otro remite a él. */
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

/**
 * Relaciones del panel: una por versículo relacionado aunque haya referencia en los dos
 * sentidos. Se queda la de más peso y conserva el rango si alguna de las dos lo tiene.
 */
export function relationsOf(nodeId: number, response: SearchResponse): Connection[] {
  const byNode = new Map<number, Connection>();
  for (const connection of connectionsOf(nodeId, response)) {
    const kept = byNode.get(connection.nodeId);
    if (!kept) {
      byNode.set(connection.nodeId, connection);
    } else if (kept.rangeEndId === null && connection.rangeEndId !== null) {
      byNode.set(connection.nodeId, {
        ...kept,
        label: connection.label,
        rangeEndId: connection.rangeEndId,
      });
    }
  }
  return [...byNode.values()];
}

/** Versículos cuya frase se pide a la API: sin repetir, en el orden del panel y como máximo 30. */
export function explanationTargets(connections: Connection[]): number[] {
  return [...new Set(connections.map((c) => c.nodeId))].slice(0, MAX_EXPLANATIONS);
}
```

`frontend/src/api.ts`:

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

export interface Explanation {
  other: number;
  text: string | null;
}

export interface ExplanationsResponse {
  verse: number;
  explanations: Explanation[];
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

export function explanationsUrl(base: string, verse: number, others: number[]): string {
  const query = new URLSearchParams({ verse: String(verse), others: others.join(",") });
  return `${base}/api/explanations?${query}`;
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

export function fetchExplanations(
  verse: number,
  others: number[],
  signal: AbortSignal,
): Promise<ExplanationsResponse> {
  return getJson<ExplanationsResponse>(explanationsUrl(API_BASE, verse, others), signal);
}
```

- [ ] **Step 6: Ejecutar los tests y el build**

Run: `docker compose exec -T -e NO_COLOR=1 frontend npx vitest run 2>&1 | grep "Tests " && docker compose exec -T frontend npm run build 2>&1 | grep -E "built|error"`
Expected: `Tests  41 passed (41)` y `✓ built`.

- [ ] **Step 7: Commit**

```bash
git add frontend
git commit -m "Add book groups, theme helpers and central term node

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Frontend: la interfaz nueva

**Files:**
- Modify: `frontend/index.html`, `frontend/src/main.tsx`, `frontend/src/styles.css`, `frontend/src/App.tsx` (se reemplazan enteros)
- Create: `frontend/public/favicon.svg`
- Create: `frontend/src/components/TopBar.tsx`, `Sidebar.tsx`, `Legend.tsx`
- Modify: `frontend/src/components/SearchBar.tsx`, `GraphView.tsx`, `VersePanel.tsx` (se reemplazan enteros)
- Delete: `frontend/src/components/LimitControls.tsx`

**Interfaces:**
- Consumes: todo lo que produce la tarea 5.
- Produces:
  - `TopBar({ query, onSearch, theme, onToggleTheme, onToggleSidebar })`.
  - `SearchBar({ query, onSearch })`, `MIN_QUERY_LENGTH`, `MAX_QUERY_LENGTH`.
  - `Sidebar({ limits, onChange, response, open })`, `Limits`, `DEFAULT_LIMITS = { seeds: 5, neighbors: 10 }`.
  - `Legend()` y `dotStyle(colorVar)`.
  - `GraphView({ response, theme, selectedId, onSelect })`, con capa de etiquetas HTML, zoom y leyenda.
  - `VersePanel({ node, nodes, connections, explanations, passage, onSelectNode, onOpenPassage, onClose })`, y los tipos `PassageState` y `ExplanationsState`.

Contexto: esta tarea no añade tests automáticos; la lógica testeable vive en la tarea 5. Se verifica con tipos, build y una comprobación en navegador. Tres detalles del código que no se deben "simplificar":
- `applyTheme` se llama en el inicializador del estado y en el botón, no en un `useEffect`: los efectos del hijo (`GraphView`) se ejecutan antes que los del padre y leerían los colores del tema anterior.
- El centrado del nodo seleccionado espera 60 ms y llama a `cy.resize()`, porque el panel estrecha el lienzo en ese mismo render.
- Las etiquetas son elementos DOM creados una vez y recolocados en cada evento `render` de Cytoscape, sin pasar por React.

- [ ] **Step 1: Página, favicon y punto de entrada**

`frontend/index.html`:

```html
<!doctype html>
<html lang="es">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <title>Biblia en red</title>
  </head>
  <body>
    <div id="root"></div>
    <script type="module" src="/src/main.tsx"></script>
  </body>
</html>
```

`frontend/public/favicon.svg`:

```xml
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 32 32"><rect width="32" height="32" rx="8" fill="#0a0e13"/><path d="M11.5 13.5 9 10.5M20.5 13.5l2.5-2M19.5 20l2 3.2" stroke="#3a4452" stroke-width="1.2"/><circle cx="16" cy="16" r="5" fill="#0a0e13" stroke="#f2b35b" stroke-width="2"/><circle cx="7" cy="9" r="2.5" fill="#0a0e13" stroke="#5b9dff" stroke-width="1.5"/><circle cx="25" cy="10" r="2.5" fill="#0a0e13" stroke="#66d19e" stroke-width="1.5"/><circle cx="23" cy="25" r="2.5" fill="#0a0e13" stroke="#a78bfa" stroke-width="1.5"/></svg>
```

`frontend/src/main.tsx`:

```tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "@fontsource-variable/inter";
import { App } from "./App";
import "./styles.css";

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);
```

- [ ] **Step 2: Estilos**

`frontend/src/styles.css`:

```css
:root {
  --bg: #0a0e13;
  --surface: #0e1319;
  --surface-2: #141a22;
  --border: #1d2530;
  --text: #e7eaef;
  --text-soft: #b9c0cb;
  --muted: #7d8795;
  --accent: #f2b35b;
  --accent-soft: rgba(242, 179, 91, 0.14);
  --edge: #3a4452;
  --node-fill: #0e1319;
  --group-ley: #f07c7c;
  --group-historicos: #c9956b;
  --group-poeticos: #4ecdc4;
  --group-profetas: #a78bfa;
  --group-evangelios: #5b9dff;
  --group-cartas: #66d19e;
  --shadow: 0 10px 30px rgba(0, 0, 0, 0.45);
  --radius: 10px;
  color-scheme: dark;
  font-family: "Inter Variable", system-ui, -apple-system, "Segoe UI", sans-serif;
  color: var(--text);
}

:root[data-theme="light"] {
  --bg: #f4f3ef;
  --surface: #ffffff;
  --surface-2: #f1f0ec;
  --border: #e2e0da;
  --text: #1a2029;
  --text-soft: #3d4654;
  --muted: #6c7482;
  --accent: #d48a1f;
  --accent-soft: rgba(212, 138, 31, 0.12);
  --edge: #c3c8d0;
  --node-fill: #ffffff;
  --group-ley: #d9534f;
  --group-historicos: #a0673a;
  --group-poeticos: #1f9e95;
  --group-profetas: #7c5ce0;
  --group-evangelios: #2f74e0;
  --group-cartas: #2e9e62;
  --shadow: 0 10px 30px rgba(20, 24, 32, 0.12);
  color-scheme: light;
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
  -webkit-font-smoothing: antialiased;
}

button {
  font: inherit;
  color: inherit;
  cursor: pointer;
}

.icon-button {
  display: inline-grid;
  place-items: center;
  width: 36px;
  height: 36px;
  padding: 0;
  color: var(--muted);
  background: transparent;
  border: 1px solid var(--border);
  border-radius: 999px;
}

.icon-button:hover {
  color: var(--text);
  border-color: var(--muted);
}

/* --- Estructura --- */

.app {
  display: grid;
  grid-template-rows: 60px 1fr;
  grid-template-columns: 260px 1fr auto;
  height: 100%;
  background: var(--bg);
}

.top-bar {
  display: flex;
  grid-column: 1 / -1;
  align-items: center;
  gap: 16px;
  padding: 0 18px;
  background: var(--surface);
  border-bottom: 1px solid var(--border);
}

.brand {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 220px;
  margin: 0;
  color: var(--text-soft);
  font-size: 0.78rem;
  font-weight: 500;
  letter-spacing: 0.28em;
  text-transform: uppercase;
}

.brand svg {
  color: var(--text-soft);
}

.search-bar {
  position: relative;
  flex: 1;
  max-width: 460px;
  margin: 0 auto;
}

.search-bar svg {
  position: absolute;
  top: 50%;
  left: 14px;
  color: var(--muted);
  transform: translateY(-50%);
  pointer-events: none;
}

.search-bar input {
  width: 100%;
  height: 38px;
  padding: 0 14px 0 40px;
  font: inherit;
  font-size: 0.92rem;
  color: var(--text);
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 999px;
  outline: none;
}

.search-bar input:focus {
  border-color: var(--accent);
  box-shadow: 0 0 0 3px var(--accent-soft);
}

.menu-button {
  display: none;
}

/* --- Barra lateral --- */

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 28px;
  padding: 24px 20px;
  overflow-y: auto;
  background: var(--surface);
  border-right: 1px solid var(--border);
}

.control h2 {
  margin: 0 0 4px;
  font-size: 0.72rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  text-transform: uppercase;
}

.control p {
  margin: 0 0 12px;
  font-size: 0.78rem;
  line-height: 1.45;
  color: var(--muted);
}

.control .slider {
  display: flex;
  align-items: center;
  gap: 12px;
}

.control input[type="range"] {
  flex: 1;
  accent-color: var(--text-soft);
}

.control output {
  min-width: 2ch;
  font-size: 0.85rem;
  font-variant-numeric: tabular-nums;
  text-align: right;
}

.sidebar-footer {
  display: grid;
  gap: 14px;
  margin-top: auto;
  font-size: 0.76rem;
  line-height: 1.5;
  color: var(--muted);
}

.sidebar-footer .stats {
  color: var(--text-soft);
}

.sidebar-footer .about {
  display: flex;
  gap: 8px;
}

.sidebar-footer .about strong {
  display: block;
  color: var(--text-soft);
  font-weight: 500;
}

.sidebar-footer a {
  color: inherit;
}

/* --- Grafo --- */

.graph-area {
  position: relative;
  min-width: 0;
  min-height: 0;
  overflow: hidden;
  background:
    radial-gradient(ellipse at center, var(--accent-soft) 0%, transparent 55%),
    var(--bg);
}

.graph-view,
.label-layer {
  position: absolute;
  inset: 0;
}

.label-layer {
  pointer-events: none;
}

.node-label {
  position: absolute;
  top: 0;
  left: 0;
  display: none;
  width: max-content;
  max-width: 180px;
  text-align: center;
  white-space: nowrap;
  transform: translate(-50%, 0);
}

.node-label.visible {
  display: block;
}

.node-label .title {
  display: block;
  font-size: 0.72rem;
  font-weight: 600;
  color: var(--text);
  text-shadow: 0 1px 3px var(--bg), 0 0 8px var(--bg);
}

.node-label .subtitle {
  display: block;
  overflow: hidden;
  font-size: 0.64rem;
  color: var(--muted);
  text-overflow: ellipsis;
  text-shadow: 0 1px 3px var(--bg);
}

.node-label.term .title {
  font-size: 0.95rem;
}

.node-label.compact .subtitle {
  display: none;
}

.node-label.dimmed {
  opacity: 0.25;
}

.graph-tools {
  position: absolute;
  bottom: 18px;
  left: 18px;
  display: flex;
  align-items: flex-end;
  gap: 14px;
}

.legend {
  margin: 0;
  padding: 12px 14px;
  list-style: none;
  background: color-mix(in srgb, var(--surface) 88%, transparent);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 0.72rem;
  color: var(--text-soft);
}

.legend li {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 2px 0;
}

.dot {
  display: inline-block;
  flex: none;
  width: 9px;
  height: 9px;
  border-radius: 50%;
  background: var(--dot, var(--muted));
  box-shadow: 0 0 6px var(--dot, transparent);
}

.zoom {
  display: grid;
  overflow: hidden;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius);
}

.zoom button {
  display: grid;
  place-items: center;
  width: 34px;
  height: 34px;
  padding: 0;
  color: var(--text-soft);
  background: transparent;
  border: 0;
}

.zoom button + button {
  border-top: 1px solid var(--border);
}

.zoom button:hover {
  color: var(--text);
  background: var(--surface-2);
}

.message {
  position: absolute;
  top: 40%;
  left: 50%;
  max-width: 30rem;
  margin: 0;
  padding: 0 16px;
  color: var(--muted);
  text-align: center;
  transform: translate(-50%, -50%);
}

.message button {
  margin-top: 12px;
  padding: 7px 16px;
  color: var(--text);
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 999px;
}

/* --- Panel del versículo --- */

.verse-panel {
  display: flex;
  flex-direction: column;
  width: 360px;
  min-height: 0;
  overflow-y: auto;
  background: var(--surface);
  border-left: 1px solid var(--border);
}

.verse-panel .close {
  align-self: flex-end;
  margin: 10px 10px 0 0;
  padding: 4px;
  color: var(--muted);
  background: none;
  border: 0;
}

.verse-panel .close:hover {
  color: var(--text);
}

.panel-header {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 0 22px;
}

.panel-header .dot {
  width: 12px;
  height: 12px;
  margin-top: 7px;
}

.panel-header h2 {
  margin: 0;
  font-size: 1.2rem;
  font-weight: 600;
}

.panel-header .group {
  margin: 2px 0 0;
  font-size: 0.78rem;
  color: var(--muted);
}

.badge {
  margin-left: auto;
  padding: 3px 10px;
  font-size: 0.7rem;
  color: var(--text-soft);
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: 999px;
}

.verse-text {
  margin: 18px 22px 0;
  padding-bottom: 20px;
  font-family: Georgia, "Times New Roman", serif;
  font-size: 0.98rem;
  line-height: 1.65;
  color: var(--text-soft);
  border-bottom: 1px solid var(--border);
}

.passage {
  margin: 16px 22px 0;
  padding: 4px 14px;
  background: var(--surface-2);
  border-radius: var(--radius);
}

.passage h3 {
  margin: 10px 0 4px;
  font-size: 0.78rem;
  color: var(--muted);
}

.passage p {
  font-family: Georgia, "Times New Roman", serif;
  font-size: 0.9rem;
  line-height: 1.6;
  color: var(--text-soft);
}

.passage sup {
  color: var(--muted);
}

.relations-title {
  display: flex;
  justify-content: space-between;
  margin: 22px 22px 6px;
  font-size: 0.7rem;
  font-weight: 600;
  letter-spacing: 0.14em;
  color: var(--muted);
  text-transform: uppercase;
}

.relations {
  margin: 0;
  padding: 0 8px 16px;
  list-style: none;
}

.relation {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 12px 14px;
  text-align: left;
  background: transparent;
  border: 0;
  border-bottom: 1px solid var(--border);
}

.relation:hover {
  background: var(--surface-2);
}

.relation .body {
  flex: 1;
  min-width: 0;
}

.relation .ref {
  display: block;
  font-size: 0.86rem;
  font-weight: 500;
  color: var(--text);
}

.relation .why {
  display: block;
  margin-top: 3px;
  font-size: 0.76rem;
  line-height: 1.4;
  color: var(--muted);
}

.relation .why.quote {
  font-style: italic;
}

.relation .chevron {
  flex: none;
  color: var(--muted);
}

.relation-extra {
  padding: 0 14px 10px 35px;
  border-bottom: 1px solid var(--border);
}

.relation-extra button {
  padding: 0;
  font-size: 0.74rem;
  color: var(--accent);
  background: none;
  border: 0;
  text-decoration: underline;
}

.relations li:has(.relation-extra) .relation {
  border-bottom: 0;
}

.skeleton {
  display: block;
  width: 70%;
  height: 0.7rem;
  margin-top: 6px;
  border-radius: 4px;
  background: linear-gradient(90deg, var(--surface-2), var(--border), var(--surface-2));
  background-size: 200% 100%;
  animation: shimmer 1.2s linear infinite;
}

@keyframes shimmer {
  from {
    background-position: 200% 0;
  }
  to {
    background-position: -200% 0;
  }
}

.muted {
  color: var(--muted);
  font-size: 0.85rem;
}

.visually-hidden {
  position: absolute;
  width: 1px;
  height: 1px;
  overflow: hidden;
  clip: rect(0 0 0 0);
  white-space: nowrap;
}

/* --- Pantallas estrechas --- */

@media (max-width: 900px) {
  .app {
    grid-template-columns: 1fr;
    grid-template-rows: 60px 1fr auto;
  }

  .brand span {
    display: none;
  }

  .brand {
    min-width: 0;
  }

  .menu-button {
    display: inline-grid;
  }

  .sidebar {
    position: fixed;
    top: 60px;
    bottom: 0;
    left: 0;
    z-index: 20;
    width: 280px;
    box-shadow: var(--shadow);
    transform: translateX(-100%);
    transition: transform 0.2s ease;
  }

  .sidebar.open {
    transform: none;
  }

  .verse-panel {
    width: auto;
    max-height: 55vh;
    border-top: 1px solid var(--border);
    border-left: 0;
  }

  .graph-tools .legend {
    display: none;
  }
}
```

- [ ] **Step 3: Barra superior y buscador**

`frontend/src/components/TopBar.tsx`:

```tsx
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
```

`frontend/src/components/SearchBar.tsx`:

```tsx
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
```

- [ ] **Step 4: Barra lateral y leyenda**

`frontend/src/components/Sidebar.tsx`:

```tsx
import { Info } from "lucide-react";
import type { SearchResponse } from "../api";

export interface Limits {
  seeds: number;
  neighbors: number;
}

export const DEFAULT_LIMITS: Limits = { seeds: 5, neighbors: 10 };

interface Props {
  limits: Limits;
  onChange: (limits: Limits) => void;
  response: SearchResponse | null;
  open: boolean;
}

export function Sidebar({ limits, onChange, response, open }: Props) {
  const seedCount = response?.nodes.filter((node) => node.is_seed).length ?? 0;

  return (
    <aside className={open ? "sidebar open" : "sidebar"} aria-label="Controles">
      <section className="control">
        <h2 id="seeds-label">Semillas</h2>
        <p>Pasajes que contienen el término o concepto de búsqueda.</p>
        <div className="slider">
          <input
            type="range"
            min={1}
            max={100}
            value={limits.seeds}
            aria-labelledby="seeds-label"
            onChange={(event) => onChange({ ...limits, seeds: Number(event.target.value) })}
          />
          <output>{limits.seeds}</output>
        </div>
      </section>

      <section className="control">
        <h2 id="neighbors-label">Vecinos</h2>
        <p>Pasajes relacionados con las semillas.</p>
        <div className="slider">
          <input
            type="range"
            min={0}
            max={20}
            value={limits.neighbors}
            aria-labelledby="neighbors-label"
            onChange={(event) => onChange({ ...limits, neighbors: Number(event.target.value) })}
          />
          <output>{limits.neighbors}</output>
        </div>
      </section>

      <footer className="sidebar-footer">
        {response && response.nodes.length > 0 && (
          <p className="stats">
            {seedCount} de {response.total_matches} coincidencias · {response.nodes.length} nodos
            {response.truncated && " · recortado a 600 nodos"}
          </p>
        )}
        <div className="about">
          <Info size={15} aria-hidden="true" />
          <p>
            <strong>La Biblia es una red de conexiones.</strong>
            Explora cómo los pasajes se relacionan entre sí.
          </p>
        </div>
        <p>
          Referencias cruzadas de{" "}
          <a href="https://www.openbible.info/labs/cross-references/" target="_blank" rel="noreferrer">
            OpenBible.info
          </a>{" "}
          (CC-BY) · Texto: Reina-Valera 1909 (dominio público)
        </p>
      </footer>
    </aside>
  );
}
```

`frontend/src/components/Legend.tsx`:

```tsx
import type { CSSProperties } from "react";
import { BOOK_GROUPS, groupVar } from "../groups";

export function dotStyle(colorVar: string): CSSProperties {
  return { "--dot": `var(${colorVar})` } as CSSProperties;
}

export function Legend() {
  return (
    <ul className="legend" aria-label="Leyenda">
      <li>
        <i className="dot" style={dotStyle("--accent")} /> Coincidencia
      </li>
      {BOOK_GROUPS.map((group) => (
        <li key={group.id}>
          <i className="dot" style={dotStyle(groupVar(group))} /> {group.name}
        </li>
      ))}
    </ul>
  );
}
```

- [ ] **Step 5: Grafo**

`frontend/src/components/GraphView.tsx`:

```tsx
import cytoscape, {
  type Core,
  type LayoutOptions,
  type NodeSingular,
  type StylesheetJson,
} from "cytoscape";
import fcose from "cytoscape-fcose";
import { Minus, Plus } from "lucide-react";
import { useEffect, useRef } from "react";
import type { SearchResponse } from "../api";
import { TERM_ID, toElements } from "../graph";
import { BOOK_GROUPS } from "../groups";
import { cssVar, type Theme } from "../theme";
import { Legend } from "./Legend";

cytoscape.use(fcose);

const ZOOM_STEP = 1.25;

/** Estilos de Cytoscape. Los colores salen de las variables CSS del tema activo. */
function buildStyle(): StylesheetJson {
  const accent = cssVar("--accent");
  const colors: [string, string][] = [
    ["seed", accent],
    ...BOOK_GROUPS.map((g): [string, string] => [g.id, cssVar(`--group-${g.id}`)]),
  ];
  return [
    {
      selector: "node",
      style: {
        width: 12,
        height: 12,
        "background-color": cssVar("--node-fill"),
        "border-width": 1.5,
        "underlay-opacity": 0.14,
        "underlay-padding": 4,
        "underlay-shape": "ellipse",
      },
    },
    ...colors.map(([name, color]) => ({
      selector: `node.c-${name}`,
      style: { "border-color": color, "underlay-color": color },
    })),
    {
      selector: "node.seed",
      style: { width: 22, height: 22, "border-width": 2, "underlay-opacity": 0.22, "underlay-padding": 7 },
    },
    {
      selector: "node.term",
      style: {
        width: 46,
        height: 46,
        "border-width": 2.5,
        "border-color": accent,
        "underlay-color": accent,
        "underlay-opacity": 0.3,
        "underlay-padding": 12,
      },
    },
    {
      selector: "edge",
      style: {
        width: "data(width)",
        "line-color": cssVar("--edge"),
        "target-arrow-color": cssVar("--edge"),
        "target-arrow-shape": "triangle",
        "arrow-scale": 0.5,
        "curve-style": "bezier",
        opacity: 0.45,
      },
    },
    {
      selector: "edge.term-edge",
      style: { width: 1, "line-color": accent, "target-arrow-shape": "none", opacity: 0.35 },
    },
    ...colors.map(([name, color]) => ({
      selector: `edge.lit.to-${name}`,
      style: { "line-color": color, "target-arrow-color": color, opacity: 0.9 },
    })),
    { selector: ".faded", style: { opacity: 0.12 } },
    { selector: "edge.faded", style: { opacity: 0.05 } },
    {
      selector: "node.selected",
      style: { "border-width": 3, "underlay-opacity": 0.4, "underlay-padding": 9 },
    },
  ];
}

const LAYOUT = {
  name: "fcose",
  animate: false,
  quality: "default",
  nodeSeparation: 70,
  idealEdgeLength: 80,
  nodeRepulsion: 7000,
  padding: 40,
  fixedNodeConstraint: [{ nodeId: TERM_ID, position: { x: 0, y: 0 } }],
} as LayoutOptions;

/** Etiquetas HTML de dos líneas, recolocadas sobre el lienzo en cada fotograma. */
function createLabelLayer(cy: Core, layer: HTMLElement): () => void {
  const labels = new Map<string, HTMLElement>();
  cy.nodes().forEach((node) => {
    const el = document.createElement("div");
    el.className = node.id() === TERM_ID ? "node-label term" : "node-label";
    const title = document.createElement("span");
    title.className = "title";
    title.textContent = node.data("label");
    const subtitle = document.createElement("span");
    subtitle.className = "subtitle";
    subtitle.textContent = node.data("snippet");
    el.append(title, subtitle);
    layer.append(el);
    labels.set(node.id(), el);
  });

  const isVisible = (node: NodeSingular) =>
    node.hasClass("term") ||
    node.hasClass("seed") ||
    node.hasClass("hover") ||
    node.hasClass("selected") ||
    node.hasClass("near");

  const place = () => {
    cy.nodes().forEach((node) => {
      const el = labels.get(node.id());
      if (!el) return;
      const visible = isVisible(node);
      el.classList.toggle("visible", visible);
      if (!visible) return;
      el.classList.toggle("dimmed", node.hasClass("faded"));
      // Los vecinos del seleccionado muestran solo la referencia, para no solaparse.
      el.classList.toggle(
        "compact",
        node.hasClass("near") &&
          !node.hasClass("selected") &&
          !node.hasClass("hover") &&
          !node.hasClass("seed") &&
          !node.hasClass("term"),
      );
      const { x, y } = node.renderedPosition();
      const offset = node.renderedOuterHeight() / 2 + 4;
      el.style.transform = `translate(calc(${x}px - 50%), ${y + offset}px)`;
    });
  };
  cy.on("render", place);
  place();
  return () => {
    cy.off("render", place);
    labels.forEach((el) => el.remove());
  };
}

interface Props {
  response: SearchResponse;
  theme: Theme;
  selectedId: number | null;
  onSelect: (id: number | null) => void;
}

export function GraphView({ response, theme, selectedId, onSelect }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const layerRef = useRef<HTMLDivElement>(null);
  const cyRef = useRef<Core | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  useEffect(() => {
    const cy = cytoscape({
      container: containerRef.current,
      elements: toElements(response),
      style: buildStyle(),
      layout: LAYOUT,
      minZoom: 0.2,
      maxZoom: 3,
    });
    const removeLabels = createLabelLayer(cy, layerRef.current!);
    cy.on("tap", "node", (event) => {
      const id = event.target.id();
      if (id !== TERM_ID) onSelectRef.current(Number(id));
    });
    cy.on("tap", (event) => {
      if (event.target === cy) onSelectRef.current(null);
    });
    cy.on("mouseover", "node", (event) => event.target.addClass("hover"));
    cy.on("mouseout", "node", (event) => event.target.removeClass("hover"));
    cyRef.current = cy;
    return () => {
      cyRef.current = null;
      removeLabels();
      cy.destroy();
    };
  }, [response]);

  // El tema cambia los colores del grafo: se recalculan desde las variables CSS.
  useEffect(() => {
    cyRef.current?.style(buildStyle());
  }, [theme]);

  useEffect(() => {
    const cy = cyRef.current;
    if (!cy) return;
    cy.elements().removeClass("faded selected near lit");
    if (selectedId === null) return;
    const node = cy.getElementById(String(selectedId));
    if (node.empty()) return;
    const neighborhood = node.closedNeighborhood();
    cy.elements().not(neighborhood).addClass("faded");
    neighborhood.nodes().addClass("near");
    node.connectedEdges().addClass("lit");
    node.addClass("selected");
    // Al abrirse el panel el lienzo se estrecha: si el nodo queda fuera, se centra.
    const timer = window.setTimeout(() => {
      cy.resize();
      const { x, y } = node.renderedPosition();
      const margin = 60;
      if (x < margin || y < margin || x > cy.width() - margin || y > cy.height() - margin) {
        cy.animate({ center: { eles: node } }, { duration: 300 });
      }
    }, 60);
    return () => window.clearTimeout(timer);
  }, [response, selectedId]);

  function zoomBy(factor: number) {
    const cy = cyRef.current;
    if (!cy) return;
    cy.zoom({
      level: cy.zoom() * factor,
      renderedPosition: { x: cy.width() / 2, y: cy.height() / 2 },
    });
  }

  return (
    <>
      <div ref={containerRef} className="graph-view" />
      <div ref={layerRef} className="label-layer" aria-hidden="true" />
      <div className="graph-tools">
        <Legend />
        <div className="zoom">
          <button type="button" onClick={() => zoomBy(ZOOM_STEP)} aria-label="Acercar">
            <Plus size={16} />
          </button>
          <button type="button" onClick={() => zoomBy(1 / ZOOM_STEP)} aria-label="Alejar">
            <Minus size={16} />
          </button>
        </div>
      </div>
    </>
  );
}
```

- [ ] **Step 6: Panel del versículo**

`frontend/src/components/VersePanel.tsx`:

```tsx
import { ChevronRight, X } from "lucide-react";
import type { GraphNode, Passage } from "../api";
import type { Connection } from "../graph";
import { groupOf, groupVar } from "../groups";
import { snippet } from "../text";
import { dotStyle } from "./Legend";

export type PassageState =
  | { status: "loading"; label: string }
  | { status: "error"; label: string }
  | { status: "done"; label: string; passage: Passage };

/** Frases de relación del versículo abierto: por ID del otro versículo. */
export type ExplanationsState =
  | { status: "loading" }
  | { status: "done"; texts: Map<number, string | null> };

interface Props {
  node: GraphNode;
  nodes: Map<number, GraphNode>;
  connections: Connection[];
  explanations: ExplanationsState;
  passage: PassageState | null;
  onSelectNode: (id: number) => void;
  onOpenPassage: (connection: Connection) => void;
  onClose: () => void;
}

function colorVar(node: GraphNode): string {
  return node.is_seed ? "--accent" : groupVar(groupOf(node.id));
}

function Why({ connection, other, explanations }: {
  connection: Connection;
  other: GraphNode | undefined;
  explanations: ExplanationsState;
}) {
  if (explanations.status === "loading") {
    return (
      <span className="why">
        <span className="visually-hidden">Generando…</span>
        <span className="skeleton" aria-hidden="true" />
      </span>
    );
  }
  const text = explanations.texts.get(connection.nodeId);
  if (text) return <span className="why">{text}</span>;
  return <span className="why quote">«{snippet(other?.text ?? "", 70)}»</span>;
}

export function VersePanel({
  node,
  nodes,
  connections,
  explanations,
  passage,
  onSelectNode,
  onOpenPassage,
  onClose,
}: Props) {
  return (
    <aside className="verse-panel" aria-label={`Versículo ${node.ref}`}>
      <button type="button" className="close" onClick={onClose} aria-label="Cerrar">
        <X size={18} />
      </button>
      <header className="panel-header">
        <i className="dot" style={dotStyle(colorVar(node))} />
        <div>
          <h2>{node.ref}</h2>
          <p className="group">{groupOf(node.id).name}</p>
        </div>
        {node.is_seed && <span className="badge">Semilla</span>}
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

      <h3 className="relations-title">
        <span>Relaciones</span>
        <span>{connections.length}</span>
      </h3>
      {connections.length === 0 && <p className="muted relations-title">Sin relaciones en este grafo.</p>}
      <ul className="relations">
        {connections.map((connection) => {
          const other = nodes.get(connection.nodeId);
          const [from, to] =
            connection.direction === "out" ? [node.label, connection.label] : [connection.label, node.label];
          return (
            <li key={connection.key}>
              <button
                type="button"
                className="relation"
                onClick={() => onSelectNode(connection.nodeId)}
                title={`${from} remite a ${to} · ${connection.weight} votos en OpenBible`}
              >
                <i className="dot" style={dotStyle(other ? colorVar(other) : "--muted")} />
                <span className="body">
                  <span className="ref">{connection.label}</span>
                  <Why connection={connection} other={other} explanations={explanations} />
                </span>
                <ChevronRight size={16} className="chevron" aria-hidden="true" />
              </button>
              {connection.rangeEndId !== null && (
                <div className="relation-extra">
                  <button type="button" onClick={() => onOpenPassage(connection)}>
                    leer pasaje
                  </button>
                </div>
              )}
            </li>
          );
        })}
      </ul>
    </aside>
  );
}
```

- [ ] **Step 7: Aplicación**

`frontend/src/App.tsx`:

```tsx
import { useEffect, useMemo, useRef, useState } from "react";
import { fetchExplanations, fetchPassage, searchGraph, type SearchResponse } from "./api";
import { GraphView } from "./components/GraphView";
import { MIN_QUERY_LENGTH } from "./components/SearchBar";
import { DEFAULT_LIMITS, type Limits, Sidebar } from "./components/Sidebar";
import { TopBar } from "./components/TopBar";
import { type ExplanationsState, type PassageState, VersePanel } from "./components/VersePanel";
import { type Connection, explanationTargets, relationsOf } from "./graph";
import { applyTheme, readTheme, type Theme } from "./theme";

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

function browserStorage(): Storage | undefined {
  try {
    return window.localStorage;
  } catch {
    return undefined;
  }
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
  const [explanations, setExplanations] = useState<ExplanationsState>({ status: "loading" });
  const [theme, setTheme] = useState<Theme>(() => {
    const initial = readTheme(browserStorage());
    applyTheme(browserStorage(), initial);
    return initial;
  });
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const passageRequest = useRef<AbortController | null>(null);

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if (event.key === "Escape") setSelectedId(null);
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

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

  const response = search.status === "done" ? search.response : null;
  const nodes = useMemo(() => new Map((response?.nodes ?? []).map((n) => [n.id, n])), [response]);
  const selectedNode = selectedId === null ? null : (nodes.get(selectedId) ?? null);
  const connections = useMemo(
    () => (response && selectedId !== null ? relationsOf(selectedId, response) : []),
    [response, selectedId],
  );
  const targets = useMemo(() => explanationTargets(connections), [connections]);

  // Frases de relación: se piden al abrir un versículo. La primera vez las genera Ollama.
  useEffect(() => {
    if (selectedId === null || targets.length === 0) return;
    const controller = new AbortController();
    setExplanations({ status: "loading" });
    fetchExplanations(selectedId, targets, controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        setExplanations({
          status: "done",
          texts: new Map(result.explanations.map((e) => [e.other, e.text])),
        });
      })
      .catch(() => {
        if (!controller.signal.aborted) setExplanations({ status: "done", texts: new Map() });
      });
    return () => controller.abort();
  }, [selectedId, targets]);

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

  return (
    <div className="app">
      <TopBar
        query={query}
        onSearch={runSearch}
        theme={theme}
        onToggleTheme={() => {
          const next = theme === "dark" ? "light" : "dark";
          applyTheme(browserStorage(), next);
          setTheme(next);
        }}
        onToggleSidebar={() => setSidebarOpen((open) => !open)}
      />
      <Sidebar limits={limits} onChange={setLimits} response={response} open={sidebarOpen} />

      <main className="graph-area">
        {search.status === "idle" && (
          <p className="message">
            Escribe un término o concepto para ver los pasajes que lo contienen y cómo se
            conectan con el resto de la Biblia.
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
            No se pudo completar la búsqueda.
            <br />
            <button type="button" onClick={() => setAttempt((n) => n + 1)}>
              Reintentar
            </button>
          </p>
        )}
        {response && response.nodes.length === 0 && (
          <p className="message">No hay versículos que contengan «{response.query}».</p>
        )}
        {response && response.nodes.length > 0 && (
          <GraphView
            response={response}
            theme={theme}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
        )}
      </main>

      {selectedNode && (
        <VersePanel
          node={selectedNode}
          nodes={nodes}
          connections={connections}
          explanations={targets.length === 0 ? { status: "done", texts: new Map() } : explanations}
          passage={passage}
          onSelectNode={setSelectedId}
          onOpenPassage={openPassage}
          onClose={() => setSelectedId(null)}
        />
      )}
    </div>
  );
}
```

- [ ] **Step 8: Borrar el componente antiguo**

Run: `git rm -q frontend/src/components/LimitControls.tsx`

- [ ] **Step 9: Tipos, tests y build**

Run: `docker compose exec -T -e NO_COLOR=1 frontend npx vitest run 2>&1 | grep "Tests " && docker compose exec -T frontend npm run build 2>&1 | grep -E "built|error"`
Expected: `Tests  41 passed (41)` y `✓ built`, sin errores de TypeScript.

- [ ] **Step 10: Comprobación en navegador**

Guarda este guion **fuera del repo**, como `ui-check.mjs` en la carpeta `pw` del directorio temporal de la sesión (la ruta está en el comando de abajo). Usa el Chrome instalado, sin descargar navegadores:

```js
// Comprobación desechable de la interfaz con Chrome sin ventana. No forma parte del repo.
// Uso: BASE=http://localhost:5180 OUT=<carpeta> node ui-check.mjs
import { chromium } from "playwright";

const BASE = process.env.BASE ?? "http://localhost:5173";
const OUT = process.env.OUT ?? ".";
const results = [];
const check = (name, ok, detail = "") => {
  results.push(ok);
  console.log(`${ok ? "OK  " : "FAIL"} ${name}${detail ? " — " + detail : ""}`);
};

const browser = await chromium.launch({ channel: "chrome" });
const page = await browser.newPage({ viewport: { width: 1360, height: 820 } });
const errors = [];
page.on("pageerror", (e) => errors.push(String(e)));
page.on("console", (m) => m.type() === "error" && errors.push(m.text()));

const cyInfo = () =>
  page.evaluate(() => {
    const cy = document.querySelector(".graph-view")?._cyreg?.cy;
    if (!cy) return null;
    return {
      nodes: cy.nodes().length,
      seeds: cy.nodes(".seed").length,
      term: cy.nodes(".term").map((n) => n.data("label")),
      termEdges: cy.edges(".term-edge").length,
      faded: cy.elements(".faded").length,
      selected: cy.nodes(".selected").map((n) => n.id()),
      fill: cy.nodes(".seed")[0]?.style("background-color"),
    };
  });
const point = (selector, index = 0) =>
  page.evaluate(
    ([selector, index]) => {
      const el = document.querySelector(".graph-view");
      const node = el._cyreg.cy.nodes(selector)[index];
      const p = node.renderedPosition();
      const r = el.getBoundingClientRect();
      return { x: r.x + p.x, y: r.y + p.y, id: node.id() };
    },
    [selector, index],
  );
const waitGraph = () => page.waitForFunction(() => document.querySelector(".graph-view")?._cyreg?.cy);

await page.goto(BASE);
check("mensaje inicial", (await page.locator(".message").innerText()).includes("Escribe un término"));
check("título de la página", (await page.title()) === "Biblia en red");

await page.fill('input[type="search"]', "amor");
await page.press('input[type="search"]', "Enter");
await waitGraph();
await page.waitForTimeout(800);
let info = await cyInfo();
check("nodo central con el término", info.term[0] === "Amor" && info.termEdges === info.seeds, JSON.stringify(info));
check("5 semillas por defecto", info.seeds === 5);
check("URL con ?q=amor", page.url().endsWith("?q=amor"));
const labels = await page.locator(".node-label.visible").count();
check("etiquetas del término y las semillas", labels === 6, `${labels} visibles`);
const stats = await page.locator(".sidebar .stats").innerText();
check("recuento en la barra lateral", /^5 de \d+ coincidencias · \d+ nodos$/.test(stats), stats);
const footer = await page.locator(".sidebar-footer").innerText();
check("atribución", footer.includes("OpenBible.info") && footer.includes("CC-BY"));
check("leyenda con 7 entradas", (await page.locator(".legend li").count()) === 7);
await page.screenshot({ path: `${OUT}/ui-1-grafo.png` });

// El nodo central no abre panel
const term = await point(".term");
await page.mouse.click(term.x, term.y);
await page.waitForTimeout(200);
check("el término no abre panel", (await page.locator(".verse-panel").count()) === 0);

// Selección de una semilla y frases
const seed = await point(".seed", 0);
await page.mouse.click(seed.x, seed.y);
await page.waitForSelector(".verse-panel");
check("etiqueta Semilla", (await page.locator(".verse-panel .badge").innerText()) === "Semilla");
const relCount = Number(await page.locator(".relations-title span").nth(1).innerText());
const rows = await page.locator(".relation").count();
check("una fila por versículo relacionado", rows === relCount && rows > 0, `${rows} filas`);
const refs = await page.locator(".relation .ref").allInnerTexts();
check("sin versículos repetidos", new Set(refs).size === refs.length);
await page.waitForFunction(() => !document.querySelector(".skeleton"), null, { timeout: 90000 });
const whys = await page.locator(".relation .why").allInnerTexts();
const phrases = whys.filter((t) => !t.startsWith("«"));
check("frases generadas", phrases.length > 0, `${phrases.length}/${whys.length} con frase`);
check("sin «Ambos» al principio", phrases.every((t) => !/^ambos/i.test(t)));
info = await cyInfo();
check("vecindario resaltado", info.faded > 0 && info.selected[0] === seed.id);
await page.screenshot({ path: `${OUT}/ui-2-frases.png` });

// Navegar por la lista
const before = await page.locator(".verse-panel h2").innerText();
await page.locator(".relation").first().click();
await page.waitForTimeout(300);
check("la fila navega a su versículo", (await page.locator(".verse-panel h2").innerText()) !== before);

// Escape cierra
await page.keyboard.press("Escape");
await page.waitForTimeout(200);
check("Escape cierra el panel", (await page.locator(".verse-panel").count()) === 0);

// Tema claro
await page.click('button[aria-label="Cambiar a tema claro"]');
await page.waitForTimeout(300);
info = await cyInfo();
const themeAttr = await page.evaluate(() => document.documentElement.dataset.theme);
check("tema claro aplicado al grafo", themeAttr === "light" && info.fill === "rgb(255,255,255)", info.fill);
await page.reload();
await waitGraph();
check("el tema se recuerda", (await page.evaluate(() => document.documentElement.dataset.theme)) === "light");
await page.screenshot({ path: `${OUT}/ui-3-claro.png` });
await page.click('button[aria-label="Cambiar a tema oscuro"]');

// Zoom
const z0 = await page.evaluate(() => document.querySelector(".graph-view")._cyreg.cy.zoom());
await page.click('button[aria-label="Acercar"]');
const z1 = await page.evaluate(() => document.querySelector(".graph-view")._cyreg.cy.zoom());
check("botón acercar", Math.abs(z1 / z0 - 1.25) < 0.01, `${z0.toFixed(2)} → ${z1.toFixed(2)}`);

// Vista estrecha
await page.setViewportSize({ width: 420, height: 860 });
await page.waitForTimeout(300);
const sidebarHidden = await page.evaluate(() => {
  const r = document.querySelector(".sidebar").getBoundingClientRect();
  return r.right <= 0;
});
await page.click('button[aria-label="Mostrar controles"]');
await page.waitForTimeout(400);
const sidebarShown = await page.evaluate(() => document.querySelector(".sidebar").getBoundingClientRect().left >= 0);
check("barra lateral plegable en móvil", sidebarHidden && sidebarShown);
await page.screenshot({ path: `${OUT}/ui-4-movil.png` });

check("sin errores de consola", errors.length === 0, errors.slice(0, 3).join(" | "));
await browser.close();
console.log(`${results.filter(Boolean).length}/${results.length} comprobaciones correctas`);
process.exit(results.every(Boolean) ? 0 : 1);
```

Run (PowerShell):

```powershell
$pw = "C:\Users\iratx\AppData\Local\Temp\claude\c--Users-iratx-Documents-PROYECTOS-bible-graph\d5e0210a-9421-4f31-a1c3-4d832ee4cc4c\scratchpad\pw"
New-Item -ItemType Directory -Force $pw | Out-Null; Set-Location $pw
if (-not (Test-Path node_modules\playwright)) { npm init -y | Out-Null; $env:PLAYWRIGHT_SKIP_BROWSER_DOWNLOAD = "1"; npm install --silent playwright | Out-Null }
Set-Location "C:\Users\iratx\Documents\PROYECTOS\bible-graph"; docker compose exec -T db psql -U bible -d bible -c "TRUNCATE relation_explanations" | Out-Null
Set-Location $pw; $env:BASE = "http://localhost:5180"; $env:OUT = $pw; node ui-check.mjs
```

Expected: `23/23 comprobaciones correctas`. Revisa además las cuatro capturas (`ui-1-grafo.png` … `ui-4-movil.png`): el grafo debe parecerse a la maqueta, con el término en el centro, anillos de colores, etiquetas de dos líneas legibles y el panel con una frase por relación.

- [ ] **Step 11: Comprobar la recarga en caliente del frontend**

Con la app abierta en <http://localhost:5180>, cambia temporalmente el texto de `.brand span` en `TopBar.tsx` y guarda. La barra superior debe actualizarse en unos segundos sin recargar la página. Deshaz el cambio.

- [ ] **Step 12: Commit**

```bash
git add frontend
git commit -m "Redesign the interface after the reference mockup

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Documentación y verificación final

**Files:**
- Modify: `README.md`, `docs/deploy.md` (se reemplazan enteros)

**Interfaces:**
- Consumes: todo lo anterior.
- Produces: documentación de Ollama, de los puertos configurables, de la pregeneración y de cómo llevar frases a Neon.

- [ ] **Step 1: Reemplazar `README.md`**

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

Hace falta Docker. Para las frases que explican cada relación, también
[Ollama](https://ollama.com) en la misma máquina con el modelo `gemma4:e4b`
(`ollama pull gemma4:e4b`); sin Ollama la app funciona igual y muestra el comienzo del
versículo relacionado en lugar de la frase.

```bash
docker compose up -d --build        # BD, API y frontend
docker compose run --rm ingest      # carga los datos (la primera vez y tras cambios de esquema)
```

Abre <http://localhost:5173> y busca "gracia".

| Servicio | URL |
|---|---|
| Frontend | <http://localhost:5173> |
| API | <http://localhost:8000> (documentación en `/docs`) |
| Postgres | `localhost:5432`, usuario, clave y base de datos `bible` |

Si alguno de esos puertos está ocupado, crea un fichero `.env` junto a
`docker-compose.yml` con otros valores (`DB_PORT`, `API_PORT`, `FRONTEND_PORT`; ver
[.env.example](.env.example)) y abre el frontend en el puerto que hayas elegido.

## Cómo se busca

- Se ignoran mayúsculas y acentos: "redencion" encuentra "redención".
- Se encuentran otras formas de la palabra: "perdón" encuentra "perdonó" y
  "perdonados".
- Varias palabras deben aparecer todas: `gracia fe`.
- Entre comillas se busca la frase exacta: `"vida eterna"`.
- `OR` busca cualquiera de las dos: `gracia OR misericordia`.
- Las palabras muy comunes ("de", "la", "fue") no se buscan.

Los versículos que contienen el término son las semillas y rodean al término, en el
centro. El grafo añade, para cada una, sus versículos más conectados. Los deslizadores
**Semillas** y **Vecinos** controlan cuántos. Los colores indican el tipo de libro.

## Frases de relación

Al abrir un versículo, el panel explica en una frase cada una de sus relaciones. Las
frases las escribe un modelo local de Ollama la primera vez (unos 5 segundos, o unos 15
si el modelo no estaba cargado) y quedan guardadas en la base de datos.

Para generarlas por adelantado, de las referencias más votadas a las menos (unas 11.000
por hora con una GPU de portátil):

```bash
docker compose run --rm ingest python -m ingest.explain --limit 5000
```

Se puede interrumpir con Ctrl+C y volver a lanzar: continúa donde lo dejó.

## Tests

```bash
docker compose run --rm api pytest          # backend (usa la BD aparte bible_test)
docker compose exec frontend npm test       # frontend
docker compose exec frontend npm run build  # tipos y build de producción
```

## Estructura

```
backend/app/      API: búsqueda, expansión del grafo, pasajes y frases de relación
backend/ingest/   Carga de los datos (python -m ingest) y frases en lote (ingest.explain)
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

- [ ] **Step 2: Reemplazar `docs/deploy.md`**

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

La ingesta se puede repetir las veces que haga falta: reemplaza los versículos y las
referencias, y conserva las frases de relación ya generadas. Vuelve a ejecutarla también
cuando una versión nueva añada tablas al esquema.

En PowerShell (Windows) la variable se define antes del comando:

```powershell
$env:INGEST_DATABASE_URL = "<cadena directa de Neon>"; docker compose run --rm ingest
```

### Frases de relación en la web publicada

Render no puede ejecutar Ollama, así que la web publicada solo muestra las frases que
ya estén en la base de datos; en las demás relaciones enseña el comienzo del versículo.
Para llevar frases a Neon, genéralas desde tu máquina con Ollama en marcha:

```bash
INGEST_DATABASE_URL="<cadena directa de Neon>" docker compose run --rm ingest python -m ingest.explain --limit 5000
```

Las más votadas van primero. Se puede interrumpir y reanudar.

## 3. API en Render

1. En <https://dashboard.render.com>, **New → Blueprint** y selecciona este repo.
   Render lee `render.yaml` y propone el servicio `bible-graph-api`.
2. Rellena las dos variables que pide:
   - `DATABASE_URL`: la cadena **con pooling** de Neon.
   - `ALLOWED_ORIGINS`: de momento `http://localhost:5173`. Se cambia en el paso 5.

   No definas `OLLAMA_URL` en Render: sin ella la API solo lee las frases guardadas.
3. Cuando termine el despliegue, copia la URL del servicio
   (`https://bible-graph-api-xxxx.onrender.com`) y comprueba:

```bash
curl https://bible-graph-api-xxxx.onrender.com/health      # {"status":"ok"}
curl https://bible-graph-api-xxxx.onrender.com/health/db   # {"status":"ok"}
```

Si `/health/db` devuelve 503, el campo `detail` dice por qué: "Base de datos no
disponible" (la `DATABASE_URL` está mal) o "La base de datos no tiene los datos
cargados" (falta la ingesta del paso 2, o apunta a otra base de datos).

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
| `/health/db` devuelve 503 con "Base de datos no disponible" | `DATABASE_URL` incorrecta en Render |
| `/health/db` devuelve 503 con "La base de datos no tiene los datos cargados" | La ingesta no se ejecutó contra esta BD |
| La ingesta falla con un error de `unaccent` o de permisos | Se usó la cadena con pooling; usa la directa |
````

- [ ] **Step 3: Verificación final**

Run:

```bash
docker compose run --rm api pytest -q | tail -1
docker compose exec -T -e NO_COLOR=1 frontend npx vitest run 2>&1 | grep "Tests "
docker compose exec -T frontend npm run build 2>&1 | grep -E "built|error"
git ls-files --eol | grep -c "w/crlf"
git status --short
```

Expected: `162 passed`, `Tests  41 passed (41)`, `✓ built`, `0`, y solo `README.md` y `docs/deploy.md` como modificados.

- [ ] **Step 4: Commit**

```bash
git add README.md docs/deploy.md
git commit -m "Document Ollama phrases, configurable ports and batch generation

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

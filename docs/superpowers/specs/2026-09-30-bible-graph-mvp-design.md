# bible-graph MVP: diseño

Fecha: 2026-09-30

## 1. Objetivo

Una web app personal de consulta. El usuario escribe un término o concepto bíblico
("gracia", "perdón") y ve un grafo interactivo de versículos: los que contienen el
término (semillas) y los que se conectan con ellos mediante referencias cruzadas
tradicionales, ponderadas por votos.

### Criterio de éxito

- Buscar "gracia" muestra un grafo legible de semillas y vecinos directos.
- Hacer click en un nodo muestra el texto del versículo.
- Todo arranca en local con `docker compose up` más una ingesta.
- El repo queda listo para desplegar gratis en Render (API), Neon (BD) y
  Cloudflare Pages (frontend).

### Dentro del alcance

- Ingesta de RV1909 y de las referencias cruzadas de OpenBible en Postgres.
- Búsqueda léxica en español con expansión del grafo.
- Frontend con búsqueda, grafo, panel de versículo y dos sliders (semillas y vecinos).
- Dockerfiles, `docker-compose.yml`, `render.yaml` y guía de despliegue.

### Fuera del alcance (fase 2)

- Embeddings y búsqueda semántica (pgvector).
- Filtros por testamento, libro o peso mínimo en la interfaz.
- Agrupación de nodos por libro o tema.
- Otras traducciones, Nave's, Treasury of Scripture Knowledge, Strong's.
- Cuentas de usuario y búsquedas guardadas.
- Integración continua.

## 2. Decisiones tomadas

| Decisión | Elección |
|---|---|
| Idioma y texto | Español, Reina-Valera 1909. El esquema admite más traducciones |
| Tamaño del grafo | Límites en el servidor (semillas y vecinos por nodo) con dos sliders en la interfaz |
| Rangos en las referencias | La arista apunta al primer versículo; el final del rango se guarda en la arista |
| Búsqueda léxica | Full-text search de Postgres con stemming español y `unaccent` |
| Acceso a datos | SQL a mano con psycopg 3, sin ORM ni Alembic |
| Sentido de la expansión | Ambos sentidos de cada arista |
| Aristas devueltas | Todas las que hay entre los nodos mostrados |

## 3. Fuentes de datos

| Fuente | URL | Licencia | Contenido |
|---|---|---|---|
| RV1909 (eBible.org) | `https://ebible.org/Scriptures/spaRV1909_vpl.zip` | Dominio público | 31.084 versículos con texto, 66 libros |
| OpenBible cross-references | `https://a.openbible.info/data/cross-references.zip` | CC-BY | 344.799 referencias |

Hechos comprobados sobre los ficheros (2026-09-30):

- `spaRV1909_vpl.txt` está en UTF-8 con BOM. Cada línea es `COD cap:vers texto`, por
  ejemplo `GEN 1:1 EN el principio crió Dios...`.
- Los códigos de libro de eBible no son USFM estándar. En orden canónico son: `GEN EXO
  LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SOL ISA
  JER LAM EZE DAN HOS JOE AMO OBA JON MIC NAH HAB ZEP HAG ZEC MAL MAT MAR LUK JOH ACT
  ROM 1CO 2CO GAL EPH PHI COL 1TH 2TH 1TI 2TI TIT PHM HEB JAM 1PE 2PE 1JO 2JO 3JO JUD
  REV`.
- El texto conserva ortografía antigua ("crió", "fué").
- `cross_references.txt` es un TSV con cabecera y columnas `From Verse`, `To Verse`,
  `Votes`. Las referencias usan códigos OSIS: `Gen.1.1`, `1John.1.5`.
- 88.150 referencias (26%) tienen un rango como destino: `Prov.8.22-Prov.8.30`.
  18 de ellas cruzan de un libro a otro.
- 3.534 referencias tienen votos ≤ 0.
- No hay pares (origen, primer versículo de destino) duplicados.
- El fichero de RV1909 tiene 31.102 líneas, pero 18 no tienen texto: `NUM 12:16`,
  `NUM 29:40`, `1SA 23:29`, `2SA 20:26`, `2CH 33:25`, `JOB 35:16`, `JOB 38:39-41`,
  `JOB 40:20-24`, `HOS 11:12`, `JON 1:17`, `ACT 19:41` y `2CO 13:14`. Son los puntos
  donde la numeración de RV1909 difiere de la de la KJV, que es la que usa OpenBible.
  Esas 18 referencias no se cargan como versículos.
- 257 referencias de OpenBible tocan un versículo que no existe en RV1909: 256 por
  las 18 líneas sin texto y una por `3John.1.15`. Se descartan. Quedan 344.542
  aristas.

OpenBible exige atribución. El pie de página de la web la muestra.

### Limitación conocida: numeración de versículos

En los capítulos afectados por esas 18 diferencias (por ejemplo Números 13, donde el
13:1 de RV1909 es el 12:16 de la KJV), las referencias cruzadas pueden apuntar al
versículo contiguo. Son una docena de capítulos de 1.189. Corregirlo exige una tabla
de equivalencias entre numeraciones y queda fuera del MVP.

## 4. Estructura del repo

```
bible-graph/
├── docker-compose.yml
├── .env.example
├── render.yaml
├── backend/
│   ├── Dockerfile
│   ├── requirements.txt         # dependencias de producción
│   ├── requirements-dev.txt     # añade pytest y el cliente de tests
│   ├── pyproject.toml           # configuración de pytest
│   ├── app/
│   │   ├── main.py              # FastAPI, CORS, /health
│   │   ├── config.py            # settings desde variables de entorno
│   │   ├── db.py                # pool de psycopg 3
│   │   ├── refs.py              # formato de referencias ("Tit 3:5-7")
│   │   ├── schemas.py           # modelos de respuesta
│   │   ├── search.py            # SQL de búsqueda y expansión del grafo
│   │   └── routes.py            # /api/search, /api/verses/{id}
│   ├── ingest/
│   │   ├── __main__.py          # CLI: python -m ingest
│   │   ├── books.py             # tabla fija de los 66 libros
│   │   ├── download.py          # descarga con caché y lectura de zips
│   │   ├── bible_text.py        # parseo de RV1909
│   │   ├── cross_refs.py        # parseo de OpenBible
│   │   └── load.py              # aplica schema.sql y hace COPY
│   ├── sql/schema.sql
│   └── tests/
├── frontend/
│   ├── Dockerfile
│   ├── package.json
│   ├── vite.config.ts
│   └── src/
│       ├── App.tsx
│       ├── api.ts
│       ├── graph.ts             # respuesta de la API → elementos de Cytoscape
│       └── components/          # SearchBar, LimitControls, GraphView, VersePanel
└── docs/
    └── deploy.md
```

La ingesta vive dentro de `backend/` para compartir imagen Docker y dependencias con
la API.

## 5. Esquema de la base de datos

```sql
CREATE EXTENSION IF NOT EXISTS unaccent;

-- Dentro de un bloque DO que comprueba pg_ts_config, para que sea idempotente.
CREATE TEXT SEARCH CONFIGURATION es_unaccent (COPY = spanish);
ALTER TEXT SEARCH CONFIGURATION es_unaccent
  ALTER MAPPING FOR hword, hword_part, word WITH unaccent, spanish_stem;

CREATE TABLE IF NOT EXISTS books (
  id        smallint PRIMARY KEY,          -- 1..66, orden canónico
  osis      text UNIQUE NOT NULL,          -- 'Gen', '1John' (OpenBible)
  name_es   text NOT NULL,                 -- 'Génesis'
  abbr_es   text NOT NULL,                 -- 'Gn'
  testament char(2) NOT NULL CHECK (testament IN ('AT','NT'))
);

CREATE TABLE IF NOT EXISTS verses (
  id       integer PRIMARY KEY,            -- BBCCCVVV: Juan 3:16 = 43003016
  book_id  smallint NOT NULL REFERENCES books,
  chapter  smallint NOT NULL,
  verse    smallint NOT NULL,
  UNIQUE (book_id, chapter, verse)
);

CREATE TABLE IF NOT EXISTS verse_texts (
  verse_id    integer NOT NULL REFERENCES verses,
  translation text    NOT NULL,            -- 'RV1909'
  text        text    NOT NULL,
  tsv         tsvector GENERATED ALWAYS AS (to_tsvector('es_unaccent', text)) STORED,
  PRIMARY KEY (translation, verse_id)
);
CREATE INDEX IF NOT EXISTS verse_texts_tsv_idx ON verse_texts USING gin (tsv);

CREATE TABLE IF NOT EXISTS edges (
  from_verse_id   integer NOT NULL REFERENCES verses,
  to_verse_id     integer NOT NULL REFERENCES verses,  -- primer versículo del rango
  to_end_verse_id integer REFERENCES verses,           -- NULL si no es rango
  weight          integer NOT NULL,                    -- votos de OpenBible
  kind            text    NOT NULL DEFAULT 'openbible',
  PRIMARY KEY (kind, from_verse_id, to_verse_id)
);
CREATE INDEX IF NOT EXISTS edges_from_idx ON edges (from_verse_id, weight DESC);
CREATE INDEX IF NOT EXISTS edges_to_idx   ON edges (to_verse_id,   weight DESC);
```

Notas:

- El ID `BBCCCVVV` (libro × 1.000.000 + capítulo × 1.000 + versículo) ordena de forma
  canónica y permite resolver rangos con `BETWEEN`.
- `verses` es la identidad del versículo y `verse_texts` guarda el texto de cada
  traducción. El código de libro de eBible no se guarda en la BD; solo lo usa la
  ingesta.
- La columna `tsv` usa el diccionario español. Una traducción en otro idioma
  necesitará su propia configuración de búsqueda; queda para la fase 2.
- Se cargan todas las aristas, incluidas las de votos ≤ 0. El filtro por peso se
  aplica en la consulta.
- `to_end_verse_id` es NULL cuando el destino es un solo versículo. Si el versículo
  final de un rango no existe en RV1909, se guarda NULL y la arista se conserva.
- La API usa la traducción `RV1909` como constante. No hay parámetro de traducción en
  el MVP.

## 6. Ingesta

`python -m ingest [--force-download]`, con `DATABASE_URL` en el entorno.

1. Aplica `sql/schema.sql`, que es idempotente.
2. Descarga los dos zips a un directorio de caché (`INGEST_CACHE_DIR`, por defecto
   `data/`; en Docker, un volumen en `/cache`). Reutiliza los ya descargados salvo
   con `--force-download`.
3. Parsea:
   - **RV1909**: lee `spaRV1909_vpl.txt` con `utf-8-sig`. Cada línea se divide en
     código de libro, `cap:vers` y texto. El código se traduce con `books.py`. Las
     líneas sin texto se omiten.
   - **OpenBible**: salta la cabecera, convierte cada referencia OSIS a `BBCCCVVV` y,
     si el destino es un rango, separa primer versículo y versículo final.
4. Carga en una sola transacción: `TRUNCATE` de las cuatro tablas y `COPY` de cada
   una. Si algo falla, la BD queda como estaba.
5. Descarta las aristas cuyo origen o primer versículo de destino no exista en
   `verses`, y las lista en el resumen.
6. Imprime un resumen: libros, versículos, aristas cargadas y aristas descartadas.
7. Antes de tocar la BD, termina con código de error y sin cargar nada si los libros
   con texto no son 66, si los versículos no son 31.084 o si las aristas cargables
   son menos de 340.000.
8. Antes de cargar imprime el servidor y la base de datos de destino, sin
   credenciales.

En compose, la BD de destino de la ingesta se cambia con `INGEST_DATABASE_URL`, no
con `DATABASE_URL`: así una `DATABASE_URL` que ya exista en la shell por otro
proyecto no redirige la carga por accidente.

`books.py` contiene, para cada uno de los 66 libros: número, código OSIS, código de
eBible, nombre en español, abreviatura en español y testamento.

## 7. API

### Endpoints

| Método | Ruta | Descripción |
|---|---|---|
| `GET` | `/api/search` | Busca semillas y devuelve el grafo expandido |
| `GET` | `/api/verses/{id}?end={id}` | Texto de un versículo o de un rango |
| `GET` | `/health` | 200 sin tocar la BD. Healthcheck de Render |
| `GET` | `/health/db` | Ejecuta `SELECT 1`. 200 si va bien, 503 si falla |

`/health` no toca la BD a propósito: Render lo llama cada pocos segundos, y una
consulta en cada llamada impediría que Neon se suspendiera.

### `GET /api/search`

| Parámetro | Por defecto | Rango | Significado |
|---|---|---|---|
| `q` | obligatorio | 2–100 caracteres | Término o frase |
| `seeds` | 25 | 1–100 | Número máximo de semillas |
| `neighbors` | 8 | 0–20 | Vecinos por nodo en cada salto |
| `min_weight` | 1 | ≥ 0 | Votos mínimos de una arista |
| `hops` | 1 | 1–2 | Saltos de expansión |

Respuesta:

```json
{
  "query": "gracia",
  "total_matches": 276,
  "truncated": false,
  "nodes": [
    {
      "id": 45003024,
      "ref": "Romanos 3:24",
      "label": "Ro 3:24",
      "book": "Romanos",
      "testament": "NT",
      "text": "Siendo justificados gratuitamente por su gracia...",
      "is_seed": true,
      "hop": 0
    }
  ],
  "edges": [
    {
      "source": 45003024,
      "target": 49002008,
      "weight": 41,
      "target_end_id": null,
      "target_label": "Ef 2:8"
    }
  ]
}
```

- `total_matches` es el número total de versículos que coinciden, antes de aplicar
  `seeds`.
- En una arista con rango, `target_end_id` es el ID del versículo final y
  `target_label` incluye el rango ("Tit 3:5-7").

### Construcción del grafo

1. **Semillas.** `websearch_to_tsquery('es_unaccent', q)` contra `verse_texts.tsv`
   con `translation = 'RV1909'`. Orden: `ts_rank_cd` descendente; a igualdad, suma
   descendente de los votos positivos de las aristas que llegan al versículo; a
   igualdad, `verse_id` ascendente. Se toman las primeras `seeds`.

   El desempate por votos es necesario: `ts_rank_cd` da la misma puntuación a todos
   los versículos que contienen la palabra una vez, y sin él "gracia" devolvería
   siempre los primeros versículos del Génesis.
2. **Expansión.** CTE recursiva desde las semillas. Para cada nodo de la frontera, un
   `LATERAL` toma sus `neighbors` vecinos de más peso con `weight >= min_weight`,
   mirando tanto `from_verse_id` como `to_verse_id`. Un vecino unido por aristas en
   los dos sentidos cuenta una sola vez, con el mayor de los dos pesos. Se detiene en `hops`. El salto
   de un nodo es el mínimo con el que se alcanza.
3. **Recorte.** Si hay más de 600 nodos, se conservan los 600 de menor salto (a
   igualdad de salto, por `verse_id`) y `truncated` es `true`.
4. **Aristas.** Todas las aristas con `weight >= min_weight` cuyos dos extremos están
   entre los nodos devueltos.

```sql
WITH RECURSIVE seeds AS (...),
walk(id, hop) AS (
  SELECT id, 0 FROM seeds
  UNION
  SELECT n.id, w.hop + 1
  FROM walk w
  CROSS JOIN LATERAL (
    SELECT e.other AS id FROM (
      SELECT to_verse_id   AS other, weight FROM edges WHERE from_verse_id = w.id
      UNION ALL
      SELECT from_verse_id AS other, weight FROM edges WHERE to_verse_id   = w.id
    ) e
    WHERE e.weight >= %(min_weight)s AND e.other <> w.id
    GROUP BY e.other
    ORDER BY max(e.weight) DESC, e.other
    LIMIT %(neighbors)s
  ) n
  WHERE w.hop < %(hops)s
)
SELECT id, min(hop) AS hop FROM walk GROUP BY id;
```

### `GET /api/verses/{id}`

Sin `end`, devuelve un versículo. Con `end`, devuelve los versículos con
`id BETWEEN {id} AND {end}` en orden. `{id}` y `end` deben estar entre 1 y
66.999.999.

```json
{
  "ref": "Tito 3:5-7",
  "verses": [
    { "id": 56003005, "ref": "Tito 3:5", "text": "..." }
  ]
}
```

- 404 si `{id}` no existe.
- 422 si `end` es menor que `id`, si el rango abarca más de 200 versículos o si
  algún ID está fuera de rango.

### Errores y límites

- A `q` se le quitan los espacios de los extremos antes de validar. `q` ausente, con
  menos de 2 o más de 100 caracteres, o con el carácter NUL: 422.
- Sin coincidencias, o consulta formada solo por palabras vacías ("de la", "fue"):
  200 con `nodes` y `edges` vacíos y `total_matches` 0.
- `statement_timeout` de 5 s en las consultas de la API. Si se supera: 503.
- BD inaccesible: 503.

### Conexión a la BD

Pool asíncrono de psycopg 3 (`psycopg_pool.AsyncConnectionPool`), con un máximo de 5
conexiones, abierto en el `lifespan` de FastAPI sin esperar a que la BD responda. Se
configura con `DATABASE_URL`.

Dos ajustes para que funcione a través del pooler de Neon (PgBouncer en modo
transacción): las sentencias preparadas están desactivadas y el `statement_timeout`
se fija con `SET LOCAL` dentro de cada transacción, no como opción de conexión.

### CORS

`ALLOWED_ORIGINS` es una lista separada por comas. Solo se permite el método `GET`.

## 8. Frontend

React, Vite y TypeScript. Cytoscape.js con el layout `cytoscape-fcose`. Estado local
de React y `fetch`; sin librería de estado ni router. Interfaz en español.

### Pantalla

```
┌────────────────────────────────────────────────────────────┐
│ [ gracia                ] [Buscar]  Semillas ──●── 25      │
│                                     Vecinos  ─●─── 8       │
├──────────────────────────────────────────┬─────────────────┤
│                                          │ Romanos 3:24    │
│                                          │                 │
│            grafo (Cytoscape)             │ Siendo justifi- │
│                                          │ cados gratuita- │
│                                          │ mente por su... │
│                                          │                 │
│                                          │ Conexiones (6)  │
│                                          │ · Ef 2:8    41  │
│                                          │ · Tit 3:5-7 28  │
├──────────────────────────────────────────┴─────────────────┤
│ 25 de 276 coincidencias · 187 nodos · Referencias cruzadas │
│ de OpenBible.info (CC-BY) · Texto: Reina-Valera 1909       │
└────────────────────────────────────────────────────────────┘
```

### Grafo

- Las semillas son más grandes y de un color destacado.
- Los vecinos se colorean según su testamento (AT o NT).
- La etiqueta del nodo es `label` ("Ro 3:24").
- Las aristas llevan flecha. Su grosor crece con `log(weight)`.

### Panel lateral

- Click en un nodo: muestra `ref`, `text` y la lista de sus conexiones dentro del
  grafo, ordenadas por peso. El resto del grafo se atenúa.
- Click en una conexión de la lista: selecciona ese nodo.
- Si la conexión es una arista con rango, al pulsarla se pide
  `/api/verses/{target}?end={target_end_id}` y el panel muestra el pasaje completo.
- Click en el fondo del grafo: deselecciona y cierra el panel.

### Controles

- Buscar: botón o tecla Enter.
- Sliders de semillas (1–100) y vecinos (0–20). Relanzan la búsqueda con un retardo
  de 300 ms.
- La búsqueda se refleja en la URL como `?q=gracia`. Al cargar la página con ese
  parámetro, se lanza la búsqueda.

### Estados

- **Inicial:** texto de ayuda en el área del grafo.
- **Cargando:** indicador. Pasados 5 s añade "La API puede tardar hasta un minuto en
  despertar".
- **Sin resultados:** "No hay versículos que contengan «…»".
- **Error:** mensaje y botón de reintentar.
- **Truncado:** aviso en el pie cuando `truncated` es `true`.

### Configuración

`VITE_API_URL` en tiempo de build.

## 9. Docker y desarrollo local

### `docker-compose.yml`

| Servicio | Imagen | Descripción |
|---|---|---|
| `db` | `pgvector/pgvector:pg17` | Volumen persistente, healthcheck `pg_isready` |
| `api` | `backend/Dockerfile` | Uvicorn con `--reload`, código montado, puerto 8000, espera a `db` sana |
| `frontend` | `frontend/Dockerfile`, etapa `dev` | Vite con recarga en caliente, puerto 5173 |
| `ingest` | la de `api` | Perfil `tools`. Se lanza con `docker compose run --rm ingest`. Caché de descargas en un volumen |

Se usa la imagen con pgvector para que la fase 2 no obligue a cambiar de imagen.

### Dockerfiles

- **`backend/Dockerfile`**: `python:3.12-slim`, usuario sin privilegios, escucha en
  `${PORT:-8000}`. El mismo Dockerfile en local y en producción; en local se
  construye con `requirements-dev.txt` para incluir pytest.
- **`frontend/Dockerfile`**: etapa `dev` (Vite, con el código y `node_modules`
  montados desde el host), etapa `build` y etapa `static` (nginx) para probar en
  local el build de producción. Cloudflare Pages no lo usa.

### Variables de entorno

| Variable | Dónde | Local | Producción |
|---|---|---|---|
| `DATABASE_URL` | API | `postgresql://bible:bible@db:5432/bible` | Neon, cadena con pooling |
| `INGEST_DATABASE_URL` | Ingesta (compose) | sin definir: usa la BD local | Neon, cadena directa |
| `ALLOWED_ORIGINS` | API | `http://localhost:5173` | URL de Cloudflare Pages |
| `PORT` | API | 8000 | La pone Render |
| `VITE_API_URL` | Frontend (build) | `http://localhost:8000` | URL `onrender.com` de la API |

`.env.example` las lista todas. Los secretos no entran en el repo.

## 10. Despliegue

Queda preparado y documentado. No se ejecuta como parte de este trabajo.

- **`render.yaml`**: servicio web, runtime Docker, plan `free`, región Frankfurt,
  `dockerfilePath` y `dockerContext` en `backend/`, `healthCheckPath: /health`, y `DATABASE_URL` y
  `ALLOWED_ORIGINS` con `sync: false`.
- **Cloudflare Pages**: se configura en su panel. Directorio raíz `frontend`, comando
  `npm run build`, salida `dist`, variable `VITE_API_URL`.
- **`docs/deploy.md`**, con estos pasos:
  1. Crear el proyecto en Neon y copiar las dos cadenas de conexión.
  2. Lanzar la ingesta desde la máquina local contra la cadena directa.
  3. Crear el servicio en Render desde el blueprint y rellenar las variables.
  4. Crear el proyecto en Cloudflare Pages con la URL de la API.
  5. Poner la URL de Pages en `ALLOWED_ORIGINS` y comprobar `/health/db`.

La ingesta usa la cadena directa de Neon porque `COPY` y `CREATE EXTENSION` no deben
pasar por PgBouncer.

## 11. Tests

- **Parsers de la ingesta** (pytest, sin BD): línea de RV1909 con BOM, códigos de
  libro de eBible, referencia simple, rango dentro de un libro, rango entre libros,
  referencia a un versículo inexistente.
- **API** (pytest contra el Postgres de compose, en una base de datos aparte
  `bible_test` para no tocar los datos de desarrollo, con un dataset mínimo de una
  docena de versículos y aristas):
  - orden de las semillas y límite `seeds`;
  - búsqueda sin acentos ("redencion" encuentra "redención") y con stemming ("perdón"
    encuentra "perdonó");
  - límite `neighbors`;
  - filtro `min_weight`;
  - expansión en ambos sentidos;
  - `hops=2`;
  - aristas entre vecinos incluidas;
  - sin resultados;
  - `/api/verses` con un versículo, con un rango, 404 y 422;
  - `/health` y `/health/db`.
- **Frontend** (Vitest): las funciones de `graph.ts` (conversión de la respuesta de
  la API en elementos de Cytoscape, grosor de arista, conexiones de un nodo) y la
  construcción de URLs de `api.ts`.
- **Verificación manual**: ingesta completa en local, búsqueda de "gracia" en el
  navegador, click en un nodo, click en una conexión con rango, los dos sliders.

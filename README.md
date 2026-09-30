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

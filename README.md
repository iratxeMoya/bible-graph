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

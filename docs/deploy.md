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

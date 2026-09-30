# Rediseño de la interfaz y frases de relación: diseño

Fecha: 2026-09-30
Parte de: el MVP descrito en `2026-09-30-bible-graph-mvp-design.md` (rama `mvp`).

## 1. Objetivo

Dar a la app el aspecto de la maqueta de referencia (tema oscuro, grafo radial con
anillos luminosos, barra lateral de controles y panel de detalle) y añadir dos cosas
que la maqueta muestra y el MVP no tiene:

- una **frase que explica cada relación** entre dos versículos, generada con un modelo
  local de Ollama y guardada en la base de datos;
- **colores por tipo de libro** en los nodos.

### Criterio de éxito

- Buscar "amor" muestra un grafo con el término en el centro, las semillas alrededor y
  los vecinos en la periferia, con el aspecto de la maqueta.
- Al seleccionar un versículo, el panel lista sus relaciones con una frase explicativa
  cada una. La primera vez se generan en unos 5 segundos (unos 15 si el modelo no está
  cargado); después son instantáneas.
- La web publicada (Render, sin Ollama) muestra las frases ya generadas y, para las
  demás, el comienzo del versículo relacionado. Sigue siendo gratuita.

### Fuera del alcance

- Nombres de concepto por nodo ("Dios", "Obediencia") y categorías Concepto, Persona,
  Tema y Lugar de la maqueta. En su lugar: referencia más fragmento, y grupos de libros.
- Generar frases desde la web publicada.
- Pregenerar todas las relaciones: se pregeneran las más votadas y el resto se genera
  al navegar en local.

## 2. Decisiones tomadas

| Decisión | Elección |
|---|---|
| Alcance | Aspecto de la maqueta con los datos existentes, más frases y colores |
| Generación de frases | En el momento, con Ollama local, y guardadas para no repetirlas |
| Frases en la web publicada | Solo lectura de las ya guardadas; sin frase, se muestra el comienzo del versículo |
| Colores | Por tipo de libro, calculados; las coincidencias en ámbar |
| Modelo | `gemma4:e4b`, configurable |
| Llamadas al modelo | Una sola llamada por versículo abierto, con todas sus relaciones pendientes |

### Mediciones que justifican el modelo y el lote

En esta máquina (RTX 3070 de portátil, Ollama 0.34.4), con cuatro pares de versículos
reales:

| Modelo | Una frase en caliente | 8 frases en una llamada | Calidad observada |
|---|---|---|---|
| `llama3.2:3b` | 2,5 s | no probado | Errores de español ("la perdonación") |
| `llama3.1:8b` | 2,6 s | 4,2 s | Buena de una en una; genérica en lote |
| `gemma4:e4b` | 2,5 s | 4,6 s | La mejor, también en lote |

La primera llamada tras un rato sin uso añade de 7 a 13 s de carga del modelo.

## 3. Interfaz

### Distribución

- **Barra superior:** icono de libro y "BIBLIA EN RED" en versalitas espaciadas a la
  izquierda, buscador centrado, botón de tema a la derecha.
- **Barra lateral izquierda (260 px):**
  - slider **Semillas** (1–100, por defecto 5) con el texto "Pasajes que contienen el
    término o concepto de búsqueda.";
  - slider **Vecinos** (0–20, por defecto 10) con el texto "Pasajes relacionados con
    las semillas.";
  - al pie: el recuento ("5 de 275 coincidencias · 48 nodos", y el aviso de recorte
    si lo hay), el texto "La Biblia es una red de conexiones. Explora cómo los pasajes
    se relacionan entre sí." y la atribución "Referencias cruzadas de OpenBible.info
    (CC-BY) · Texto: Reina-Valera 1909 (dominio público)".
- **Centro:** el grafo. Abajo a la izquierda, la leyenda en una tarjeta y los botones
  de zoom `+` y `−`.
- **Panel derecho (360 px):** aparece al seleccionar un nodo; se cierra con `×`, con
  Escape o haciendo click en el fondo del grafo.
- **Por debajo de 900 px de ancho:** la barra lateral se pliega tras un botón en la
  barra superior, y el panel se muestra como hoja inferior con altura máxima del 55 %.

### Tema

- Oscuro por defecto; claro como alternativa. La elección se guarda en `localStorage`
  (con `try/catch`: si no está disponible, se usa el oscuro).
- Colores definidos como variables CSS en `:root` y redefinidos para el tema claro con
  `[data-theme="light"]`.

### Grafo

- **Nodo central:** el término buscado, con la primera letra en mayúscula, como anillo
  ámbar grande con halo. Lo crea el frontend y lo une a cada semilla con una línea
  ámbar tenue. No es seleccionable: al pulsarlo no abre panel.
- **Semillas:** anillos ámbar medianos con halo.
- **Vecinos:** anillos pequeños con el borde del color de su grupo de libros.
- **Grupos de libros** (calculados en el frontend a partir del ID del versículo:
  libro = `id // 1.000.000`):

| Grupo | Libros | IDs de libro |
|---|---|---|
| Ley | Génesis–Deuteronomio | 1–5 |
| Históricos | Josué–Ester | 6–17 |
| Poéticos | Job–Cantares | 18–22 |
| Profetas | Isaías–Malaquías | 23–39 |
| Evangelios y Hechos | Mateo–Hechos | 40–44 |
| Cartas y Apocalipsis | Romanos–Apocalipsis | 45–66 |

- **Etiquetas:** dos líneas. Arriba la referencia abreviada en claro ("1 Co 13:4");
  debajo, más pequeña y en gris, el comienzo del versículo (hasta 40 caracteres, con
  "…"). Se dibujan en una capa HTML encima del lienzo de Cytoscape, recolocada en cada
  evento `render`, porque Cytoscape no admite dos estilos en una misma etiqueta.
- **Qué nodos llevan etiqueta:** el nodo central, las semillas, el nodo seleccionado y
  sus vecinos, y el nodo bajo el ratón. Los demás se muestran como puntos tenues.
- **Líneas:** finas y con poca opacidad. Al seleccionar un nodo, sus líneas se iluminan
  con el color del nodo del otro extremo y el resto del grafo se atenúa.
- **Layout:** `fcose`, con el nodo central fijado en el centro.
- **Zoom:** los botones `+` y `−` multiplican o dividen el zoom por 1,25 alrededor del
  centro del lienzo.

### Panel derecho

- **Cabecera:** punto del color del nodo, referencia completa ("1 Corintios 13:4"),
  nombre del grupo de libros, etiqueta "Semilla" si lo es, y el texto del versículo
  con tipografía serif.
- **"RELACIONES" y su número.** Una fila por relación dentro del grafo mostrado,
  ordenadas por votos:
  - punto del color del otro nodo;
  - referencia del otro nodo (con rango si lo tiene, "Tit 3:5-7");
  - debajo, la frase explicativa en gris; mientras se genera, una línea animada con el
    texto "Generando…"; si no hay frase, el comienzo del versículo relacionado;
  - a la derecha, `›`: al pulsar la fila se selecciona ese versículo;
  - los votos y el sentido de la referencia ("Romanos 3:24 remite a Efesios 2:8") en
    el texto emergente de la fila;
  - en las relaciones con rango, un enlace pequeño "leer pasaje" que abre el pasaje
    completo en el panel, como en el MVP.

### Técnica

- CSS propio con variables, sin Tailwind.
- Iconos: `lucide-react`.
- Tipografía: Inter, instalada con `@fontsource-variable/inter` y servida desde el
  build.

## 4. Frases de relación

### Tabla

```sql
CREATE TABLE IF NOT EXISTS relation_explanations (
  verse_a    integer NOT NULL,
  verse_b    integer NOT NULL,
  text       text    NOT NULL,
  model      text    NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (verse_a, verse_b),
  CHECK (verse_a < verse_b)
);
```

- Una frase por par sin dirección: `verse_a` es el menor de los dos IDs.
- Sin clave foránea hacia `edges` ni `verses`: la ingesta hace `TRUNCATE` de esas
  tablas y no debe borrar las frases. La ingesta no toca esta tabla.
- Se añade a `schema.sql`, que sigue siendo idempotente.

### Endpoint

`GET /api/explanations?verse={id}&others={id},{id},…`

- `verse`: el versículo abierto. `others`: de 1 a 30 IDs, separados por comas. Fuera
  de esos límites, o con valores no numéricos: 422.
- Respuesta:

```json
{
  "verse": 46013004,
  "explanations": [
    { "other": 62004008, "text": "Amar es la evidencia visible de conocer a Dios." },
    { "other": 46013007, "text": null }
  ]
}
```

- Mismo orden que `others`. `text` es `null` cuando no hay frase.

Comportamiento:

1. Se descartan los `others` que no forman una referencia cruzada con `verse` en
   ninguno de los dos sentidos: su `text` es `null` y nunca se generan.
2. Se leen las frases guardadas de los pares restantes.
3. Si faltan frases y `OLLAMA_URL` está configurada, se generan todas las que faltan en
   **una sola llamada** a Ollama, con los textos de ambos versículos de cada par.
4. Cada frase generada se valida: debe haber exactamente una por par, y cada una debe
   tener entre 20 y 160 caracteres una vez quitadas comillas y espacios de los
   extremos. Las válidas se guardan con `INSERT … ON CONFLICT DO NOTHING` y se
   devuelven; las inválidas se devuelven como `null` y no se guardan.
5. Si `OLLAMA_URL` no está configurada, Ollama no responde en 60 s o devuelve algo que
   no se puede interpretar, las frases que faltan se devuelven como `null`. El
   endpoint responde 200 en todos estos casos.

La llamada a Ollama se hace **sin tener una conexión del pool**: se leen textos y
frases, se devuelve la conexión, se genera y se pide otra conexión para guardar. El
`statement_timeout` de 5 s sigue aplicándose solo a las consultas.

### Llamada a Ollama

- `POST {OLLAMA_URL}/api/generate` con `stream: false`, `think: false`,
  `format: "json"`, `temperature: 0.2` y el modelo de `OLLAMA_MODEL`.
- Prompt: los pares numerados con la referencia y el texto de cada versículo, y la
  instrucción de devolver `{"frases": [...]}` con una frase por par, en español actual,
  de 6 a 12 palabras, sin repetir las referencias.
- El cliente de Ollama es una dependencia inyectable, para poder sustituirlo en los
  tests.

### Configuración

| Variable | Local (compose) | Render |
|---|---|---|
| `OLLAMA_URL` | `http://host.docker.internal:11434` | sin definir |
| `OLLAMA_MODEL` | `gemma4:e4b` (por defecto) | no aplica |

El servicio `api` de compose añade `extra_hosts: ["host.docker.internal:host-gateway"]`
para que `host.docker.internal` resuelva también en Linux.

### Pregeneración en lote

`python -m ingest.explain [--limit N] [--batch 8]`, que en compose se lanza con
`docker compose run --rm ingest python -m ingest.explain --limit 5000`.

- Recorre los pares de `edges` de mayor a menor peso (sin dirección, con el mayor peso
  de los dos sentidos), salta los que ya tienen frase y genera en lotes de `--batch`.
- Se detiene tras generar `--limit` frases, o con Ctrl+C sin perder lo ya guardado.
- Usa `DATABASE_URL` y, en compose, `INGEST_DATABASE_URL`, así que puede rellenar Neon.
- Imprime el avance: frases generadas, descartadas y ritmo por hora.
- Sin `OLLAMA_URL`, termina con código de error y un mensaje claro.

Referencia de ritmo medido: unos 4,6 s por lote de 8, es decir unas 6.000 frases por
hora.

## 5. Tests

- **Backend (pytest):**
  - frases guardadas se devuelven sin llamar al generador;
  - las que faltan se generan en una sola llamada y se guardan;
  - el par se guarda sin dirección y sirve en ambos sentidos;
  - un `other` que no es referencia cruzada devuelve `null` y no se genera;
  - frases inválidas (número distinto de pares, demasiado cortas o largas) no se
    guardan;
  - sin `OLLAMA_URL`, generador caído o respuesta ilegible: 200 con `null`;
  - validación de parámetros (422);
  - la ingesta no borra las frases;
  - `ingest.explain` respeta `--limit`, salta lo existente y falla sin `OLLAMA_URL`.
- **Frontend (Vitest):** grupo de libro a partir del ID, texto de las etiquetas
  (recorte a 40 caracteres), elementos de Cytoscape con el nodo central y sus aristas,
  y orden de las relaciones.
- **Navegador:** comprobación con Chromium sin interfaz (Playwright en Docker) de la
  búsqueda, el nodo central, la selección, las frases (con Ollama real), el tema claro,
  el zoom y la vista estrecha.

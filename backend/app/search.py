"""Búsqueda léxica, expansión del grafo y lectura de pasajes."""

from psycopg import AsyncConnection

from app.refs import format_ref
from app.schemas import Edge, Node, PassageResponse, SearchResponse, Verse

TRANSLATION = "RV1909"
MAX_NODES = 600

# Las semillas se ordenan por relevancia léxica y, a igualdad, por los votos que
# reciben como destino de referencias cruzadas: sin ese desempate, una palabra que
# aparece una vez por versículo devolvería siempre los primeros versículos del Génesis.
#
# `walk` arrastra el peso de la arista por la que se llega a cada nodo. Si hay que
# recortar a MAX_NODES, caen primero los nodos de mayor salto y, dentro de un salto,
# los de menor peso: recortar por orden canónico dejaría fuera el Nuevo Testamento.
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
walk(id, hop, weight) AS (
  SELECT id, 0, NULL::integer FROM seeds
  UNION
  SELECT n.id, w.hop + 1, n.weight
  FROM walk w
  CROSS JOIN LATERAL (
    SELECT e.other AS id, max(e.weight) AS weight
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
  SELECT DISTINCT ON (id) id, hop, weight
  FROM walk
  ORDER BY id, hop, weight DESC NULLS FIRST
),
capped AS (
  SELECT id, hop
  FROM reached
  ORDER BY hop, weight DESC NULLS FIRST, id
  LIMIT %(max_nodes)s
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

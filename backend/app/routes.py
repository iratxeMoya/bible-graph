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
        pool,
        request.app.state.generator,
        verse,
        parse_ids(others),
        lock=getattr(request.app.state, "generation_lock", None),
        cancelled=request.is_disconnected,
    )

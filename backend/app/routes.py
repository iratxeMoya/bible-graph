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

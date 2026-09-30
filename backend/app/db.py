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

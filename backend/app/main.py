"""Aplicación FastAPI."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import psycopg
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import Settings
from app.db import create_pool
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


def create_app(settings: Settings | None = None) -> FastAPI:
    app = FastAPI(title="bible-graph", lifespan=lifespan)
    app.state.settings = settings or Settings.from_env()
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

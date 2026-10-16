"""FastAPI application factory + wiring.

Mirrors the talentNet Express app: CORS (credentialed, single origin for the
refresh cookie), feature routers under /api, and a central error handler that
turns thrown AppErrors into consistent JSON. Infra (DB pool, storage bucket) is
opened in the lifespan so importing this module never touches the network.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .db import pool
from .db_migrate import run_migrations
from .env import env
from .errors import AppError
from .routers import api_router
from .routers.us_valuations import REVIEW_ONLY
from .security.headers import add_security_headers
from .storage import ensure_bucket

log = logging.getLogger("uvicorn.error")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if REVIEW_ONLY:
        # The authenticated immutable review is not a deployment: no DB/storage
        # startup, migrations, jobs, or saved valuations may be triggered.
        yield
        return
    pool.open()
    # Ensure the schema exists before serving. Essential for a managed DB
    # (Supabase, Neon, …) that never runs infrastructure/postgres/init/*.sql.
    # Skipped under tests, which run hermetically without a real database.
    if env.APP_ENV != "test":
        run_migrations()
    try:
        ensure_bucket()
    except Exception as exc:  # storage not ready shouldn't stop the API booting
        log.warning("Could not ensure storage bucket: %s", exc)
    yield
    pool.close()


app = FastAPI(title="PSE Valuation API", lifespan=lifespan)

if REVIEW_ONLY:
    from .security.jwt import verify_access_token,TokenError
    @app.middleware("http")
    async def read_only_catalog_boundary(request: Request, call_next):
        header=request.headers.get('authorization','')
        try:
            if not header.startswith('Bearer '):raise ValueError('missing authentication')
            verify_access_token(header[7:])
        except (ValueError,TokenError):
            return JSONResponse(status_code=401,content={'error':'Authenticated read-only review only'})
        path=request.url.path
        allowed = (path=='/api/us-valuations' or path.startswith('/api/us-valuations/')) and (
            request.method == 'GET' or (request.method == 'POST' and request.url.path.endswith('/calculator')))
        if not allowed:
            return JSONResponse(status_code=403, content={'error':'Read-only catalog review only'})
        from .routers.us_valuations import CATALOG
        private700 = CATALOG.manifest.get('private_review', {}).get('profile') == 'B16-B20-FROZEN-PRIVATE-1' or CATALOG.manifest.get('staged_review', {}).get('profile') == 'B16-B20-STAGED-PUBLIC-1'
        if private700 and request.method == 'POST':
            body = await request.json()
            if body.get('save') or body.get('manual_price') is not None:
                return JSONResponse(status_code=403, content={'error':'Private700 cannot save or add market price inputs'})
        response = await call_next(request)
        if private700:
            response.headers['Cache-Control'] = 'no-store'
        return response

# Secure response headers (Helmet-equivalent). Added first so it wraps every
# response, including CORS preflights and error responses.
add_security_headers(app)

# credentials=True + a specific origin is required for the refresh cookie to be
# sent/received cross-origin (Vite dev server -> API).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[env.CLIENT_URL],
    # Cloud Run exposes each service on two URL forms (project-number and hash);
    # accept either for the finsight staging/prod frontend so the app isn't
    # blocked depending on which URL the user opens.
    allow_origin_regex=r"https://finsight-frontend-(staging|prod)-[a-z0-9.-]+\.run\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(AppError)
async def handle_app_error(_request: Request, exc: AppError) -> JSONResponse:
    return JSONResponse(status_code=exc.status, content={"error": exc.message})


@app.exception_handler(Exception)
async def handle_unexpected(_request: Request, exc: Exception) -> JSONResponse:
    # Log the full error but return a generic message so we don't leak internals.
    log.exception("Unhandled request error: %s", exc)
    return JSONResponse(status_code=500, content={"error": "Internal Server Error"})


app.include_router(api_router)

"""Idempotent startup migrations — the runtime source of truth for the schema.

The SQL in infrastructure/postgres/init/ only runs once, on a *fresh* local
Postgres volume (via the docker-entrypoint-initdb.d hook). A managed database
(Supabase, Neon, RDS) never runs it — and the backend image doesn't even ship
that directory — so everything the app needs is (re)created here on every boot.

Every statement is a guarded no-op once applied (IF NOT EXISTS / IF EXISTS), so
running this repeatedly against any Postgres — empty or already-populated — is
safe. Keep it in sync with infrastructure/postgres/init/*.sql; when the schema
stabilises, graduate both to a real migration tool.
"""

import logging

from .db import query

log = logging.getLogger("uvicorn.error")

# Mirrors infrastructure/postgres/init/01-extensions.sql + 02-schema.sql, with
# the Google-sign-in additions to `users` folded in. Ordered so referenced
# tables (users, companies) exist before the tables that reference them.
_STATEMENTS: tuple[str, ...] = (
    # pgvector: available for future semantic search over filings. Harmless if
    # unused. Available on Supabase/Neon/RDS.
    "CREATE EXTENSION IF NOT EXISTS vector",
    # --- Auth ---
    """
    CREATE TABLE IF NOT EXISTS users (
      id            SERIAL PRIMARY KEY,
      email         TEXT NOT NULL UNIQUE,
      password_hash TEXT,
      role          TEXT NOT NULL DEFAULT 'user',
      is_verified   BOOLEAN NOT NULL DEFAULT FALSE,
      google_sub    TEXT UNIQUE,
      created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
      updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    # For databases created before Google sign-in existed: add the column and
    # relax the password requirement (Google-only accounts have no password).
    "ALTER TABLE users ADD COLUMN IF NOT EXISTS google_sub TEXT",
    """
    DO $$ BEGIN
      IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'users_google_sub_key'
      ) THEN
        ALTER TABLE users ADD CONSTRAINT users_google_sub_key UNIQUE (google_sub);
      END IF;
    END $$
    """,
    "ALTER TABLE users ALTER COLUMN password_hash DROP NOT NULL",
    # --- Auth sessions (revocable refresh tokens; formerly Redis) ---
    # One row per live refresh token. is_valid() checks expires_at; rows are
    # pruned opportunistically on create() (see services/session_service.py).
    """
    CREATE TABLE IF NOT EXISTS sessions (
      jti        TEXT PRIMARY KEY,
      user_id    INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
      expires_at TIMESTAMPTZ NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_sessions_user ON sessions (user_id)",
    "CREATE INDEX IF NOT EXISTS idx_sessions_expires ON sessions (expires_at)",
    # --- Rate-limit counters (fixed window per key; formerly Redis) ---
    """
    CREATE TABLE IF NOT EXISTS rate_limits (
      key      TEXT PRIMARY KEY,
      count    INTEGER NOT NULL,
      reset_at TIMESTAMPTZ NOT NULL
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_rate_limits_reset ON rate_limits (reset_at)",
    # --- Files ---
    """
    CREATE TABLE IF NOT EXISTS files (
      id           SERIAL PRIMARY KEY,
      object_key   TEXT NOT NULL,
      filename     TEXT NOT NULL,
      content_type TEXT,
      size_bytes   BIGINT,
      created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    # --- Valuation domain ---
    """
    CREATE TABLE IF NOT EXISTS companies (
      id         SERIAL PRIMARY KEY,
      ticker     TEXT NOT NULL,
      name       TEXT NOT NULL,
      sector     TEXT,
      currency   TEXT NOT NULL DEFAULT 'PHP',
      market     TEXT NOT NULL DEFAULT 'PH',
      exchange   TEXT,
      cik        TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "ALTER TABLE companies ADD COLUMN IF NOT EXISTS market TEXT NOT NULL DEFAULT 'PH'",
    "ALTER TABLE companies ADD COLUMN IF NOT EXISTS exchange TEXT",
    "ALTER TABLE companies ADD COLUMN IF NOT EXISTS cik TEXT",
    "ALTER TABLE companies DROP CONSTRAINT IF EXISTS companies_ticker_key",
    "CREATE INDEX IF NOT EXISTS idx_companies_sector ON companies (sector)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_companies_market_ticker ON companies (market, ticker)",
    """
    CREATE TABLE IF NOT EXISTS market_assumptions (
      id                       SERIAL PRIMARY KEY,
      key                      TEXT NOT NULL UNIQUE,
      risk_free_rate           NUMERIC NOT NULL,
      equity_risk_premium      NUMERIC NOT NULL,
      graham_current_yield     NUMERIC NOT NULL,
      graham_normalizing_yield NUMERIC NOT NULL DEFAULT 4.4,
      graham_base_pe           NUMERIC NOT NULL DEFAULT 8.5,
      default_perpetual_growth NUMERIC NOT NULL DEFAULT 0.03,
      updated_at               TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS valuations (
      id          SERIAL PRIMARY KEY,
      user_id     INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
      company_id  INTEGER REFERENCES companies (id) ON DELETE SET NULL,
      model       TEXT NOT NULL,
      inputs      JSONB NOT NULL,
      assumptions JSONB NOT NULL DEFAULT '{}'::jsonb,
      result      JSONB NOT NULL,
      created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_valuations_user ON valuations (user_id, created_at DESC)",
    "CREATE INDEX IF NOT EXISTS idx_valuations_company ON valuations (company_id)",
    "ALTER TABLE valuations ADD COLUMN IF NOT EXISTS us_company BOOLEAN NOT NULL DEFAULT FALSE",
    "ALTER TABLE valuations ADD COLUMN IF NOT EXISTS ticker TEXT",
    "ALTER TABLE valuations ADD COLUMN IF NOT EXISTS model_version TEXT",
    "ALTER TABLE valuations ADD COLUMN IF NOT EXISTS user_price NUMERIC",
    "CREATE INDEX IF NOT EXISTS idx_valuations_us_ticker ON valuations (ticker) WHERE us_company",
    # --- Portfolio-aware insights (see docs/architecture.md) ---
    # What a user owns — the personalization key. Everything in the feed is
    # scoped to these rows via holdings.user_id.
    """
    CREATE TABLE IF NOT EXISTS holdings (
      id         SERIAL PRIMARY KEY,
      user_id    INTEGER NOT NULL REFERENCES users (id) ON DELETE CASCADE,
      company_id INTEGER NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (user_id, company_id)
    )
    """,
    # Holdings is a pure owned-company watchlist (news-scoping key) — drop the
    # old shares/avg_cost columns from databases created before this change.
    "ALTER TABLE holdings DROP COLUMN IF EXISTS shares",
    "ALTER TABLE holdings DROP COLUMN IF EXISTS avg_cost",
    "CREATE INDEX IF NOT EXISTS idx_holdings_user ON holdings (user_id)",
    # Raw articles from the news source(s). Global (not user-specific). The
    # embedding is for future pgvector thematic matching; dimension matches the
    # OPENAI_EMBED_MODEL output (text-embedding-3-small -> 1536).
    """
    CREATE TABLE IF NOT EXISTS news_items (
      id           SERIAL PRIMARY KEY,
      source       TEXT NOT NULL,
      url          TEXT NOT NULL UNIQUE,
      title        TEXT NOT NULL,
      body         TEXT,
      published_at TIMESTAMPTZ,
      status       TEXT NOT NULL DEFAULT 'pending',
      embedding    vector(1536),
      created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_news_items_status ON news_items (status)",
    # Article -> affected stocks. A property of the article, shared by all users.
    """
    CREATE TABLE IF NOT EXISTS article_stocks (
      news_item_id INTEGER NOT NULL REFERENCES news_items (id) ON DELETE CASCADE,
      company_id   INTEGER NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
      link_type    TEXT NOT NULL DEFAULT 'direct',
      relevance    NUMERIC,
      PRIMARY KEY (news_item_id, company_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_article_stocks_company ON article_stocks (company_id)",
    # Article -> affected sectors/themes. Also a property of the article.
    """
    CREATE TABLE IF NOT EXISTS article_sectors (
      news_item_id INTEGER NOT NULL REFERENCES news_items (id) ON DELETE CASCADE,
      sector       TEXT NOT NULL,
      link_type    TEXT NOT NULL DEFAULT 'direct',
      relevance    NUMERIC,
      PRIMARY KEY (news_item_id, sector)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_article_sectors_sector ON article_sectors (sector)",
    # The generated insight, one per (article, company). Shared and auditable.
    # direction is informational (headwind|tailwind|mixed) — NOT advice.
    """
    CREATE TABLE IF NOT EXISTS insights (
      id              SERIAL PRIMARY KEY,
      news_item_id    INTEGER NOT NULL REFERENCES news_items (id) ON DELETE CASCADE,
      company_id      INTEGER NOT NULL REFERENCES companies (id) ON DELETE CASCADE,
      summary         TEXT NOT NULL,
      possible_impact TEXT NOT NULL,
      direction       TEXT,
      confidence      NUMERIC,
      sources         JSONB NOT NULL DEFAULT '[]'::jsonb,
      created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (news_item_id, company_id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_insights_company ON insights (company_id, created_at DESC)",
    # --- Research workbench: per-company filing financials (see docs) ---
    # One row per scored company; `data` holds the full filing snapshot + the
    # valuation inputs the engine reads (ported from the FinSight dataset).
    """
    CREATE TABLE IF NOT EXISTS company_financials (
      company_id INTEGER PRIMARY KEY REFERENCES companies (id) ON DELETE CASCADE,
      period     TEXT,
      data       JSONB NOT NULL,
      updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    # --- Governed PSE valuation V2 evidence store ---
    """
    CREATE TABLE IF NOT EXISTS pse_securities (
      security_id TEXT PRIMARY KEY,
      issuer_id TEXT NOT NULL,
      ticker TEXT NOT NULL,
      issuer_name TEXT NOT NULL,
      security_type TEXT NOT NULL DEFAULT 'ordinary_common',
      subsector TEXT,
      listing_status TEXT,
      source_as_of DATE,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (ticker, security_type)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pse_documents (
      id BIGSERIAL PRIMARY KEY,
      issuer_id TEXT NOT NULL,
      security_id TEXT NOT NULL REFERENCES pse_securities (security_id),
      source_url TEXT,
      published_at DATE,
      retrieved_at TIMESTAMPTZ NOT NULL,
      sha256 TEXT NOT NULL UNIQUE,
      object_key TEXT NOT NULL,
      content_type TEXT,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_pse_documents_issuer ON pse_documents (issuer_id, published_at)",
    """
    CREATE TABLE IF NOT EXISTS pse_reported_facts (
      id BIGSERIAL PRIMARY KEY,
      document_id BIGINT NOT NULL REFERENCES pse_documents (id) ON DELETE CASCADE,
      metric TEXT NOT NULL,
      value NUMERIC NOT NULL,
      currency TEXT NOT NULL,
      unit_scale TEXT NOT NULL,
      period_start DATE,
      period_end DATE NOT NULL,
      period_type TEXT NOT NULL,
      measurement_type TEXT NOT NULL,
      consolidation_scope TEXT NOT NULL,
      source_page INTEGER,
      restatement_version INTEGER NOT NULL DEFAULT 0,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_pse_facts_metric_period ON pse_reported_facts (metric, period_end)",
    "CREATE UNIQUE INDEX IF NOT EXISTS idx_pse_facts_identity ON pse_reported_facts (document_id, metric, period_end, measurement_type, consolidation_scope, restatement_version)",
    """
    CREATE TABLE IF NOT EXISTS pse_assumptions (
      id BIGSERIAL PRIMARY KEY,
      version TEXT NOT NULL,
      scope TEXT NOT NULL,
      metric TEXT NOT NULL,
      scenario TEXT NOT NULL DEFAULT 'all',
      value JSONB NOT NULL,
      unit TEXT,
      effective_date DATE NOT NULL,
      source_or_rationale TEXT NOT NULL,
      reviewer TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (version, scope, metric, scenario)
    )
    """,
    "UPDATE pse_assumptions SET scenario = 'all' WHERE scenario IS NULL",
    "ALTER TABLE pse_assumptions ALTER COLUMN scenario SET DEFAULT 'all'",
    "ALTER TABLE pse_assumptions ALTER COLUMN scenario SET NOT NULL",
    """
    CREATE TABLE IF NOT EXISTS pse_valuation_runs (
      id BIGSERIAL PRIMARY KEY,
      security_id TEXT NOT NULL REFERENCES pse_securities (security_id),
      valuation_date DATE NOT NULL,
      model_version TEXT NOT NULL,
      input_hash TEXT NOT NULL,
      assumptions JSONB NOT NULL,
      private_result JSONB NOT NULL,
      availability_type TEXT NOT NULL,
      publication_state TEXT NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
      UNIQUE (security_id, valuation_date, model_version, input_hash)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS pse_adjustments (
      id BIGSERIAL PRIMARY KEY,
      run_id BIGINT NOT NULL REFERENCES pse_valuation_runs (id) ON DELETE CASCADE,
      metric TEXT NOT NULL,
      amount NUMERIC NOT NULL,
      reason TEXT NOT NULL,
      evidence TEXT NOT NULL,
      author TEXT NOT NULL,
      effective_date DATE NOT NULL,
      review_date DATE NOT NULL,
      created_at TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
)


def run_migrations() -> None:
    """Apply the schema. Called from the app lifespan, after the pool is open."""
    for statement in _STATEMENTS:
        query(statement)
    log.info("Database migrations applied (%d statements).", len(_STATEMENTS))

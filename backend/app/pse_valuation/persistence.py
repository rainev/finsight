"""Postgres/MinIO persistence boundary for reviewed PSE V2 evidence."""

from __future__ import annotations

import hashlib
from datetime import date, datetime
from typing import Any

from ..db import query, query_one
from ..storage import BUCKET, s3


def upsert_security(
    *,
    security_id: str,
    issuer_id: str,
    ticker: str,
    issuer_name: str,
    subsector: str,
    source_as_of: date,
    listing_status: str = "listed",
) -> dict[str, Any]:
    return query_one(
        """
        INSERT INTO pse_securities
          (security_id, issuer_id, ticker, issuer_name, security_type,
           subsector, listing_status, source_as_of)
        VALUES (%s, %s, %s, %s, 'ordinary_common', %s, %s, %s)
        ON CONFLICT (security_id) DO UPDATE
          SET issuer_name = EXCLUDED.issuer_name,
              subsector = EXCLUDED.subsector,
              listing_status = EXCLUDED.listing_status,
              source_as_of = EXCLUDED.source_as_of
        RETURNING *
        """,
        (security_id, issuer_id, ticker, issuer_name, subsector, listing_status, source_as_of),
    )


def capture_document(
    *,
    issuer_id: str,
    security_id: str,
    source_url: str | None,
    published_at: date | None,
    retrieved_at: datetime,
    filename: str,
    raw: bytes,
    content_type: str = "application/pdf",
) -> dict[str, Any]:
    digest = hashlib.sha256(raw).hexdigest()
    object_key = f"pse-v2/raw/{issuer_id}/{digest}/{filename}"
    s3.put_object(Bucket=BUCKET, Key=object_key, Body=raw, ContentType=content_type)
    return query_one(
        """
        INSERT INTO pse_documents
          (issuer_id, security_id, source_url, published_at, retrieved_at,
           sha256, object_key, content_type)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (sha256) DO UPDATE SET retrieved_at = EXCLUDED.retrieved_at
        RETURNING *
        """,
        (
            issuer_id,
            security_id,
            source_url,
            published_at,
            retrieved_at,
            digest,
            object_key,
            content_type,
        ),
    )


def store_reported_fact(document_id: int, fact: dict[str, Any]) -> dict[str, Any]:
    return query_one(
        """
        INSERT INTO pse_reported_facts
          (document_id, metric, value, currency, unit_scale, period_start,
           period_end, period_type, measurement_type, consolidation_scope,
           source_page, restatement_version)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT
          (document_id, metric, period_end, measurement_type,
           consolidation_scope, restatement_version)
        DO UPDATE SET
          value = EXCLUDED.value,
          currency = EXCLUDED.currency,
          unit_scale = EXCLUDED.unit_scale,
          period_start = EXCLUDED.period_start,
          period_type = EXCLUDED.period_type,
          source_page = EXCLUDED.source_page
        RETURNING *
        """,
        (
            document_id,
            fact["metric"],
            fact["value"],
            fact["currency"],
            fact["unit_scale"],
            fact.get("period_start"),
            fact["period_end"],
            fact["period_type"],
            fact["measurement_type"],
            fact["consolidation_scope"],
            fact.get("source_page"),
            fact.get("restatement_version", 0),
        ),
    )


def store_adjustment(run_id: int, adjustment: dict[str, Any]) -> dict[str, Any]:
    return query_one(
        """
        INSERT INTO pse_adjustments
          (run_id, metric, amount, reason, evidence, author, effective_date, review_date)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING *
        """,
        (
            run_id,
            adjustment["metric"],
            adjustment["amount"],
            adjustment["reason"],
            adjustment["evidence"],
            adjustment["author"],
            adjustment["effective_date"],
            adjustment["review_date"],
        ),
    )


def store_assumption(assumption: dict[str, Any]) -> dict[str, Any]:
    import json

    return query_one(
        """
        INSERT INTO pse_assumptions
          (version, scope, metric, scenario, value, unit, effective_date,
           source_or_rationale, reviewer)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (version, scope, metric, scenario) DO UPDATE
          SET value = EXCLUDED.value,
              source_or_rationale = EXCLUDED.source_or_rationale,
              reviewer = EXCLUDED.reviewer
        RETURNING *
        """,
        (
            assumption["version"],
            assumption["scope"],
            assumption["metric"],
            assumption.get("scenario") or "all",
            json.dumps(assumption["value"]),
            assumption.get("unit"),
            assumption["effective_date"],
            assumption["source_or_rationale"],
            assumption["reviewer"],
        ),
    )


def store_valuation_run(artifact: dict[str, Any], private_result: dict[str, Any]) -> dict[str, Any]:
    import json

    return query_one(
        """
        INSERT INTO pse_valuation_runs
          (security_id, valuation_date, model_version, input_hash, assumptions,
           private_result, availability_type, publication_state)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (security_id, valuation_date, model_version, input_hash) DO UPDATE
          SET private_result = EXCLUDED.private_result,
              availability_type = EXCLUDED.availability_type,
              publication_state = EXCLUDED.publication_state
        RETURNING *
        """,
        (
            artifact["security"]["security_id"],
            artifact["valuation_date"],
            artifact["model_version"],
            artifact["input_hash"],
            json.dumps(artifact["public_assumptions"]),
            json.dumps(private_result),
            artifact["availability_type"],
            artifact["publication_state"],
        ),
    )


def list_documents(issuer_id: str) -> list[dict[str, Any]]:
    return query(
        "SELECT * FROM pse_documents WHERE issuer_id = %s ORDER BY published_at, id",
        (issuer_id,),
    )

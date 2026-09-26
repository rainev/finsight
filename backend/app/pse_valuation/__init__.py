"""Governed Philippine-equity valuation pipeline (V2).

The package is intentionally separate from the legacy manual PSE workbench.
Pure model functions live under :mod:`app.pse_valuation.models`; catalog and
artifact modules provide the staged, fail-closed serving boundary.
"""

SCHEMA_VERSION = "FINSIGHT-PSE-VALUATION-2.0"
MODEL_VERSION = "PSE-V2-PILOT-1.1"
CATALOG_VERSION = "PSE-V2-PILOT-2026-09-21-1.1"

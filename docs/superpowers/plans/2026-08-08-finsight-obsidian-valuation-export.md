# Finsight Obsidian Valuation Export Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Export concise, provenance-linked US valuation summaries from the existing SEC/XBRL-derived JSON artifacts into the repository’s Obsidian vault so Graphify can index them without loading raw filings.

**Architecture:** Add a pure Python exporter that reads `backend/app/data/us_valuations/*.json`, renders one Markdown note per issuer plus an index note, and writes only inside a configurable vault subdirectory. The exporter will preserve SEC filing URLs, local artifact paths, model/assumption/review fields, and scenario ranges while avoiding raw XBRL payloads and secrets. It will fail clearly on malformed artifacts and support a dry run.

**Tech Stack:** Python 3 standard library, Markdown, pytest.

## Global Constraints

- Do not call the SEC or any external API while exporting; use the existing local artifacts.
- Do not copy raw XBRL, full filing text, secrets, or large source payloads into Obsidian.
- Preserve existing files outside the exporter output directory.
- Keep output deterministic and stable for Graphify indexing.
- Use the project root as the Obsidian vault because it already contains `.obsidian/`.

### Task 1: Add failing exporter tests

**Files:**
- Create: `backend/tests/test_obsidian_export.py`

- [x] **Step 1: Write tests for deterministic note rendering and index output.**

```python
def test_export_writes_company_note_and_index_without_raw_payload(tmp_path):
    result = export_valuations(sample_artifact_dir, tmp_path / "vault" / "Finsight" / "US Valuations")
    assert result["exported"] == 1
    note = (tmp_path / "vault/Finsight/US Valuations/MSFT.md").read_text()
    assert "SEC filing" in note
    assert "Residual Income" in note
    assert "raw_text" not in note
    assert (tmp_path / "vault/Finsight/US Valuations/README.md").exists()
```

```python
def test_export_skips_invalid_artifact_and_reports_error(tmp_path):
    result = export_valuations(tmp_path / "artifacts", tmp_path / "vault")
    assert result["exported"] == 0
    assert result["errors"]
```

- [x] **Step 2: Run the focused tests and verify the expected missing-module failure.**

Run: `PYTHONPATH=backend pytest -q backend/tests/test_obsidian_export.py`

Expected: collection failure because `scripts/export_us_valuations_to_obsidian.py` does not yet exist.

### Task 2: Implement the exporter

**Files:**
- Create: `scripts/export_us_valuations_to_obsidian.py`
- Test: `backend/tests/test_obsidian_export.py`

**Interface:**

```python
def render_valuation_note(artifact: dict, artifact_path: Path) -> str: ...
def export_valuations(artifact_dir: Path, output_dir: Path, *, dry_run: bool = False) -> dict: ...
```

- [x] **Step 1: Implement safe scalar formatting and Markdown escaping.**
- [x] **Step 2: Render issuer, valuation date, filing metadata, model policy, methodology, public assumptions, scenarios, review state, warnings, and provenance links.**
- [x] **Step 3: Write one ticker note and a deterministic index sorted by ticker.**
- [x] **Step 4: Reject path traversal and skip malformed/non-JSON artifacts with structured error counts.**
- [x] **Step 5: Add CLI flags `--artifacts`, `--output`, and `--dry-run`, defaulting to the local artifact directory and `Finsight/US Valuations` inside the project vault.**
- [x] **Step 6: Run the focused tests and confirm green.**

### Task 3: Document and verify the connection

**Files:**
- Modify: `README.md`
- Test: `backend/tests/test_obsidian_export.py`

- [x] **Step 1: Add the no-network export command and explain that Obsidian should open the repository root as the vault.**
- [x] **Step 2: Add a test that the exporter uses the SEC URL from `source_financial_statement` and the local artifact path without copying raw XBRL.**
- [x] **Step 3: Run focused tests, compile the script, and run `git diff --check`.**
- [x] **Step 4: Inspect generated sample output and report any environment limitation separately from test results.**

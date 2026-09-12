from __future__ import annotations

import hashlib
import json

from app.us_valuation.refresh_source_ingestion import _event_with_index, _event_records


class _FakeClient:
    def __init__(self, index: dict, bodies: dict[str, bytes]):
        self.index = index
        self.bodies = bodies

    def filing_index(self, cik: str, accession: str, *, refresh: bool = False) -> dict:
        return self.index

    def filing_attachment(self, cik: str, accession: str, filename: str, *, refresh: bool = False, max_bytes=None) -> bytes:
        if filename not in self.bodies:
            raise RuntimeError("missing cached body")
        return self.bodies[filename]


def _event() -> dict:
    return {
        "accession": "0000000000-26-000001",
        "form": "8-K",
        "filed_date": "2026-08-01",
        "primaryDocument": "body.htm",
    }


def test_exhibit_relationship_requires_sgml_or_primary_body_proof() -> None:
    body = b'<html><body><a href="generic.bin">Exhibit 99.1 earnings attachment</a></body></html>'
    sgml = b"<DOCUMENT>\n<TYPE>EX-99.1\n<FILENAME>generic.bin\n</DOCUMENT>"
    attachment = b"reported earnings bytes"
    client = _FakeClient(
        {"directory": {"item": [
            {"name": "body.htm", "type": "8-K"},
            {"name": "generic.bin", "type": "binary"},
            {"name": "unlinked.bin", "type": "binary"},
        ]}},
        {
            "body.htm": body,
            "0000000000-26-000001.txt": sgml,
            "generic.bin": attachment,
        },
    )
    result = _event_with_index(client, _event(), cik="0000000000", refresh=False)
    assert result["relationships_status"] == "exhibit_relationships_captured"
    assert result["relationships"][0]["type"] == "EX-99.1"
    assert result["relationships"][0]["attachment_sha256"] == hashlib.sha256(attachment).hexdigest()
    assert [row["name"] for row in result["attachments"]] == ["generic.bin"]
    assert "unlinked.bin" not in json.dumps(result["relationships"])


def test_index_alone_and_missing_body_are_review_exceptions() -> None:
    client = _FakeClient(
        {"directory": {"item": [{"name": "generic.bin", "type": "binary"}]}},
        {"generic.bin": b"not enough relationship evidence"},
    )
    result = _event_with_index(client, _event(), cik="0000000000", refresh=False)
    assert result["relationships"] == []
    assert result["relationships_status"] == "review_exception"
    assert any("no exhibit relationship" in row.get("reason", "") for row in result["review_exceptions"])


def test_submission_record_preserves_primary_document_through_capture():
    events = _event_records([{'accessionNumber': '0000000000-26-000001',
        'form': '8-K', 'filingDate': '2026-08-01', 'reportDate': '2026-07-31',
        'primaryDocument': 'body.htm', 'items': '2.02,9.01'}],
        cik='0000000000', cutoff='2026-08-14', event_since='2026-07-01',
        allowed_items=frozenset({'2.02','9.01'}))
    client = _FakeClient({'directory': {'item': [{'name': 'body.htm'}, {'name': 'earnings.htm'}]}},
        {'body.htm': b'<a href="earnings.htm">Exhibit 99.1</a>',
         'earnings.htm': b'earnings', '0000000000-26-000001.txt': b''})
    result = _event_with_index(client, events[0], cik='0000000000', refresh=False)
    assert result['relationships_status'] == 'exhibit_relationships_captured'
    assert any(row['role'] == 'primary_filing' for row in result['document_sources'])

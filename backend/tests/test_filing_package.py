"""Hermetic tests for reproducible SEC structural filing packages."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from app.us_valuation.filing_package import (
    FilingPackageIncomplete,
    cache_structural_filing_package,
)
from app.us_valuation.sec_client import SecClient


class FakeSecClient:
    """A no-network SEC client whose filing directory is fully controlled by a test."""

    def __init__(self, *, index_names: list[str], attachments: dict[str, bytes] | None = None) -> None:
        self.index_names = index_names
        self.attachments = attachments or {
            name: f"contents:{name}".encode("utf-8") for name in index_names
        }
        self.requested: list[str] = []

    def filing_index(self, cik: str, accession: str, *, refresh: bool = False) -> dict[str, object]:
        return {"directory": {"item": [{"name": name} for name in self.index_names]}}

    def filing_attachment(
        self,
        cik: str,
        accession: str,
        filename: str,
        *,
        refresh: bool = False,
    ) -> bytes:
        self.requested.append(filename)
        return self.attachments[filename]


def test_package_cache_downloads_only_structural_resources(tmp_path: Path) -> None:
    client = FakeSecClient(
        index_names=[
            "fsi-20251231.htm",
            "fsi-2025.xsd",
            "fsi-2025_pre.xml",
            "fsi-2025_cal.xml",
            "fsi-2025_lab.xml",
            "press-release.pdf",
        ]
    )
    entrypoint = cache_structural_filing_package(
        client,
        cik="0000000001",
        accession="0000000001-26-000001",
        primary_document="fsi-20251231.htm",
        output_dir=tmp_path,
    )

    assert entrypoint.name == "fsi-20251231.htm"
    assert not (entrypoint.parent / "press-release.pdf").exists()
    manifest = json.loads((entrypoint.parent / "package-manifest.json").read_text())
    assert manifest["accession"] == "0000000001-26-000001"
    assert manifest["files"][0]["source_url"].startswith(
        "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/"
    )
    assert set(client.requested) == {
        "fsi-20251231.htm",
        "fsi-2025.xsd",
        "fsi-2025_pre.xml",
        "fsi-2025_cal.xml",
        "fsi-2025_lab.xml",
    }


def test_package_cache_downloads_only_the_matching_instance_xml(tmp_path: Path) -> None:
    client = FakeSecClient(
        index_names=[
            "fsi-20251231.htm",
            "fsi-2025.xsd",
            "fsi-2025.xml",
            "unrelated-exhibit.xml",
            "FilingSummary.xml",
        ]
    )

    cache_structural_filing_package(
        client,
        cik="1",
        accession="0000000001-26-000001",
        primary_document="fsi-20251231.htm",
        output_dir=tmp_path,
    )

    assert set(client.requested) == {
        "fsi-20251231.htm",
        "fsi-2025.xsd",
        "fsi-2025.xml",
    }


def test_filing_index_uses_unpadded_cik_in_sec_archive_url(tmp_path: Path) -> None:
    class RecordingSecClient(SecClient):
        def _get_json(
            self,
            url: str,
            *,
            cache_name: str,
            refresh: bool,
        ) -> dict[str, object]:
            self.url = url
            return {}

    client = RecordingSecClient(user_agent=None, cache_dir=tmp_path)
    client.filing_index("0000320193", "0000320193-25-000001")

    assert client.url == (
        "https://www.sec.gov/Archives/edgar/data/320193/"
        "000032019325000001/index.json"
    )


def test_filing_index_retries_malformed_network_json_before_caching(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    payloads = iter(
        [
            b"not-json",
            b'{"directory":{"item":[]}}',
        ]
    )
    calls: list[str] = []

    class Response:
        def __init__(self, body: bytes) -> None:
            self.body = body

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self) -> bytes:
            return self.body

    def fake_urlopen(request: object, *, timeout: int) -> Response:
        calls.append(request.full_url)  # type: ignore[attr-defined]
        return Response(next(payloads))

    monkeypatch.setattr("app.us_valuation.sec_client.urlopen", fake_urlopen)
    monkeypatch.setattr("app.us_valuation.sec_client.time.sleep", lambda _: None)
    client = SecClient(
        user_agent="FinSight contact@example.com",
        cache_dir=tmp_path,
        requests_per_second=5,
        max_retries=1,
    )

    assert client.filing_index("1", "0000000001-26-000001") == {
        "directory": {"item": []}
    }
    cache_path = tmp_path / "archives/CIK0000000001/000000000126000001/index.json"
    assert len(calls) == 2
    assert cache_path.read_bytes() == b'{"directory":{"item":[]}}'
    metadata = json.loads(
        cache_path.with_suffix(".json.meta.json").read_text(encoding="utf-8")
    )
    assert metadata["sha256"] == hashlib.sha256(cache_path.read_bytes()).hexdigest()


def test_cached_malformed_filing_index_fails_clearly(tmp_path: Path) -> None:
    cache_path = tmp_path / "archives/CIK0000000001/000000000126000001/index.json"
    cache_path.parent.mkdir(parents=True)
    cache_path.write_bytes(b"not-json")

    with pytest.raises(RuntimeError, match="Invalid SEC cache file: index.json"):
        SecClient(user_agent=None, cache_dir=tmp_path).filing_index(
            "1", "0000000001-26-000001"
        )


@pytest.mark.parametrize("filename", ["../secret", "/tmp/file.xsd", "nested/file.xml"])
def test_filing_attachment_rejects_unsafe_names(filename: str, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="safe file name"):
        SecClient(user_agent=None, cache_dir=tmp_path).filing_attachment(
            "1", "0000000001-26-000001", filename
        )


def test_package_cache_rejects_missing_locally_referenced_schema(tmp_path: Path) -> None:
    client = FakeSecClient(
        index_names=["fsi-20251231.htm"],
        attachments={
            "fsi-20251231.htm": (
                b'<html><head><link href="missing-extension.xsd" /></head></html>'
            )
        },
    )

    with pytest.raises(FilingPackageIncomplete, match="missing-extension.xsd"):
        cache_structural_filing_package(
            client,
            cik="1",
            accession="0000000001-26-000001",
            primary_document="fsi-20251231.htm",
            output_dir=tmp_path,
        )


@pytest.mark.parametrize(
    "reference",
    ["missing-extension.xsd?v=1", "missing-extension.xsd#schema"],
)
def test_package_cache_rejects_missing_schema_with_url_suffix(
    reference: str,
    tmp_path: Path,
) -> None:
    client = FakeSecClient(
        index_names=["fsi-20251231.htm"],
        attachments={
            "fsi-20251231.htm": (
                f'<html><head><link href="{reference}" /></head></html>'.encode()
            )
        },
    )

    with pytest.raises(FilingPackageIncomplete, match="missing-extension.xsd"):
        cache_structural_filing_package(
            client,
            cik="1",
            accession="0000000001-26-000001",
            primary_document="fsi-20251231.htm",
            output_dir=tmp_path,
        )

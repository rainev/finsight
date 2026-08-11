"""Hermetic tests for reproducible SEC structural filing packages."""

from __future__ import annotations

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
    assert set(client.requested) == {
        "fsi-20251231.htm",
        "fsi-2025.xsd",
        "fsi-2025_pre.xml",
        "fsi-2025_cal.xml",
        "fsi-2025_lab.xml",
    }


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

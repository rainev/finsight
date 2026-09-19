"""Hermetic tests for reproducible SEC structural filing packages."""

from __future__ import annotations

import hashlib
import io
import json
import errno
from pathlib import Path
import zipfile
from urllib.error import HTTPError
from urllib.request import HTTPRedirectHandler, Request

import pytest

from app.us_valuation.filing_package import (
    FilingPackageIncomplete,
    cache_structural_filing_package,
)
from app.us_valuation.sec_client import (
    SecClient,
    canonicalize_legacy_taxonomy_url,
    validate_taxonomy_url,
)


class FakeSecClient:
    """A no-network SEC client whose filing directory is fully controlled by a test."""

    def __init__(
        self,
        *,
        index_names: list[str],
        attachments: dict[str, bytes] | None = None,
        taxonomy_resources: dict[str, bytes] | None = None,
    ) -> None:
        self.index_names = index_names
        self.attachments = attachments or {
            name: f"contents:{name}".encode("utf-8") for name in index_names
        }
        self.requested: list[str] = []
        self.taxonomy_resources = taxonomy_resources or {}
        self.requested_urls: list[str] = []

    def filing_index(self, cik: str, accession: str, *, refresh: bool = False) -> dict[str, object]:
        return {"directory": {"item": [{"name": name} for name in self.index_names]}}

    def filing_attachment(
        self,
        cik: str,
        accession: str,
        filename: str,
        *,
        refresh: bool = False,
        max_bytes: int | None = None,
    ) -> bytes:
        self.requested.append(filename)
        return self.attachments[filename]

    def taxonomy_resource(
        self,
        url: str,
        *,
        refresh: bool = False,
        max_bytes: int,
    ) -> bytes:
        self.requested_urls.append(url)
        return self.taxonomy_resources[url]


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


def test_package_cache_uses_official_xbrl_zip_when_index_hides_individual_files(
    tmp_path: Path,
) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("filing.htm", '<link href="filing.xsd"/>')
        archive.writestr("filing.xsd", "schema")
        archive.writestr("filing_pre.xml", "presentation")
    zip_name = "0000000001-26-000001-xbrl.zip"
    client = FakeSecClient(
        index_names=[zip_name],
        attachments={
            zip_name: buffer.getvalue(),
            "filing.htm": b'<link href="filing.xsd"/>',
        },
    )

    entrypoint = cache_structural_filing_package(
        client,
        cik="1",
        accession="0000000001-26-000001",
        primary_document="filing.htm",
        output_dir=tmp_path,
    )

    manifest = json.loads((entrypoint.parent / "package-manifest.json").read_text())
    schema = next(item for item in manifest["files"] if item["local_path"] == "filing.xsd")
    assert schema["source_url"].endswith(f"/{zip_name}")
    assert schema["logical_url"].endswith("/filing.xsd")
    assert schema["archive_member"] == "filing.xsd"
    assert (entrypoint.parent / "filing.xsd").read_text() == "schema"
    assert set(client.requested) == {zip_name, "filing.htm"}


def test_package_cache_reuses_verified_content_addressed_resource_store(
    tmp_path: Path,
) -> None:
    client = FakeSecClient(
        index_names=["filing.htm", "filing.xsd"],
        attachments={"filing.htm": b'<link href="filing.xsd"/>', "filing.xsd": b"schema"},
    )
    store = tmp_path / "resource-store"
    first = cache_structural_filing_package(
        client,
        cik="1",
        accession="0000000001-26-000001",
        primary_document="filing.htm",
        output_dir=tmp_path / "packages-a",
        resource_store=store,
    )
    second = cache_structural_filing_package(
        client,
        cik="1",
        accession="0000000001-26-000001",
        primary_document="filing.htm",
        output_dir=tmp_path / "packages-b",
        resource_store=store,
    )

    manifest = json.loads((first.parent / "package-manifest.json").read_text())
    store_files = [path for path in store.rglob("*") if path.is_file()]
    assert len(store_files) == len(manifest["files"])
    for item in manifest["files"]:
        package_file = first.parent / item["local_path"]
        store_file = store / item["sha256"][:2] / item["sha256"]
        assert package_file.is_file() and not package_file.is_symlink()
        assert store_file.is_file() and not store_file.is_symlink()
        assert package_file.stat().st_ino == store_file.stat().st_ino
    assert second.read_bytes() == first.read_bytes()


def test_package_cache_rejects_corrupt_resource_store_entry(tmp_path: Path) -> None:
    client = FakeSecClient(
        index_names=["filing.htm", "filing.xsd"],
        attachments={"filing.htm": b'<link href="filing.xsd"/>', "filing.xsd": b"schema"},
    )
    store = tmp_path / "resource-store"
    cache_structural_filing_package(
        client,
        cik="1",
        accession="0000000001-26-000001",
        primary_document="filing.htm",
        output_dir=tmp_path / "packages-a",
        resource_store=store,
    )
    schema_digest = hashlib.sha256(b"schema").hexdigest()
    (store / schema_digest[:2] / schema_digest).write_bytes(b"tampered")

    with pytest.raises(FilingPackageIncomplete, match="XBRL_RESOURCE_STORE_INTEGRITY"):
        cache_structural_filing_package(
            client,
            cik="1",
            accession="0000000001-26-000001",
            primary_document="filing.htm",
            output_dir=tmp_path / "packages-b",
            resource_store=store,
        )


def test_package_cache_copies_when_hard_link_is_cross_filesystem_unsupported(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    client = FakeSecClient(
        index_names=["filing.htm", "filing.xsd"],
        attachments={"filing.htm": b'<link href="filing.xsd"/>', "filing.xsd": b"schema"},
    )
    store = tmp_path / "resource-store"
    cache_structural_filing_package(
        client,
        cik="1",
        accession="0000000001-26-000001",
        primary_document="filing.htm",
        output_dir=tmp_path / "packages-a",
        resource_store=store,
    )

    def unsupported_link(*args: object, **kwargs: object) -> None:
        raise OSError(errno.EXDEV, "cross-device link")

    monkeypatch.setattr("app.us_valuation.filing_package.os.link", unsupported_link)
    entrypoint = cache_structural_filing_package(
        client,
        cik="1",
        accession="0000000001-26-000001",
        primary_document="filing.htm",
        output_dir=tmp_path / "packages-b",
        resource_store=store,
    )

    manifest = json.loads((entrypoint.parent / "package-manifest.json").read_text())
    for item in manifest["files"]:
        package_file = entrypoint.parent / item["local_path"]
        store_file = store / item["sha256"][:2] / item["sha256"]
        assert package_file.is_file() and not package_file.is_symlink()
        assert package_file.stat().st_ino != store_file.stat().st_ino
        assert hashlib.sha256(package_file.read_bytes()).hexdigest() == item["sha256"]


def test_package_cache_falls_back_to_individual_resources_when_xbrl_zip_is_unavailable(
    tmp_path: Path,
) -> None:
    zip_name = "0000000001-26-000001-xbrl.zip"
    client = FakeSecClient(
        index_names=[zip_name, "filing.htm", "filing.xsd", "filing_pre.xml"],
        attachments={
            "filing.htm": b'<link href="filing.xsd"/>',
            "filing.xsd": b"schema",
            "filing_pre.xml": b"presentation",
        },
    )

    entrypoint = cache_structural_filing_package(
        client,
        cik="1",
        accession="0000000001-26-000001",
        primary_document="filing.htm",
        output_dir=tmp_path,
    )

    manifest = json.loads((entrypoint.parent / "package-manifest.json").read_text())
    assert {item["local_path"] for item in manifest["files"]} == {
        "filing.htm",
        "filing.xsd",
        "filing_pre.xml",
    }
    assert all(zip_name not in item["source_url"] for item in manifest["files"])
    assert set(client.requested) == {
        zip_name,
        "filing.htm",
        "filing.xsd",
        "filing_pre.xml",
    }


def test_package_cache_falls_back_when_xbrl_zip_transport_fails(
    tmp_path: Path,
) -> None:
    zip_name = "0000000001-26-000001-xbrl.zip"

    class TransportUnavailableClient(FakeSecClient):
        def filing_attachment(
            self,
            cik: str,
            accession: str,
            filename: str,
            *,
            refresh: bool = False,
            max_bytes: int | None = None,
        ) -> bytes:
            if filename == zip_name:
                raise RuntimeError("SEC request failed after retries") from HTTPError(
                    "https://www.sec.gov/Archives/edgar/data/1/000000000126000001/"
                    + zip_name,
                    404,
                    "Not Found",
                    {},
                    None,
                )
            return super().filing_attachment(
                cik,
                accession,
                filename,
                refresh=refresh,
                max_bytes=max_bytes,
            )

    client = TransportUnavailableClient(
        index_names=[zip_name, "filing.htm", "filing.xsd"],
        attachments={
            "filing.htm": b'<link href="filing.xsd"/>',
            "filing.xsd": b"schema",
        },
    )

    entrypoint = cache_structural_filing_package(
        client,
        cik="1",
        accession="0000000001-26-000001",
        primary_document="filing.htm",
        output_dir=tmp_path,
    )

    assert entrypoint.read_bytes() == b'<link href="filing.xsd"/>'


def test_package_cache_does_not_fallback_from_malformed_xbrl_zip(
    tmp_path: Path,
) -> None:
    zip_name = "0000000001-26-000001-xbrl.zip"
    client = FakeSecClient(
        index_names=[zip_name, "filing.htm", "filing.xsd"],
        attachments={
            zip_name: b"not a zip",
            "filing.htm": b'<link href="filing.xsd"/>',
            "filing.xsd": b"schema",
        },
    )

    with pytest.raises(FilingPackageIncomplete, match="invalid filing XBRL archive"):
        cache_structural_filing_package(
            client,
            cik="1",
            accession="0000000001-26-000001",
            primary_document="filing.htm",
            output_dir=tmp_path,
        )

    assert client.requested == [zip_name]


def test_package_cache_does_not_fallback_from_unsafe_xbrl_zip_member(
    tmp_path: Path,
) -> None:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("evil\\filing.xsd", "unsafe")
    zip_name = "0000000001-26-000001-xbrl.zip"
    client = FakeSecClient(
        index_names=[zip_name, "filing.htm", "filing.xsd"],
        attachments={
            zip_name: buffer.getvalue(),
            "filing.htm": b'<link href="filing.xsd"/>',
            "filing.xsd": b"schema",
        },
    )

    with pytest.raises(FilingPackageIncomplete, match="unsafe XBRL archive member"):
        cache_structural_filing_package(
            client,
            cik="1",
            accession="0000000001-26-000001",
            primary_document="filing.htm",
            output_dir=tmp_path,
        )

    assert client.requested == [zip_name]


def test_package_cache_includes_only_governed_relevant_attachments_and_cutoff_metadata(
    tmp_path: Path,
) -> None:
    client = FakeSecClient(
        index_names=[
            "filing.htm",
            "filing.xsd",
            "exhibit99-1.htm",
            "unrelated-press-release.pdf",
        ],
        attachments={
            "filing.htm": b'<link href="filing.xsd" />',
            "filing.xsd": b"schema",
            "exhibit99-1.htm": b"filed supplement",
            "unrelated-press-release.pdf": b"not governed",
        },
    )

    entrypoint = cache_structural_filing_package(
        client,
        cik="1",
        accession="0000000001-26-000001",
        primary_document="filing.htm",
        filed_date="2026-08-10",
        report_date="2026-06-30",
        relevant_attachments={"exhibit99-1.htm": "earnings_supplement"},
        output_dir=tmp_path,
    )

    manifest = json.loads((entrypoint.parent / "package-manifest.json").read_text())
    assert manifest["filed_date"] == "2026-08-10"
    assert manifest["report_date"] == "2026-06-30"
    assert manifest["relevant_attachments"] == [
        {"filename": "exhibit99-1.htm", "role": "earnings_supplement"}
    ]
    assert set(client.requested) == {"filing.htm", "filing.xsd", "exhibit99-1.htm"}
    assert not (entrypoint.parent / "unrelated-press-release.pdf").exists()


def test_package_generation_changes_when_semantic_filing_metadata_changes(
    tmp_path: Path,
) -> None:
    client = FakeSecClient(
        index_names=["filing.htm", "filing.xsd"],
        attachments={
            "filing.htm": b'<link href="filing.xsd" />',
            "filing.xsd": b"schema",
        },
    )
    first = cache_structural_filing_package(
        client,
        cik="1",
        accession="0000000001-26-000001",
        primary_document="filing.htm",
        filed_date="2026-08-10",
        report_date="2026-06-30",
        output_dir=tmp_path,
    )
    second = cache_structural_filing_package(
        client,
        cik="1",
        accession="0000000001-26-000001",
        primary_document="filing.htm",
        filed_date="2026-08-11",
        report_date="2026-06-30",
        output_dir=tmp_path,
    )

    assert first.parent != second.parent
    assert json.loads((first.parent / "package-manifest.json").read_text())["filed_date"] == "2026-08-10"
    assert json.loads((second.parent / "package-manifest.json").read_text())["filed_date"] == "2026-08-11"


def test_package_cache_downloads_only_the_matching_instance_xml(tmp_path: Path) -> None:
    client = FakeSecClient(
        index_names=[
            "fsi-20251231.htm",
            "fsi-2025.xsd",
            "fsi-2025.xml",
            "unrelated-exhibit.xml",
            "FilingSummary.xml",
        ],
        attachments={
            "fsi-20251231.htm": b'<html><link href="fsi-2025.xsd" /></html>',
            "fsi-2025.xsd": b"schema",
            "fsi-2025.xml": b"instance",
            "unrelated-exhibit.xml": b"unrelated",
            "FilingSummary.xml": b"summary",
        },
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


def test_package_cache_selects_instance_for_primary_referenced_schema_only(
    tmp_path: Path,
) -> None:
    client = FakeSecClient(
        index_names=[
            "filing.htm",
            "filing.xsd",
            "filing.xml",
            "filing_pre.xml",
            "unrelated.xsd",
            "unrelated.xml",
            "unrelated_lab.xml",
        ],
        attachments={
            "filing.htm": b'<html><link href="filing.xsd?v=1#extension" /></html>',
            "filing.xsd": b"filing schema",
            "filing.xml": b"filing instance",
            "filing_pre.xml": b"filing presentation",
            "unrelated.xsd": b"unrelated schema",
            "unrelated.xml": b"unrelated instance",
            "unrelated_lab.xml": b"required label linkbase",
        },
    )

    cache_structural_filing_package(
        client,
        cik="1",
        accession="0000000001-26-000001",
        primary_document="filing.htm",
        output_dir=tmp_path,
    )

    assert set(client.requested) == {
        "filing.htm",
        "filing.xsd",
        "filing.xml",
        "filing_pre.xml",
        "unrelated.xsd",
        "unrelated_lab.xml",
    }


def test_filing_index_uses_unpadded_cik_in_sec_archive_url(tmp_path: Path) -> None:
    class RecordingSecClient(SecClient):
        def _get_json(
            self,
            url: str,
            *,
            cache_name: str,
            refresh: bool,
            max_bytes: int | None = None,
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


def test_package_cache_recursively_closes_url_taxonomy_dependencies(
    tmp_path: Path,
) -> None:
    remote_schema = "https://xbrl.fasb.org/us-gaap/2025/us-gaap-2025.xsd"
    remote_linkbase = "https://www.xbrl.org/2025/us-gaap-2025_lab.xml"
    client = FakeSecClient(
        index_names=["fsi.htm", "fsi.xsd"],
        attachments={
            "fsi.htm": b'<link rel="schemaRef" href="fsi.xsd"/>',
            "fsi.xsd": (
                f'<xs:import schemaLocation="{remote_schema}"/>'
            ).encode(),
        },
        taxonomy_resources={
            remote_schema: (
                f'<link:linkbaseRef xlink:href="{remote_linkbase}"/>'
            ).encode(),
            remote_linkbase: b"<link:linkbase/>",
        },
    )

    entrypoint = cache_structural_filing_package(
        client,
        cik="1",
        accession="0000000001-26-000001",
        primary_document="fsi.htm",
        form="10-K/A",
        output_dir=tmp_path,
    )

    manifest = json.loads((entrypoint.parent / "package-manifest.json").read_text())
    source_urls = {item["source_url"] for item in manifest["files"]}
    assert source_urls >= {remote_schema, remote_linkbase}
    assert manifest["form"] == "10-K/A"
    assert manifest["manifest_version"] == "FINSIGHT-XBRL-PACKAGE-1"
    assert manifest["resource_count"] == 4
    assert manifest["total_bytes"] == sum(item["byte_count"] for item in manifest["files"])
    assert all((entrypoint.parent / item["local_path"]).is_file() for item in manifest["files"])
    remote_schema_record = next(
        item for item in manifest["files"] if item["source_url"] == remote_schema
    )
    assert remote_schema_record["taxonomy_version"] == "2025"
    assert remote_schema_record["taxonomy_namespace"] == ""
    assert client.requested_urls == [remote_schema, remote_linkbase]


def test_package_cache_rejects_unapproved_or_insecure_taxonomy_urls(
    tmp_path: Path,
) -> None:
    client = FakeSecClient(
        index_names=["fsi.htm", "fsi.xsd"],
        attachments={
            "fsi.htm": b'<link href="fsi.xsd"/>',
            "fsi.xsd": b'<xs:import schemaLocation="http://evil.example/taxonomy.xsd"/>',
        },
    )

    with pytest.raises(FilingPackageIncomplete, match="XBRL_URL_NOT_ALLOWED"):
        cache_structural_filing_package(
            client,
            cik="1",
            accession="0000000001-26-000001",
            primary_document="fsi.htm",
            form="10-K",
            output_dir=tmp_path,
        )


def test_package_cache_upgrades_legacy_http_url_on_governed_taxonomy_host(
    tmp_path: Path,
) -> None:
    declared_url = "http://www.xbrl.org/2003/xbrl-instance-2003-12-31.xsd"
    governed_url = "https://www.xbrl.org/2003/xbrl-instance-2003-12-31.xsd"
    client = FakeSecClient(
        index_names=["fsi.htm", "fsi.xsd"],
        attachments={
            "fsi.htm": b'<link href="fsi.xsd"/>',
            "fsi.xsd": (
                f'<xs:import schemaLocation="{declared_url}"/>'
            ).encode(),
        },
        taxonomy_resources={governed_url: b"<xs:schema/>",},
    )

    entrypoint = cache_structural_filing_package(
        client,
        cik="1",
        accession="0000000001-26-000001",
        primary_document="fsi.htm",
        output_dir=tmp_path,
    )

    manifest = json.loads((entrypoint.parent / "package-manifest.json").read_text())
    assert client.requested_urls == [governed_url]
    assert governed_url in {item["source_url"] for item in manifest["files"]}
    assert declared_url not in {item["source_url"] for item in manifest["files"]}


@pytest.mark.parametrize(
    "url",
    (
        "https://www.xbrl.org:444/taxonomy.xsd",
        "https://www.xbrl.org:not-a-port/taxonomy.xsd",
    ),
)
def test_taxonomy_url_rejects_nondefault_or_malformed_https_ports(url: str) -> None:
    with pytest.raises(ValueError, match="governed host and default port"):
        validate_taxonomy_url(url)


def test_legacy_taxonomy_url_leaves_malformed_http_port_for_governed_rejection() -> None:
    url = "http://www.xbrl.org:not-a-port/taxonomy.xsd"

    assert canonicalize_legacy_taxonomy_url(url) == url


@pytest.mark.parametrize(
    "limits,code",
    [
        ({"max_resource_count": 1}, "XBRL_RESOURCE_COUNT_LIMIT"),
        ({"max_file_bytes": 5}, "XBRL_FILE_SIZE_LIMIT"),
        ({"max_total_bytes": 10}, "XBRL_PACKAGE_SIZE_LIMIT"),
    ],
)
def test_package_acquisition_fails_closed_at_governed_limits(
    tmp_path: Path,
    limits: dict[str, int],
    code: str,
) -> None:
    client = FakeSecClient(
        index_names=["fsi.htm", "fsi.xsd"],
        attachments={
            "fsi.htm": b'<link href="fsi.xsd"/>',
            "fsi.xsd": b"1234567890",
        },
    )

    with pytest.raises(FilingPackageIncomplete, match=code):
        cache_structural_filing_package(
            client,
            cik="1",
            accession="0000000001-26-000001",
            primary_document="fsi.htm",
            form="10-K",
            output_dir=tmp_path,
            **limits,
        )

    assert not list(tmp_path.rglob("package-manifest.json"))


def test_package_publication_uses_fresh_content_addressed_generations(
    tmp_path: Path,
) -> None:
    client = FakeSecClient(
        index_names=["fsi.htm", "fsi.xsd"],
        attachments={
            "fsi.htm": b'<link href="fsi.xsd"/>',
            "fsi.xsd": b"first",
        },
    )
    first = cache_structural_filing_package(
        client,
        cik="1",
        accession="0000000001-26-000001",
        primary_document="fsi.htm",
        form="10-Q",
        output_dir=tmp_path,
    )
    (first.parent / "stale.xml").write_text("stale")
    client.attachments["fsi.xsd"] = b"second"

    second = cache_structural_filing_package(
        client,
        cik="1",
        accession="0000000001-26-000001",
        primary_document="fsi.htm",
        form="10-Q",
        output_dir=tmp_path,
        refresh=True,
    )

    assert first.parent != second.parent
    assert not (second.parent / "stale.xml").exists()
    assert second.parent.name == json.loads(
        (second.parent / "package-manifest.json").read_text()
    )["generation"]


def test_package_refuses_tampered_existing_immutable_generation(tmp_path: Path) -> None:
    client = FakeSecClient(index_names=["fsi.htm"])
    entrypoint = cache_structural_filing_package(
        client,
        cik="1",
        accession="0000000001-26-000001",
        primary_document="fsi.htm",
        form="10-K",
        output_dir=tmp_path,
    )
    entrypoint.write_bytes(b"tampered")

    with pytest.raises(FilingPackageIncomplete, match="XBRL_IMMUTABLE_CONFLICT"):
        cache_structural_filing_package(
            client,
            cik="1",
            accession="0000000001-26-000001",
            primary_document="fsi.htm",
            form="10-K",
            output_dir=tmp_path,
        )


def test_sec_taxonomy_fetch_rejects_redirect_outside_governed_hosts(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, size: int = -1) -> bytes:
            return b"schema" if size != 0 else b""

        def geturl(self) -> str:
            return "https://evil.example/redirected.xsd"

    class FakeOpener:
        def open(self, *args: object, **kwargs: object) -> Response:
            return Response()

    monkeypatch.setattr(
        "app.us_valuation.sec_client.build_opener",
        lambda *args, **kwargs: FakeOpener(),
    )
    client = SecClient(
        user_agent="FinSight contact@example.com",
        cache_dir=tmp_path,
        max_retries=0,
    )

    with pytest.raises(RuntimeError, match="redirect"):
        client.taxonomy_resource(
            "https://xbrl.fasb.org/us-gaap/2025/us-gaap-2025.xsd",
            max_bytes=1024,
        )


def test_sec_taxonomy_redirect_is_rejected_before_following_unsafe_location(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    unsafe_request_made = False

    class Response:
        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, size: int = -1) -> bytes:
            return b"schema" if size != 0 else b""

        def geturl(self) -> str:
            return "https://evil.example/redirected.xsd"

    def fake_urlopen(*args: object, **kwargs: object) -> Response:
        nonlocal unsafe_request_made
        unsafe_request_made = True
        return Response()

    def fake_base_redirect(
        self: HTTPRedirectHandler,
        request: Request,
        fp: object,
        code: int,
        msg: str,
        headers: object,
        newurl: str,
    ) -> Request:
        nonlocal unsafe_request_made
        unsafe_request_made = True
        return Request(newurl)

    class FakeOpener:
        def __init__(self, handler: HTTPRedirectHandler) -> None:
            self.handler = handler

        def open(self, request: Request, *, timeout: int) -> Response:
            self.handler.redirect_request(
                request,
                None,
                302,
                "Found",
                {},
                "https://evil.example/redirected.xsd",
            )
            return Response()

    monkeypatch.setattr("app.us_valuation.sec_client.urlopen", fake_urlopen)
    monkeypatch.setattr(
        "app.us_valuation.sec_client.build_opener",
        lambda handler: FakeOpener(handler),
        raising=False,
    )
    monkeypatch.setattr(HTTPRedirectHandler, "redirect_request", fake_base_redirect)
    client = SecClient(
        user_agent="FinSight contact@example.com",
        cache_dir=tmp_path,
        max_retries=0,
    )

    with pytest.raises(RuntimeError, match="redirect"):
        client.taxonomy_resource(
            "https://xbrl.fasb.org/us-gaap/2025/us-gaap-2025.xsd",
            max_bytes=1024,
        )

    assert unsafe_request_made is False


def test_sec_filing_index_response_is_bounded_before_cache_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    body = json.dumps({"padding": "x" * (2 * 1024 * 1024)}).encode()

    class Response:
        def __init__(self) -> None:
            self.offset = 0

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, size: int = -1) -> bytes:
            if self.offset >= len(body):
                return b""
            if size < 0:
                size = len(body) - self.offset
            chunk = body[self.offset : self.offset + size]
            self.offset += len(chunk)
            return chunk

    monkeypatch.setattr(
        "app.us_valuation.sec_client.urlopen", lambda *args, **kwargs: Response()
    )
    client = SecClient(
        user_agent="FinSight contact@example.com",
        cache_dir=tmp_path,
        max_retries=0,
    )

    with pytest.raises(RuntimeError, match="byte limit"):
        client.filing_index("1", "0000000001-26-000001")

    assert not list(tmp_path.rglob("index.json"))


def test_sec_filing_attachment_stream_is_bounded_before_cache_write(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class Response:
        chunks = iter((b"1234", b"5678", b""))

        def __enter__(self) -> "Response":
            return self

        def __exit__(self, *args: object) -> None:
            return None

        def read(self, size: int = -1) -> bytes:
            return next(self.chunks)

    monkeypatch.setattr("app.us_valuation.sec_client.urlopen", lambda *args, **kwargs: Response())
    client = SecClient(
        user_agent="FinSight contact@example.com",
        cache_dir=tmp_path,
        max_retries=0,
    )

    with pytest.raises(RuntimeError, match="byte limit"):
        client.filing_attachment(
            "1",
            "0000000001-26-000001",
            "fsi.xsd",
            max_bytes=5,
        )

    assert not list(tmp_path.rglob("fsi.xsd"))

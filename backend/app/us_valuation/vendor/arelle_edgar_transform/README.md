# Arelle SEC Inline Transforms

This directory contains the runtime-only `transform` plugin from the official
[`Arelle/EDGAR`](https://github.com/Arelle/EDGAR) repository, pinned at commit
`72033f579e89ab47e882437b5d4ceed9c7656ed5` (retrieved 2026-08-11).

Included upstream files:

- `transform/__init__.py` — SHA-256
  `2296586f945ffd95ab37d3d4147c4e45f42ce4e5f397f61143e053208adefbf1`
- `transform/text2num.py` — SHA-256
  `6c9b26354320a2fb34fe380cdc71ff7f8d1cc712811e6b10c661e512f0383409`
- repository `LICENSE`
- Arelle 2.44.0 `COPYRIGHT.md`

License provenance is intentionally explicit because the upstream files carry
several notices:

- the EDGAR repository distributes its work under the included CC0 license;
- the transform module identifies SEC employee work as U.S. government work
  and declares `Apache-2` in its Arelle plugin metadata;
- `text2num.py` embeds its complete MIT notice and Greg Hewgill copyright;
- the transform module imports Arelle and refers to Arelle's `COPYRIGHT.md`, so
  the matching Arelle 2.44.0 copyright notice is included here.

The EDGAR test registry, shell scripts, XSL, and bundled Saxon JAR are omitted
because FinSight only loads the Python transformation hook at runtime. Update
these files only after compatibility tests against the pinned Arelle version
and real SEC Inline XBRL filings pass.

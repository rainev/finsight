---
name: sec-xbrl-zip-is-a-package-source
description: Treat the official SEC XBRL ZIP as the complete package and detect split Inline XBRL pages before declaring a filing empty.
metadata: { type: gotcha }
---
# SEC XBRL ZIP is a package source

Some SEC filing-directory indexes expose only the filing index, complete-submission text, and an official `*-xbrl.zip`; the primary Inline XBRL document may still be addressable directly while its referenced schema/linkbases exist only inside that ZIP. Treating absent individual index entries as missing creates false package failures.

Durable rule: safely open the official XBRL ZIP with entry-count, uncompressed-size, file-size, duplicate-basename, and path controls. Preserve both the ZIP source URL and logical member URL/name in the immutable manifest, hash every extracted member, and keep dependency resolution bound to the logical filing URL.

**Why:** Clorox's 2026 10-K primary page contained only two DEI cover facts, while the linked
`clx-20260630_d2.htm` member contained the financial statements. Parsing only the declared primary
looked like a current-period data failure even though the official ZIP was complete.

**How to detect / apply:** when a primary Inline XBRL page has implausibly few numeric facts, scan
same-filing HTML links and official ZIP members for additional Inline XBRL pages. Parse them as one
document set with the primary contexts/resources, hash every input and the deterministic composition,
and preserve the exact accession/period/unit gates. After extraction, reconcile commercial paper,
long-term debt, finance leases, supplier finance, and operating leases separately; more facts do not
prove the bridge is complete. See [[financing-claims-reconcile-to-statement-totals]].

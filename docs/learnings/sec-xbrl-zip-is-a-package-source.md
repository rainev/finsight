# SEC XBRL ZIP is a package source

Some SEC filing-directory indexes expose only the filing index, complete-submission text, and an official `*-xbrl.zip`; the primary Inline XBRL document may still be addressable directly while its referenced schema/linkbases exist only inside that ZIP. Treating absent individual index entries as missing creates false package failures.

Durable rule: safely open the official XBRL ZIP with entry-count, uncompressed-size, file-size, duplicate-basename, and path controls. Preserve both the ZIP source URL and logical member URL/name in the immutable manifest, hash every extracted member, and keep dependency resolution bound to the logical filing URL.

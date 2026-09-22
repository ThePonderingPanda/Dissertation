# -*- coding: utf-8 -*-
"""Confirm what the two collision runs actually stored."""
import sqlite3, zlib
E = "/home/student/dissertation/experiments/collision/"
for label, db in [("E2a, unmodified pipeline (three-hash match)", "e2a.db"),
                  ("E2c, fault injected (MD5-only match)", "e2c.db")]:
    con = sqlite3.connect("file:%s%s?mode=ro" % (E, db), uri=True)
    print("=" * 74)
    print(label)
    print("=" * 74)
    rows = con.execute("SELECT id, size, md5, sha256 FROM content_store ORDER BY id").fetchall()
    print("  contents stored : %d" % len(rows))
    print("  refs stored     : %d" % con.execute("SELECT COUNT(*) FROM file_refs").fetchone()[0])
    for cid, size, md5, sha in rows:
        blob = con.execute("SELECT compressed_content FROM content_store WHERE id=?", (cid,)).fetchone()[0]
        data = zlib.decompress(blob)
        paths = [r[0] for r in con.execute("SELECT path FROM file_refs WHERE content_id=?", (cid,))]
        print("   id=%d %d B  md5=%s" % (cid, size, md5))
        print("        sha256=%s" % sha)
        print("        stored bytes start: %s" % data[:16].hex())
        print("        paths: %s" % ", ".join(paths))
    if len(rows) == 2:
        a = zlib.decompress(con.execute("SELECT compressed_content FROM content_store WHERE id=1").fetchone()[0])
        b = zlib.decompress(con.execute("SELECT compressed_content FROM content_store WHERE id=2").fetchone()[0])
        print("  the two stored contents are %s"
              % ("IDENTICAL (data lost!)" if a == b else "different (both preserved)"))
        print("  bytes differing between them: %d" % sum(1 for x, y in zip(a, b) if x != y))
    con.close()
    print()

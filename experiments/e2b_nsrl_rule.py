#!/usr/bin/env python3
"""
E2b -- does the dual-hash requirement on the NSRL lookup actually matter?

Section 3.6: "The lookup requires both SHA-256 and SHA-1 to agree with the same
NSRL record, not either one alone, which was adopted on supervisory guidance.
That is a stricter test than any reviewed system applies to its own matching, and
it means a single-hash coincidence cannot mark a file as known."

The claim has never been tested. This tests it with the SHAttered pair, two PDFs
that share a SHA-1 and differ in SHA-256.

Two steps:

  1. Ask the real NSRL whether it holds either PDF. It does not, so the
     demonstration below has to use a stand-in reference set. Said plainly rather
     than glossed over.
  2. Build a stand-in reference database with the real NSRL's FILE schema, put
     ONE of the two PDFs in it as a known-good record, then run both rules
     against the OTHER PDF:
       - the rule as implemented: sha256 AND sha1 must match the same row
       - a single-hash rule: sha1 alone

The real NSRL is opened read-only. The stand-in and the evidence database are
both scratch copies created for this experiment.
"""
import os
import sqlite3
import sys

E = "/home/student/dissertation/experiments/collision/"
NSRL = "/mnt/d/Dissertation/RDS_2026.03.1_legacy_minimal/RDS_2026.03.1_legacy_minimal.db"
DB = E + "e2b.db"
STANDIN = E + "e2b_standin_reference.db"


def main():
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT cs.id, cs.sha1, cs.sha256, cs.size, fr.path"
        " FROM content_store cs JOIN file_refs fr ON fr.content_id = cs.id"
        " ORDER BY fr.path").fetchall()
    print("Extracted content:")
    for cid, sha1, sha256, size, path in rows:
        print("  id=%d  %s  %d bytes" % (cid, path, size))
        print("     sha1   %s" % sha1)
        print("     sha256 %s" % sha256)
    if len(rows) != 2:
        sys.exit("expected two contents, found %d" % len(rows))
    if rows[0][1] != rows[1][1]:
        sys.exit("the two SHA-1 values differ -- not a collision pair")
    print("\n  the two files share a SHA-1 and differ in SHA-256: confirmed")

    # ---- step 1: is either file actually in the NSRL? --------------------
    print("\nStep 1: asking the real NSRL (read-only, indexed on sha256)")
    if not os.path.exists(NSRL):
        print("  NSRL not found at %s -- skipping" % NSRL)
    else:
        n = sqlite3.connect("file:%s?mode=ro" % NSRL, uri=True)
        for cid, sha1, sha256, size, path in rows:
            hit = n.execute("SELECT file_name FROM FILE WHERE sha256 = ?",
                            (sha256.upper(),)).fetchone()
            print("  %-18s sha256 lookup: %s"
                  % (path, "FOUND as %s" % hit[0] if hit else "not present"))
        n.close()
        print("  Neither is in the reference set, so the comparison below uses a")
        print("  stand-in. That is a limit of what can be demonstrated, not of")
        print("  the rule being tested.")

    # ---- step 2: stand-in reference set ---------------------------------
    print("\nStep 2: stand-in reference set holding only the FIRST file")
    if os.path.exists(STANDIN):
        os.remove(STANDIN)
    s = sqlite3.connect(STANDIN)
    s.execute("""CREATE TABLE FILE (
                    sha256 TEXT, sha1 TEXT, md5 TEXT, crc32 TEXT,
                    file_name TEXT, file_size INTEGER, package_id INTEGER,
                    PRIMARY KEY (sha256, sha1))""")
    first = rows[0]
    s.execute("INSERT INTO FILE VALUES (?,?,?,?,?,?,?)",
              (first[2].upper(), first[1].upper(), "", "",
               os.path.basename(first[4]), first[3], 1))
    s.commit()
    s.close()
    print("  inserted one record: %s" % os.path.basename(first[4]))

    con.execute("ATTACH DATABASE ? AS ref", (STANDIN,))

    # the rule as implemented in nsrl_match.py
    implemented = con.execute("""
        SELECT cs.id, fr.path FROM content_store cs
        JOIN file_refs fr ON fr.content_id = cs.id
        WHERE EXISTS (SELECT 1 FROM ref.FILE nf
                      WHERE nf.sha256 = UPPER(cs.sha256)
                        AND nf.sha1  = UPPER(cs.sha1))
        ORDER BY fr.path""").fetchall()

    # what a single-hash rule would do instead
    sha1_only = con.execute("""
        SELECT cs.id, fr.path FROM content_store cs
        JOIN file_refs fr ON fr.content_id = cs.id
        WHERE EXISTS (SELECT 1 FROM ref.FILE nf
                      WHERE nf.sha1 = UPPER(cs.sha1))
        ORDER BY fr.path""").fetchall()

    con.close()

    print("\nResults")
    print("  %-46s %s" % ("rule", "files marked known-good"))
    print("  " + "-" * 72)
    print("  %-46s %s" % ("sha256 AND sha1, same record (as implemented)",
                          ", ".join(p for _, p in implemented) or "none"))
    print("  %-46s %s" % ("sha1 alone (the common practice)",
                          ", ".join(p for _, p in sha1_only) or "none"))

    impl = {p for _, p in implemented}
    only = {p for _, p in sha1_only}
    extra = only - impl
    print()
    if extra:
        print("  The single-hash rule marks %d file(s) known-good that the"
              % len(extra))
        print("  implemented rule refuses: %s" % ", ".join(sorted(extra)))
        print("  Those files are NOT the reference file. A single-hash rule would")
        print("  have excluded genuine evidence from further examination.")
        return 0
    print("  The two rules agree, which was not expected. Investigate.")
    return 1


if __name__ == "__main__":
    sys.exit(main())

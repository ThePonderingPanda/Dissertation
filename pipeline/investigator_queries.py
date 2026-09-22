"""
investigator_queries.py

Demonstrates the query interface as a set of realistic investigator
questions run against the real evidence database -- not a general-purpose
tool, a Results-chapter demonstration that the schema actually supports
the kinds of questions an investigator would ask (this doubles as
evidence for the schema-design sub-question).

Attaches vt_results.db so VirusTotal findings can be joined in by
sha256 -- VT results were never written back into content_store's
known_malicious column (that column predates VT and was scoped for
the now-superseded EMBER check), so this keeps the two sources
separate and joins them live rather than migrating old data.

Usage:
  python3 -u investigator_queries.py | tee investigator_queries.log
"""
import sqlite3

DB_PATH = "/mnt/d/Dissertation/dedup.db"
VT_DB_PATH = "/home/student/dissertation/vt_results.db"


def run(cur, title, sql, params=()):
    print(f"\n=== {title} ===")
    cur.execute(sql, params)
    rows = cur.fetchall()
    if not rows:
        print("  (no results)")
        return
    cols = [d[0] for d in cur.description]
    print("  " + " | ".join(cols))
    for row in rows:
        print("  " + " | ".join(str(v) for v in row))
    print(f"  ({len(rows)} row(s))")


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(f"ATTACH DATABASE '{VT_DB_PATH}' AS vt")
    cur = conn.cursor()

    # Q1: "Show all files flagged malicious"
    run(cur, "Files flagged malicious (VirusTotal)", """
        SELECT cs.sha256, cs.size, vr.malicious_count, vr.total_engines,
               GROUP_CONCAT(fr.path, ' | ') AS paths
        FROM content_store cs
        JOIN vt.vt_results vr ON vr.sha256 = cs.sha256
        JOIN file_refs fr ON fr.content_id = cs.id
        WHERE vr.status = 'malicious'
        GROUP BY cs.id
    """)

    # Q2: "Which files are duplicates and where else do they appear"
    run(cur, "Duplicate files and their other locations", """
        SELECT cs.id, cs.size, COUNT(fr.id) AS occurrences,
               GROUP_CONCAT(fr.path, ' | ') AS paths
        FROM content_store cs
        JOIN file_refs fr ON fr.content_id = cs.id
        GROUP BY cs.id
        HAVING COUNT(fr.id) > 1
        ORDER BY occurrences DESC
        LIMIT 20
    """)

    # Q3: "How much storage did this case actually save"
    print("\n=== Storage saved (dedup + compression combined) ===")
    cur.execute("""
        SELECT
            (SELECT COUNT(*) FROM file_refs) AS total_refs,
            (SELECT COUNT(*) FROM content_store) AS unique_stored,
            (SELECT SUM(cs.size) FROM content_store cs
             JOIN file_refs fr ON fr.content_id = cs.id) AS naive_bytes,
            (SELECT SUM(LENGTH(compressed_content)) FROM content_store) AS actual_bytes
    """)
    total_refs, unique_stored, naive_bytes, actual_bytes = cur.fetchone()
    saved_pct = (1 - actual_bytes / naive_bytes) * 100 if naive_bytes else 0
    print(f"  Total file references (incl. duplicates): {total_refs}")
    print(f"  Unique files actually stored: {unique_stored}")
    print(f"  Naive size if every reference stored separately, uncompressed: {naive_bytes:,} bytes")
    print(f"  Actual bytes stored (deduped + compressed): {actual_bytes:,} bytes")
    print(f"  Total space saved: {saved_pct:.1f}%")

    conn.close()


if __name__ == "__main__":
    main()

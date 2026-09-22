"""
nsrl_match.py

Matches every unique file in content_store against the NSRL RDSv3
database on SHA-1 AND SHA-256 together (per your supervisor's
guidance -- both hashes must agree with the same NSRL record, not
just one in isolation). Anything that matches neither is exported as
a plain SHA-256 list, one hash per line, ready to feed straight into
check_virustotal.py.

Schema confirmed directly from your real file's
RDS_2026.03.1_modern_minimal.schema.sql: a FILE table with lowercase
columns (sha256, sha1, md5, crc32, file_name, file_size, package_id),
primary-keyed starting with (sha256, sha1, ...). There's also a
DISTINCT_HASH view, but it's built with SELECT DISTINCT over the
whole FILE table -- and since your file is 181GB, recomputing that
distinct set on every query would be painfully slow (views aren't
cached in SQLite). We don't need distinctness for a simple "does this
hash exist" check, so this queries the FILE table directly instead,
which uses its primary key index for a fast lookup.

DB_PATH and NSRL_DB_PATH are now required CLI arguments rather than
hardcoded here -- pass them each time you run this script.
"""
import sqlite3
import sys

NSRL_TABLE = "FILE"
NSRL_SHA1_COL = "sha1"
NSRL_SHA256_COL = "sha256"

CONTENT_TABLE = "content_store"
ID_COL = "id"
SHA1_COL = "sha1"                        # created by backfill_sha1.py -- run that first
SHA256_COL = "sha256"


def main():
    if len(sys.argv) != 3:
        print(f"Usage: python3 {sys.argv[0]} <db_path> <nsrl_db_path>")
        sys.exit(1)
    db_path = sys.argv[1]
    nsrl_db_path = sys.argv[2]

    output_hashes_file = "non_nsrl_hashes_" + db_path.split("/")[-1].replace(".db", "") + ".txt"

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    print(f"Attaching NSRL database: {nsrl_db_path}")
    cur.execute(f"ATTACH DATABASE '{nsrl_db_path}' AS nsrl")

    # Index your own hash columns -- the NSRL side should already be
    # indexed for lookups, but yours almost certainly isn't yet, and
    # this join will crawl without one.
    print("Indexing local sha1/sha256 columns...")
    cur.execute(f"""
        CREATE INDEX IF NOT EXISTS idx_content_hashes
        ON {CONTENT_TABLE} ({SHA1_COL}, {SHA256_COL})
    """)
    conn.commit()

    cur.execute(f"SELECT COUNT(*) FROM {CONTENT_TABLE}")
    total = cur.fetchone()[0]
    print(f"{total} unique files to check against NSRL.")

    # content_store already has an nsrl_known column from earlier planning --
    # using it directly rather than adding a second, redundant one.
    # EXISTS against the raw FILE table uses its primary key index
    # (which starts with sha256, sha1) for a fast per-row lookup --
    # no need to materialize the DISTINCT_HASH view first.
    print("Running the match (index-backed lookup, should be quick "
          "despite the NSRL file's size)...")
    cur.execute(f"""
        UPDATE {CONTENT_TABLE}
        SET nsrl_known = 1
        WHERE EXISTS (
            SELECT 1
            FROM nsrl.{NSRL_TABLE} nf
            WHERE nf.{NSRL_SHA256_COL} = UPPER({CONTENT_TABLE}.{SHA256_COL})
              AND nf.{NSRL_SHA1_COL} = UPPER({CONTENT_TABLE}.{SHA1_COL})
        )
    """)
    conn.commit()

    cur.execute(f"SELECT COUNT(*) FROM {CONTENT_TABLE} WHERE nsrl_known = 1")
    matched = cur.fetchone()[0]
    unmatched = total - matched
    print(f"Matched (known-good, in NSRL): {matched}")
    print(f"Not matched (unknown -- VirusTotal candidates): {unmatched}")

    print(f"Writing unmatched SHA-256 hashes to {output_hashes_file}...")
    cur.execute(f"""
        SELECT {SHA256_COL} FROM {CONTENT_TABLE}
        WHERE nsrl_known IS NULL OR nsrl_known = 0
    """)
    with open(output_hashes_file, "w") as f:
        for (sha256,) in cur.fetchall():
            f.write(sha256 + "\n")

    conn.close()
    print(f"Done. {unmatched} hashes written to {output_hashes_file} -- "
          f"feed this straight into check_virustotal.py next.")


if __name__ == "__main__":
    main()

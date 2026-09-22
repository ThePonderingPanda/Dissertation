"""
backfill_sha1.py

Adds a SHA-1 hash for every already-stored piece of content, without
touching the disk image again. Per your supervisor's guidance, NSRL
matching should compare SHA-1 and SHA-256 together -- and SHA-1 was
never computed in the original hashing pass (only MD5, SHA-256,
SHA-512), so this backfills it retroactively.

Why this is safe and cheap: content_store already holds the full,
zlib-compressed original bytes of every unique file. Decompressing
that and hashing the result gives the exact same SHA-1 you'd get from
re-reading the disk image -- there's no need to re-run extraction,
re-mount the image, or touch anything already verified in Steps A-E.

ADJUST THESE THREE to match your actual schema before running --
I don't have your exact column names in front of me, only the
general shape of the table from the walk-through. DB_PATH is now
a required CLI argument instead of hardcoded here.
"""
import sqlite3
import sys
import zlib
import hashlib

TABLE = "content_store"
ID_COL = "id"
BLOB_COL = "compressed_content"


def main():
    if len(sys.argv) != 2:
        print(f"Usage: python3 {sys.argv[0]} <db_path>")
        sys.exit(1)
    db_path = sys.argv[1]

    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Add the column if it doesn't already exist
    try:
        cur.execute(f"ALTER TABLE {TABLE} ADD COLUMN sha1 TEXT")
        conn.commit()
        print("Added sha1 column.")
    except sqlite3.OperationalError:
        print("sha1 column already exists, continuing.")

    cur.execute(f"SELECT {ID_COL}, {BLOB_COL} FROM {TABLE} WHERE sha1 IS NULL")
    rows = cur.fetchall()
    print(f"{len(rows)} rows need a SHA-1 backfilled.")

    update_cur = conn.cursor()
    for i, (row_id, compressed) in enumerate(rows, 1):
        data = zlib.decompress(compressed)
        sha1 = hashlib.sha1(data).hexdigest()
        update_cur.execute(
            f"UPDATE {TABLE} SET sha1 = ? WHERE {ID_COL} = ?",
            (sha1, row_id),
        )
        if i % 500 == 0:
            conn.commit()
            print(f"  [{i}/{len(rows)}] committed")

    conn.commit()
    conn.close()
    print(f"Done. {len(rows)} rows backfilled with SHA-1.")


if __name__ == "__main__":
    main()

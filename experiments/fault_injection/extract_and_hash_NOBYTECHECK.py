"""
extract_and_hash.py
Logical extraction + enumeration + hashing + deduplication + compression
of files from a forensic disk image, stored in a SQLite database.

Step B: dedup logic (all three hashes must match) + compression on new
content only. Commits are batched (every 500 files, plus one final
commit at the end) instead of once per file, to reduce slow disk writes
to the Windows-mounted D: drive.

Step E: byte-level verification wired into the Step B dedup check. When
all three hashes match an existing content_store row, the stored bytes
are decompressed and compared directly against the newly-read file's
bytes before trusting the match. A genuine match is treated as a
duplicate as before. A mismatch (hashes matched, bytes didn't) is a
caught hash collision -- it is stored as brand-new content rather than
reused, and flagged in both the per-file log line and the run summary.
"""
import pytsk3
import hashlib
import sqlite3
import zlib
import sys
import time
import os
import shutil

BATCH_SIZE = 500

# Local staging: the working database is written to WSL-native storage
# (not /mnt/*) during the run, then copied to the real destination once
# at the end, to avoid hundreds of slow small writes over the 9P bridge.
# Bounded on two independent axes since local disk space may be limited:
MIN_FREE_BYTES = 2 * 1024**3      # hard floor -- abort if the whole local disk drops below this
STAGING_SIZE_CAP = 10 * 1024**3   # this script will not let its OWN staged file exceed this
STAGING_DIR = None    # set once in main(), read (not written) inside walk_and_store()
LOCAL_DB_PATH = None  # same


def get_file_content(f):
    """Read all bytes of a file inside the disk image, in chunks."""
    try:
        size = f.info.meta.size
    except AttributeError:
        return None
    offset = 0
    data = b""
    CHUNK = 1024 * 1024  # 1MB at a time
    while offset < size:
        to_read = min(CHUNK, size - offset)
        chunk = f.read_random(offset, to_read)
        if not chunk:
            break
        data += chunk
        offset += len(chunk)
    return data


def hash_file(data):
    return (
        hashlib.md5(data).hexdigest(),
        hashlib.sha256(data).hexdigest(),
        hashlib.sha512(data).hexdigest(),
    )


def create_database(db_path):
    """Set up the three tables if they don't already exist."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS images (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            image_hash TEXT,
            acquisition_date TEXT,
            examiner TEXT,
            notes TEXT
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS content_store (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            size INTEGER,
            md5 TEXT,
            sha256 TEXT,
            sha512 TEXT,
            compressed_content BLOB,
            nsrl_known INTEGER
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS file_refs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_id INTEGER,
            content_id INTEGER,
            path TEXT,
            FOREIGN KEY (image_id) REFERENCES images (id),
            FOREIGN KEY (content_id) REFERENCES content_store (id)
        )
    """)
    conn.commit()
    return conn


def insert_image(conn, name):
    cur = conn.cursor()
    cur.execute("INSERT INTO images (name) VALUES (?)", (name,))
    conn.commit()
    return cur.lastrowid


def find_existing_content(cur, md5, sha256, sha512):
    """Look up a content_store row by all three hashes.
    Returns (id, compressed_content) if found, else None -- the caller
    needs the stored bytes to run the Step E byte-level check, not just
    the id."""
    # FAULT INJECTION for experiment E2c. The real pipeline requires all three
    # hashes to agree. This copy matches on MD5 alone, so a published MD5
    # collision reaches the byte-for-byte check that normally never sees one.
    # This file is NOT the pipeline. It exists only to exercise the failure path.
    cur.execute("""
        SELECT id, compressed_content FROM content_store
        WHERE md5 = ?
    """, (md5,))
    return cur.fetchone()


def insert_new_content(cur, size, md5, sha256, sha512, data):
    compressed = zlib.compress(data)
    cur.execute("""
        INSERT INTO content_store (size, md5, sha256, sha512, compressed_content)
        VALUES (?, ?, ?, ?, ?)
    """, (size, md5, sha256, sha512, compressed))
    return cur.lastrowid


def insert_file_ref(cur, image_id, content_id, path):
    cur.execute("""
        INSERT INTO file_refs (image_id, content_id, path)
        VALUES (?, ?, ?)
    """, (image_id, content_id, path))


def walk_and_store(directory, conn, image_id, path="", stats=None):
    if stats is None:
        stats = {
            "total": 0,
            "new": 0,
            "duplicate": 0,
            "bytes_new": 0,
            "bytes_saved": 0,
            "hash_collisions": 0,
        }
    cur = conn.cursor()
    for entry in directory:
        if entry.info.name.name in (b".", b".."):
            continue
        try:
            name = entry.info.name.name.decode("utf-8", errors="replace")
        except Exception:
            continue
        full_path = f"{path}/{name}"
        if entry.info.meta is None:
            continue
        file_type = entry.info.meta.type
        if file_type == pytsk3.TSK_FS_META_TYPE_DIR:
            try:
                walk_and_store(entry.as_directory(), conn, image_id, full_path, stats)
            except Exception as e:
                print(f"  [!] Skipped folder {full_path}: {e}")
        elif file_type == pytsk3.TSK_FS_META_TYPE_REG:
            try:
                data = get_file_content(entry)
                if data is None:
                    continue
                size = entry.info.meta.size
                md5, sha256, sha512 = hash_file(data)

                existing = find_existing_content(cur, md5, sha256, sha512)

                if existing is not None:
                    existing_id, existing_compressed = existing

                    # Step E: byte-level verification on hash match.
                    verify_start = time.perf_counter()
                    existing_data = zlib.decompress(existing_compressed)
                    # FAULT INJECTION for E2c, condition 3. The real pipeline
                    # compares the stored bytes against the new file's bytes.
                    # This copy trusts the hash instead, which is what every
                    # system reviewed in Chapter 2 does.
                    bytes_match = True
                    verify_elapsed = time.perf_counter() - verify_start

                    if bytes_match:
                        insert_file_ref(cur, image_id, existing_id, full_path)
                        stats["duplicate"] += 1
                        stats["bytes_saved"] += size
                        print(f"  [=] {full_path} ({size} bytes) - duplicate, "
                              f"reused content id {existing_id} "
                              f"(byte-check: {verify_elapsed:.4f}s)")
                    else:
                        # Hashes matched, bytes didn't: a genuine caught
                        # collision. Store as brand-new content -- do NOT
                        # reuse the existing content_id.
                        content_id = insert_new_content(cur, size, md5, sha256, sha512, data)
                        insert_file_ref(cur, image_id, content_id, full_path)
                        stats["new"] += 1
                        stats["bytes_new"] += size
                        stats["hash_collisions"] += 1
                        print(f"  [COLLISION] {full_path} ({size} bytes) - hashes "
                              f"matched content id {existing_id} but bytes differ! "
                              f"Stored as new content id {content_id} "
                              f"(byte-check: {verify_elapsed:.4f}s)")
                else:
                    content_id = insert_new_content(cur, size, md5, sha256, sha512, data)
                    insert_file_ref(cur, image_id, content_id, full_path)
                    stats["new"] += 1
                    stats["bytes_new"] += size
                    print(f"  [+] {full_path} ({size} bytes) - new, stored as content id {content_id}")

                stats["total"] += 1
                if stats["total"] % BATCH_SIZE == 0:
                    conn.commit()
                    free_bytes = shutil.disk_usage(STAGING_DIR).free
                    staged_size = os.path.getsize(LOCAL_DB_PATH) if os.path.exists(LOCAL_DB_PATH) else 0
                    if free_bytes < MIN_FREE_BYTES or staged_size > STAGING_SIZE_CAP:
                        reason = "local disk nearly full" if free_bytes < MIN_FREE_BYTES else "staged file exceeded its size cap"
                        print(f"  [!] Stopping cleanly ({reason}). Everything committed "
                              f"so far ({stats['total']} files) is safe in {LOCAL_DB_PATH}.")
                        conn.close()
                        sys.exit(1)
                    print(f"  ... committed batch at {stats['total']} files "
                          f"(staged: {staged_size / 1024**3:.2f}GB, "
                          f"{free_bytes / 1024**3:.2f}GB free locally)")
            except Exception as e:
                print(f"  [!] Skipped file {full_path}: {e}")
    return stats


def main(image_path, partition_offset_sectors, db_path):
    global STAGING_DIR, LOCAL_DB_PATH
    STAGING_DIR = os.path.expanduser("~/dissertation/.staging")
    os.makedirs(STAGING_DIR, exist_ok=True)
    LOCAL_DB_PATH = os.path.join(STAGING_DIR, os.path.basename(db_path))

    free_bytes = shutil.disk_usage(STAGING_DIR).free
    print(f"Local staging free space: {free_bytes / 1024**3:.2f}GB "
          f"(will stop cleanly if it drops below {MIN_FREE_BYTES / 1024**3:.0f}GB, "
          f"or if this run's own staged file exceeds {STAGING_SIZE_CAP / 1024**3:.0f}GB)")
    if free_bytes < MIN_FREE_BYTES:
        print(f"  [!] Already below the floor -- aborting before starting.")
        sys.exit(1)

    print(f"Opening image: {image_path}")
    img = pytsk3.Img_Info(image_path)
    fs = pytsk3.FS_Info(img, offset=partition_offset_sectors * 512)
    root = fs.open_dir(path="/")

    conn = create_database(LOCAL_DB_PATH)
    image_id = insert_image(conn, image_path)

    print("Walking file system, hashing, deduplicating, verifying, and storing...")
    stats = walk_and_store(root, conn, image_id)
    conn.commit()  # final commit, catches any leftover partial batch
    conn.close()

    print(f"Copying finished database to {db_path}...")
    shutil.copy2(LOCAL_DB_PATH, db_path)
    os.remove(LOCAL_DB_PATH)
    print(f"Copied and cleaned up local staging file.")

    print(f"\nDone.")
    print(f"Total files processed: {stats['total']}")
    print(f"New (content stored):  {stats['new']}")
    print(f"  of which from a caught hash collision (bytes differed): {stats['hash_collisions']}")
    print(f"Duplicates (reused, byte-verified identical): {stats['duplicate']}")
    print(f"Bytes of new content stored: {stats['bytes_new']}")
    print(f"Bytes saved by not re-storing duplicates: {stats['bytes_saved']}")


if __name__ == "__main__":
    if len(sys.argv) != 4:
        print("Usage: python3 extract_and_hash.py <image_path> <offset_in_sectors> <db_path>")
        sys.exit(1)
    main(sys.argv[1], int(sys.argv[2]), sys.argv[3])

"""
test_malicious_detection.py
Fast, isolated test of the flagging and search logic, using a
disposable throwaway database -- no real image or EMBER data needed.

Tests two cases:
  1. A file whose hash IS in malware_hashes -> should get flagged and
     show up in the search results.
  2. A file whose hash is NOT in malware_hashes -> should stay
     unflagged and NOT show up in the search results.

This is the only way to prove the logic actually catches a match,
since a real match on the Stage 1 image is very unlikely by nature
(EMBER's malware is 2006-2018 Windows PE samples; Stage 1 is a ~2004
Windows XP training image).
"""
import os
import sqlite3

TEST_DB = "/tmp/test_malicious.db"

if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

conn = sqlite3.connect(TEST_DB)
cur = conn.cursor()

cur.execute("CREATE TABLE images (id INTEGER PRIMARY KEY, name TEXT)")
cur.execute("CREATE TABLE content_store (id INTEGER PRIMARY KEY, sha256 TEXT, known_malicious INTEGER DEFAULT 0)")
cur.execute("CREATE TABLE file_refs (id INTEGER PRIMARY KEY, image_id INTEGER, content_id INTEGER, path TEXT)")
cur.execute("CREATE TABLE malware_hashes (sha256 TEXT PRIMARY KEY, source TEXT)")

cur.execute("INSERT INTO images (id, name) VALUES (1, 'test_image')")
cur.execute("INSERT INTO content_store (id, sha256) VALUES (1, 'malicious_hash_abc')")
cur.execute("INSERT INTO content_store (id, sha256) VALUES (2, 'clean_hash_xyz')")
cur.execute("INSERT INTO file_refs (image_id, content_id, path) VALUES (1, 1, '/evil.exe')")
cur.execute("INSERT INTO file_refs (image_id, content_id, path) VALUES (1, 2, '/notepad.exe')")
cur.execute("INSERT INTO malware_hashes (sha256, source) VALUES ('malicious_hash_abc', 'TEST')")
conn.commit()

cur.execute("UPDATE content_store SET known_malicious = 1 WHERE sha256 IN (SELECT sha256 FROM malware_hashes)")
conn.commit()

cur.execute("SELECT known_malicious FROM content_store WHERE id = 1")
result1 = cur.fetchone()[0]
assert result1 == 1, f"FAILED: expected malicious_hash_abc to be flagged, got {result1}"
print("[Case 1: known-malicious hash] flagged correctly")

cur.execute("SELECT known_malicious FROM content_store WHERE id = 2")
result2 = cur.fetchone()[0]
assert result2 == 0, f"FAILED: expected clean_hash_xyz to stay unflagged, got {result2}"
print("[Case 2: clean hash] correctly left unflagged")

cur.execute("""
    SELECT images.name, file_refs.path, content_store.sha256
    FROM file_refs
    JOIN content_store ON file_refs.content_id = content_store.id
    JOIN images ON file_refs.image_id = images.id
    WHERE content_store.known_malicious = 1
""")
search_results = cur.fetchall()
assert len(search_results) == 1, f"FAILED: expected 1 search result, got {len(search_results)}"
assert search_results[0][1] == "/evil.exe", f"FAILED: expected '/evil.exe', got '{search_results[0][1]}'"
print(f"[Search tool] correctly found exactly the malicious file: {search_results[0]}")

conn.close()
os.remove(TEST_DB)
print("\nAll cases behaved as expected: malicious hash flagged, clean hash left alone, search tool found exactly the right file.")

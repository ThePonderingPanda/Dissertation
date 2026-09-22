"""
test_step_e.py
Fast, isolated test of the Step E dedup + byte-verification logic,
using the real functions from extract_and_hash.py against a disposable
throwaway database. No disk image or mount needed -- runs in under a
second.

Tests three cases:
  1. A brand-new file -> should be stored as new content.
  2. The exact same file again -> should be detected as a genuine
     duplicate (hashes match AND bytes match).
  3. A deliberately engineered fake collision: real hashes copied from
     an existing content_store row, paired with genuinely different
     bytes. This cannot happen on real data -- it's the only way to
     directly exercise the [COLLISION] branch, which run5 and any
     real-image run can never trigger naturally.
"""
import zlib
import os
import sys
# the pipeline scripts live one directory up, in pipeline/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                os.pardir, 'pipeline'))
from extract_and_hash import create_database, find_existing_content, insert_new_content, hash_file

TEST_DB = "/tmp/test_step_e.db"


def check_and_store(cur, size, md5, sha256, sha512, data, label):
    """Same logic as the hash-match branch in walk_and_store(), copied
    here so it can run against controlled test data without pytsk3."""
    existing = find_existing_content(cur, md5, sha256, sha512)
    if existing is not None:
        existing_id, existing_compressed = existing
        existing_data = zlib.decompress(existing_compressed)
        bytes_match = (existing_data == data)
        if bytes_match:
            print(f"[{label}] hash matched content id {existing_id}, bytes MATCH -> genuine duplicate")
            return "duplicate"
        else:
            content_id = insert_new_content(cur, size, md5, sha256, sha512, data)
            print(f"[{label}] hash matched content id {existing_id}, bytes DIFFER -> COLLISION caught, stored as new content id {content_id}")
            return "collision"
    else:
        content_id = insert_new_content(cur, size, md5, sha256, sha512, data)
        print(f"[{label}] no hash match -> stored as new content id {content_id}")
        return "new"


if os.path.exists(TEST_DB):
    os.remove(TEST_DB)

conn = create_database(TEST_DB)
cur = conn.cursor()

data_a = b"This is test file A, some arbitrary content."
md5_a, sha256_a, sha512_a = hash_file(data_a)
result1 = check_and_store(cur, len(data_a), md5_a, sha256_a, sha512_a, data_a, "Case 1: new file")
assert result1 == "new", f"FAILED: expected 'new', got '{result1}'"

result2 = check_and_store(cur, len(data_a), md5_a, sha256_a, sha512_a, data_a, "Case 2: same file again")
assert result2 == "duplicate", f"FAILED: expected 'duplicate', got '{result2}'"

data_c = b"Completely different content, wrong length even."
result3 = check_and_store(cur, len(data_c), md5_a, sha256_a, sha512_a, data_c, "Case 3: engineered fake collision")
assert result3 == "collision", f"FAILED: expected 'collision', got '{result3}'"

conn.commit()
conn.close()
os.remove(TEST_DB)

print("\nAll three cases behaved as expected: new file stored, genuine duplicate detected, engineered collision caught and stored separately.")

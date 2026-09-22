"""
test_integrity.py
Fast, isolated test of verify_integrity.py's core hashing and
before/after comparison logic -- no disk image, mount, or hour-long
pipeline needed. Runs in under a second.

Tests two cases:
  1. A file left genuinely unchanged between two hashes -> should MATCH.
  2. A file deliberately modified in between -> should MISMATCH. This
     proves the check would actually catch a real integrity problem,
     not just always report PASS no matter what.
"""
import os
import sys
# the pipeline scripts live one directory up, in pipeline/
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                os.pardir, 'pipeline'))
from verify_integrity import hash_file_streaming

TEST_FILE = "/tmp/test_integrity_sample.bin"

# Case 1: unchanged file
with open(TEST_FILE, "wb") as f:
    f.write(b"Some sample evidence bytes, unchanged.")
before = hash_file_streaming(TEST_FILE)
after = hash_file_streaming(TEST_FILE)
assert before == after, f"FAILED: expected MATCH for an unchanged file, got before={before} after={after}"
print(f"[Case 1: unchanged file] before={before[:12]}... after={after[:12]}... -> MATCH (correct)")

# Case 2: deliberately modified file in between the two hashes
before2 = hash_file_streaming(TEST_FILE)
with open(TEST_FILE, "ab") as f:
    f.write(b" -- tampered!")
after2 = hash_file_streaming(TEST_FILE)
assert before2 != after2, "FAILED: expected MISMATCH for a modified file, but hashes matched"
print(f"[Case 2: modified file] before={before2[:12]}... after={after2[:12]}... -> MISMATCH (correct, caught the change)")

os.remove(TEST_FILE)
print("\nBoth cases behaved as expected: an unchanged file correctly matched, and a deliberately modified file was correctly caught as different.")

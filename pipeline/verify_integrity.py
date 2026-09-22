"""
verify_integrity.py
Wraps the extraction pipeline (extract_and_hash.py) with a before/after
integrity check on the RAW evidence files (the .E01/.E02 segments on
disk), not the mounted virtual view.

Automatically discovers every segment sharing the same base filename as
the given .E01 (E01, E02, E03, ...) so nothing gets silently missed --
this project has direct history with exactly that kind of miss.

Hashes every segment with SHA-256 (streamed in 1MB chunks, so a multi-GB
evidence file never needs to be loaded fully into memory) before the
extraction pipeline runs, runs the real pipeline by calling
extract_and_hash.main() directly (no logic duplicated), then hashes
every segment again afterward and compares.

If every segment's hash matches exactly before and after, that's direct
proof the pipeline never wrote to or altered the original evidence
during the run. A result log is written to integrity_check_result.txt
for citing in the dissertation.

Usage:
    python3 verify_integrity.py <raw_E01_path> <mounted_image_path> <offset_in_sectors> <db_path>

Example:
    python3 verify_integrity.py "/mnt/d/Dissertation/hacking case/4Dell Latitude CPi.E01" ~/ewf_mount/ewf1 63 /mnt/d/Dissertation/dedup.db
"""
import hashlib
import os
import sys

import extract_and_hash


def find_segments(e01_path):
    """Given the path to a .E01 file, find every sibling segment
    (.E01, .E02, .E03, ...) sharing the exact same base name, stopping
    at the first missing number."""
    if not e01_path.endswith(".E01"):
        raise ValueError(f"Expected a path ending in .E01, got: {e01_path}")
    base = e01_path[:-4]  # strip ".E01"
    segments = []
    n = 1
    while True:
        candidate = f"{base}.E{n:02d}"
        if os.path.exists(candidate):
            segments.append(candidate)
            n += 1
        else:
            break
    return segments


def hash_file_streaming(path, chunk_size=1024 * 1024):
    """SHA-256 of a file, read in 1MB chunks so multi-GB evidence files
    don't need to be loaded fully into memory."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def hash_segments(segments, label):
    print(f"\nHashing evidence {label}...")
    hashes = {}
    for seg in segments:
        h = hash_file_streaming(seg)
        hashes[seg] = h
        print(f"  SHA-256({seg}) = {h}")
    return hashes


def main(e01_path, mounted_image_path, partition_offset_sectors, db_path):
    segments = find_segments(e01_path)
    if not segments:
        print(f"No segments found starting from {e01_path} -- nothing to check.")
        sys.exit(1)
    print(f"Found {len(segments)} evidence segment(s):")
    for seg in segments:
        print(f"  {seg}")

    before_hashes = hash_segments(segments, "BEFORE running the pipeline")

    print("\nRunning the extraction pipeline...")
    extract_and_hash.main(mounted_image_path, partition_offset_sectors, db_path)

    after_hashes = hash_segments(segments, "AFTER running the pipeline")

    print("\nComparing before and after hashes...")
    all_match = True
    for seg in segments:
        match = before_hashes[seg] == after_hashes[seg]
        print(f"  {seg}: {'MATCH' if match else 'MISMATCH'}")
        if not match:
            all_match = False

    print()
    if all_match:
        print("PASS: evidence integrity confirmed. Every segment's hash is identical before and after the pipeline ran.")
    else:
        print("FAIL: evidence integrity check FAILED. At least one segment's hash changed during the run. "
              "Do not trust this run's results -- investigate immediately.")

    log_path = "integrity_check_result.txt"
    with open(log_path, "w") as f:
        f.write("Evidence integrity check\n")
        f.write(f"Segments checked: {len(segments)}\n")
        for seg in segments:
            f.write(f"\n{seg}\n")
            f.write(f"  Before: {before_hashes[seg]}\n")
            f.write(f"  After:  {after_hashes[seg]}\n")
            f.write(f"  Result: {'MATCH' if before_hashes[seg] == after_hashes[seg] else 'MISMATCH'}\n")
        f.write(f"\nOverall: {'PASS' if all_match else 'FAIL'}\n")
    print(f"\nResult also written to {log_path}")

    return all_match


if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("Usage: python3 verify_integrity.py <raw_E01_path> <mounted_image_path> <offset_in_sectors> <db_path>")
        sys.exit(1)
    ok = main(sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4])
    sys.exit(0 if ok else 1)

#!/usr/bin/env python3
"""
reverify_storage2.py -- in-residence integrity re-verification, repeatable.

Replaces reverify_storage.py. Same measurement, three defects fixed:

  1. The original does `cur.fetchall()` on a SELECT that includes
     compressed_content, loading every stored blob into memory at once. That is
     773 MB on the Hacking Case and 5.5 GB on the Data Leakage PC, and it is the
     pattern that has had sessions killed by the OOM killer. Ids are fetched
     first here and blobs pulled one row at a time.
  2. The original opens the evidence database read-write. Opened read-only here.
  3. The original prints "MB/s" while dividing by 1024 squared, so a binary
     number carried a decimal label. Reported as MiB/s here, matching the
     correction already made throughout the dissertation.

Fetch and verification are still timed separately, so the per-file figure remains
comparable with the published one: only the decompress, re-hash and compare are
counted as verification.

Repeats the whole pass N times and reports mean and standard deviation, which is
what section 5.6 calls for when it concedes that most figures come from one run.

Read-only. Writes nothing.

Usage:
    python3 reverify_storage2.py <db_path> [--repeat N]
"""
import hashlib
import math
import sqlite3
import sys
import time
import zlib

ALGOS = ("md5", "sha1", "sha256", "sha512")


def one_pass(db_path, verbose=False):
    con = sqlite3.connect("file:%s?mode=ro" % db_path, uri=True)
    ids = [r[0] for r in con.execute("SELECT id FROM content_store ORDER BY id")]

    fetch_s = verify_s = 0.0
    total_bytes = 0
    mismatches = []
    missing_hash = 0

    for cid in ids:
        t0 = time.perf_counter()
        row = con.execute(
            "SELECT md5, sha1, sha256, sha512, compressed_content"
            " FROM content_store WHERE id = ?", (cid,)).fetchone()
        t1 = time.perf_counter()
        fetch_s += t1 - t0
        if row is None or row[4] is None:
            continue

        stored = dict(zip(ALGOS, row[:4]))
        blob = row[4]
        t1 = time.perf_counter()
        data = zlib.decompress(blob)
        fresh = {a: getattr(hashlib, a)(data).hexdigest() for a in ALGOS}
        for a in ALGOS:
            if stored[a] is None:
                missing_hash += 1
            elif stored[a] != fresh[a]:
                mismatches.append((cid, a, stored[a], fresh[a]))
        t2 = time.perf_counter()
        verify_s += t2 - t1
        total_bytes += len(data)
        data = None
        blob = None
        row = None

    con.close()
    return {
        "n": len(ids), "fetch_s": fetch_s, "verify_s": verify_s,
        "bytes": total_bytes, "mismatches": mismatches,
        "missing_hash": missing_hash,
    }


def mean_sd(xs):
    n = len(xs)
    m = sum(xs) / n
    if n < 2:
        return m, 0.0
    var = sum((x - m) ** 2 for x in xs) / (n - 1)
    return m, math.sqrt(var)


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    db_path = sys.argv[1]
    repeat = 1
    if "--repeat" in sys.argv:
        repeat = int(sys.argv[sys.argv.index("--repeat") + 1])

    print("re-verifying %s, %d pass(es)" % (db_path, repeat))
    runs = []
    for i in range(repeat):
        r = one_pass(db_path)
        runs.append(r)
        print("  pass %d: %d contents, %.2f MiB decompressed, "
              "verify %.3f s, fetch %.3f s, %d mismatch(es)"
              % (i + 1, r["n"], r["bytes"] / 1024 ** 2,
                 r["verify_s"], r["fetch_s"], len(r["mismatches"])),
              flush=True)

    per_file = [r["verify_s"] / r["n"] * 1000 for r in runs if r["n"]]
    thru = [r["bytes"] / 1024 ** 2 / r["verify_s"] for r in runs if r["verify_s"]]
    verify = [r["verify_s"] for r in runs]
    fetch = [r["fetch_s"] for r in runs]

    print()
    print("  contents re-verified      : %d" % runs[0]["n"])
    print("  decompressed bytes        : %d" % runs[0]["bytes"])
    for name, xs, unit in (("verification time", verify, "s"),
                           ("fetch time", fetch, "s"),
                           ("per content", per_file, "ms"),
                           ("throughput", thru, "MiB/s")):
        m, sd = mean_sd(xs)
        print("  %-25s : %9.3f %s  (sd %.3f, n=%d)" % (name, m, unit, sd, len(xs)))

    bad = sum(len(r["mismatches"]) for r in runs)
    miss = runs[0]["missing_hash"]
    print("  mismatches across all passes: %d" % bad)
    if miss:
        print("  NOTE: %d stored hash values were NULL and could not be compared"
              % miss)
    for cid, a, s, f in runs[0]["mismatches"][:5]:
        print("    id=%s %s stored=%s fresh=%s" % (cid, a, s, f))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())

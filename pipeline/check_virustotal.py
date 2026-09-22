"""
check_virustotal.py

Looks up a list of SHA-256 hashes against VirusTotal's Public API v3,
using the hash-only lookup endpoint (no file upload -- we never send
actual file content to a third party, only its hash).

Intended use: once Step D (NSRL) identifies which stored files do NOT
match the NSRL "known good" list, dump their SHA-256 hashes one per
line into a text file and pass it to this script. Only that non-NSRL
subset should go through VT -- checking every file would burn through
the free-tier quota fast for no benefit, since a known-good file
matched in NSRL doesn't need a malware verdict too.

Respects the VirusTotal Public API free-tier limits (verified July 2026):
  - 4 requests / minute
  - 500 requests / day
There's no burst allowance -- requests over the limit are dropped with
HTTP 429 -- so this sleeps between every call rather than trying to
catch up after a failure. Already-checked hashes are skipped on re-run,
so it's safe to stop and resume across multiple days if you have more
than 500 to get through.

Requires a free VT API key: sign up at virustotal.com, then either
  export VT_API_KEY="your_key_here"
or pass it as the second command-line argument.

Usage:
  python3 -u check_virustotal.py hashes.txt [api_key] | tee vt_run.log
"""
import sys
import os
import time
import sqlite3
import requests
from requests.exceptions import RequestException

VT_URL = "https://www.virustotal.com/api/v3/files/{}"
SECONDS_BETWEEN_REQUESTS = 0.5   # 20,000/min research quota granted, safety margin retained
DAILY_LIMIT = 9000


def create_results_db(db_path):
    conn = sqlite3.connect(db_path)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS vt_results (
            sha256 TEXT PRIMARY KEY,
            status TEXT,          -- 'clean', 'malicious', 'not_found', 'error_*'
            malicious_count INTEGER,
            total_engines INTEGER,
            checked_at TEXT
        )
    """)
    conn.commit()
    return conn


# A single flaky request (timeout, dropped connection, etc.) used to
# crash the entire run -- no exception handling existed around the
# network call at all. Now retries a couple of times with a short
# backoff, and if it still fails, reports it as a transient network
# error rather than raising -- the caller decides not to cache that
# result, so it gets retried automatically on the next run.
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 3


def lookup_hash(session, api_key, sha256):
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = session.get(
                VT_URL.format(sha256),
                headers={"x-apikey": api_key},
                timeout=30,
            )
            break
        except RequestException as e:
            if attempt == MAX_RETRIES:
                return f"network_error: {type(e).__name__}", None, None
            time.sleep(RETRY_BACKOFF_SECONDS * attempt)

    if resp.status_code == 200:
        stats = resp.json()["data"]["attributes"]["last_analysis_stats"]
        # "suspicious" counted alongside "malicious" as flagged; adjust
        # here if you want a stricter/looser threshold for the write-up.
        malicious = stats.get("malicious", 0) + stats.get("suspicious", 0)
        total = sum(stats.values())
        status = "malicious" if malicious > 0 else "clean"
        return status, malicious, total
    elif resp.status_code == 404:
        return "not_found", None, None
    elif resp.status_code == 429:
        return "rate_limited", None, None
    else:
        return f"error_{resp.status_code}", None, None


def main(hashes_path, api_key, db_path="vt_results.db"):
    if not api_key:
        print("No API key found. Set VT_API_KEY or pass it as an argument.")
        sys.exit(1)

    with open(hashes_path) as f:
        hashes = [line.strip().lower() for line in f if line.strip()]

    print(f"Loaded {len(hashes)} hashes to check.")

    conn = create_results_db(db_path)
    cur = conn.cursor()
    session = requests.Session()

    counts = {"clean": 0, "malicious": 0, "not_found": 0, "other": 0}
    real_calls_made = 0
    skipped = 0

    for i, h in enumerate(hashes, 1):
        cur.execute("SELECT status FROM vt_results WHERE sha256 = ?", (h,))
        if cur.fetchone():
            skipped += 1
            continue

        if real_calls_made >= DAILY_LIMIT:
            print(f"  [!] Reached today's {DAILY_LIMIT}-request limit after "
                  f"{skipped} cached skips and {real_calls_made} real checks. "
                  f"{len(hashes) - i} hashes still unchecked -- re-run tomorrow.")
            break

        status, malicious, total = lookup_hash(session, api_key, h)
        real_calls_made += 1

        if status == "rate_limited":
            print(f"  [!] Rate limited at {h} -- stopping early. "
                  f"Re-run later to pick up where this left off.")
            break

        if status.startswith("network_error"):
            # Transient -- deliberately NOT cached to vt_results.db,
            # so this hash is retried automatically on the next run
            # rather than being permanently marked as an error.
            print(f"  [{real_calls_made}/{DAILY_LIMIT}] [!] {h} - {status}, "
                  f"skipping (will retry on next run)")
            time.sleep(SECONDS_BETWEEN_REQUESTS)
            continue

        if status == "clean":
            counts["clean"] += 1
            print(f"  [{real_calls_made}/{DAILY_LIMIT}] [CLEAN] {h} - 0/{total} engines flagged it")
        elif status == "malicious":
            counts["malicious"] += 1
            print(f"  [{real_calls_made}/{DAILY_LIMIT}] [MALICIOUS] {h} - {malicious}/{total} engines flagged it")
        elif status == "not_found":
            counts["not_found"] += 1
            print(f"  [{real_calls_made}/{DAILY_LIMIT}] [UNKNOWN] {h} - not previously seen by VirusTotal")
        else:
            counts["other"] += 1
            print(f"  [{real_calls_made}/{DAILY_LIMIT}] [!] {h} - {status}")

        cur.execute("""
            INSERT OR REPLACE INTO vt_results
            (sha256, status, malicious_count, total_engines, checked_at)
            VALUES (?, ?, ?, ?, datetime('now'))
        """, (h, status, malicious, total))
        conn.commit()
        time.sleep(SECONDS_BETWEEN_REQUESTS)

    conn.close()
    print(f"\nDone. Skipped (already cached): {skipped}  "
          f"Real checks made today: {real_calls_made}  "
          f"Clean: {counts['clean']}  "
          f"Malicious: {counts['malicious']}  "
          f"Not found in VT: {counts['not_found']}  "
          f"Errors: {counts['other']}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 check_virustotal.py <hashes.txt> [api_key]")
        sys.exit(1)
    hashes_file = sys.argv[1]
    key = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("VT_API_KEY")
    main(hashes_file, key)

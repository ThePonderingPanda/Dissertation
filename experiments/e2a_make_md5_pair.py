#!/usr/bin/env python3
"""
E2a, step 1 -- construct a published MD5 collision pair locally and verify it.

These are the two 128-byte messages from Wang and Yu's differential attack on
MD5, the pair reproduced in Selinger's demonstration, which is already cited in
the dissertation's reference list. They are inert data blocks, not programs.

Nothing is downloaded. The pair is written from constants and then checked: if
the MD5 digests do not match, or if any other digest does match, the constants
are wrong and the script says so rather than proceeding.

Writes two small files into the directory given on the command line.
"""
import hashlib
import os
import sys

# Wang and Yu (2005), the widely reproduced pair. Each is 128 bytes and they
# differ in six of them.
MSG1 = bytes.fromhex(
    "d131dd02c5e6eec4693d9a0698aff95c2fcab58712467eab4004583eb8fb7f89"
    "55ad340609f4b30283e488832571415a085125e8f7cdc99fd91dbdf280373c5b"
    "d8823e3156348f5bae6dacd436c919c6dd53e2b487da03fd02396306d248cda0"
    "e99f33420f577ee8ce54b67080a80d1ec69821bcb6a8839396f9652b6ff72a70"
)
MSG2 = bytes.fromhex(
    "d131dd02c5e6eec4693d9a0698aff95c2fcab50712467eab4004583eb8fb7f89"
    "55ad340609f4b30283e4888325f1415a085125e8f7cdc99fd91dbd7280373c5b"
    "d8823e3156348f5bae6dacd436c919c6dd53e23487da03fd02396306d248cda0"
    "e99f33420f577ee8ce54b67080280d1ec69821bcb6a8839396f965ab6ff72a70"
)

ALGOS = ("md5", "sha1", "sha256", "sha512")


def digests(b):
    return {a: getattr(hashlib, a)(b).hexdigest() for a in ALGOS}


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else "."
    os.makedirs(out, exist_ok=True)

    d1, d2 = digests(MSG1), digests(MSG2)

    print("block 1: %d bytes" % len(MSG1))
    print("block 2: %d bytes" % len(MSG2))
    print("bytes differing: %d"
          % sum(1 for a, b in zip(MSG1, MSG2) if a != b))
    print()
    for a in ALGOS:
        same = d1[a] == d2[a]
        print("  %-7s %s" % (a, "IDENTICAL" if same else "different"))
        print("          %s" % d1[a])
        print("          %s" % d2[a])
    print()

    if MSG1 == MSG2:
        print("FAILED: the two blocks are the same data, not a collision pair.")
        return 1
    if d1["md5"] != d2["md5"]:
        print("FAILED: the MD5 digests do not match, so the constants above are")
        print("wrong. Do not proceed; obtain a verified pair instead.")
        return 1
    for a in ("sha1", "sha256", "sha512"):
        if d1[a] == d2[a]:
            print("FAILED: %s also matches, which should be impossible." % a)
            return 1

    p1 = os.path.join(out, "collision_a.bin")
    p2 = os.path.join(out, "collision_b.bin")
    open(p1, "wb").write(MSG1)
    open(p2, "wb").write(MSG2)

    print("VERIFIED: same MD5, different SHA-1, SHA-256 and SHA-512.")
    print("written: %s" % p1)
    print("written: %s" % p2)
    return 0


if __name__ == "__main__":
    sys.exit(main())

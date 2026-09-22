# Deduplicated storage for forensic disk images — source code

MSc Cyber Security dissertation, University of Plymouth, PROJ518.
*Identical Until Proven Otherwise: Design and Evaluation of a Deduplicated Storage System for Forensic Disk Images.*

Licensed under the MIT License (see LICENSE).

This is the system the dissertation describes, together with its tests and the
collision experiment that its central claim rests on. It is a research prototype,
written to take measurements rather than to be deployed.

**The complete archive is what accompanies the dissertation**, as
`dissertation-code.tar.gz`: the same code plus every measurement script, the run
logs those measurements were read from, and an earlier approach to malware
detection that was abandoned during implementation. This repository carries the
part a reader would want to run and read. Appendix H of the dissertation lists the
archive in full.

---

## What the system does

It extracts allocated files from a forensic disk image, deduplicates them by whole
file content, verifies every hash match byte for byte before treating two files as
identical, compresses what remains, and stores it in SQLite. Stored content is
then looked up in the NSRL reference set and screened against VirusTotal.

The design decision that distinguishes it from the systems reviewed in Chapter 2
is the byte-for-byte comparison. Every other system deletes one of two files on a
hash match alone. This one reads both and compares them, and on a mismatch stores
both rather than discarding either.

---

## Requirements

```
python >= 3.10
pytsk3          # filesystem parsing, via The Sleuth Kit
requests        # VirusTotal API
```

`pip install -r requirements.txt`

Also needed outside Python:

- **The Sleuth Kit** 4.12.1 or later (`blkls`, `fls`, `fsstat`, `mmls`).
- **libewf** (`ewfmount`, `ewfinfo`) for EWF evidence. This matters: the pytsk3
  build used here is **not** compiled with EWF support, so an `.E01` cannot be
  opened directly. Automatic detection reads the container's compressed bytes as
  though they were a filesystem and reports "possible encryption detected, high
  entropy". EWF evidence must be mounted with `ewfmount` first and the resulting
  raw device passed to the pipeline. Raw `.dd` images open directly.

Nothing else is required. The development environment also carried `pandas`,
`numpy`, `scipy`, `scikit-learn`, `lightgbm` and `ember`, from an approach to
malware detection that was abandoned during implementation. None of them is needed
by anything here.

---

## Layout

```
pipeline/      the system itself, seven scripts, in the order they run
tests/         three tests that need no evidence image
experiments/   the collision experiment, including the fault-injected extractors
figures/       every figure in the dissertation, the data behind each as a CSV,
               the scripts that drew them, and how to rebuild them by hand
```

Appendix H of the dissertation describes all seven pipeline scripts with their
line counts. They are the system; everything else here supports them.

---

## Running it, in order

**1. Acquisition integrity, before extraction**

```bash
python pipeline/verify_integrity.py <image.E01>
```

Digests each segment, runs the pipeline, digests them again, compares the two sets.
Takes an `.E01` path only; it enumerates `.E02`, `.E03` and onward itself, stopping
at the first gap so a partial set cannot pass unnoticed. Writes
`integrity_check_result.txt`.

> Detection, not prevention. The second digest is taken after extraction has already
> finished, so a failure tells you the run cannot be trusted. It does not stop it.

**2. Extraction, hashing, deduplication, compression and storage**

```bash
python pipeline/extract_and_hash.py <image> <partition_offset_in_sectors> <out.db>
```

Offset `0` where there is no partition table. Use `mmls <image>` to find it
otherwise. The database is assembled on local disk and moved to the destination once the run
ends. Building it in place across a mounted Windows share is far slower: the write
pattern is many small transactions.

Output lines: `[+]` new content stored, `[=]` duplicate confirmed byte-identical
and reused, `[COLLISION]` hashes matched but bytes differed, so both were stored.

**3. SHA-1 backfill**

```bash
python pipeline/backfill_sha1.py <out.db>
```

Adds a `sha1` column and fills it.

> SHA-1 is never consulted when deciding whether two files are the same. It is here
> for one reason: NSRL records are keyed on it. For rows written before this script
> ran, the digest covers the bytes held in the store, not the file as it sat on the
> image.

**4. Known-file lookup**

```bash
python pipeline/nsrl_match.py <out.db> <nsrl.db>
```

Sets `nsrl_known` where **both** SHA-256 and SHA-1 agree with the same reference
record. Requiring both is deliberate: a single-hash rule can be defeated by a
published SHA-1 collision, which the dissertation demonstrates.

Note that this stage **annotates and does not remove**. Nothing is deleted from
storage. The dissertation reports what removal would save as a counterfactual.

This script creates an index on the local hash columns. That index is not used by
the query it was created for, and the dissertation reports its cost.

**5. Malware screening**

```bash
python pipeline/check_virustotal.py <hash_list.txt>
```

Submits only what step 4 left unresolved. Responses are cached in `vt_results.db`,
so a repeat run costs no quota. Requires an API key.

**6. In-residence re-verification, on demand**

```bash
python pipeline/reverify_storage.py <out.db> [--repeat N]
```

Reads every stored content back, decompresses it, re-derives all four hashes from
the decompressed bytes and compares them against the recorded values. `--repeat`
runs the whole pass more than once and reports mean and standard deviation.

**7. Investigator queries**

```bash
python pipeline/investigator_queries.py
```

A demonstration that the schema supports the questions an investigator would ask.

---

## Checking it works, with no evidence image

Everything above needs a disk image. Nothing below does, so this is the quickest
way to satisfy yourself that the system behaves as described.

**The three tests.** Each builds its own data, asserts, and prints what it found.

```bash
python tests/test_step_e.py                 # new file stored, duplicate reused, collision caught
python tests/test_integrity.py              # unchanged file matches, modified file caught
python tests/test_malicious_detection.py    # malicious flagged, clean left alone
```

They import from `pipeline/`, so `pytsk3` must be installed even though no image is
ever opened. Without it the import fails before the first assertion runs.

**The collision experiment**, which is the one that matters. It exercises the
byte-for-byte comparison against a published MD5 collision rather than an
engineered one. `e2a_make_md5_pair.py` emits the pair from the constants and aborts unless it can
confirm matching MD5 alongside differing SHA-1, SHA-256 and SHA-512. A typo in a
constant fails the script rather than quietly producing a worthless test. One
`mke2fs -d` puts them in an ext2 filesystem, with no mounting and no root:

```bash
mkdir files && cd files
python ../experiments/e2a_make_md5_pair.py       # the two 128-byte files
cd ..
mke2fs -q -t ext2 -d files -F collision.img 1M   # no mount, no root
python pipeline/extract_and_hash.py collision.img 0 out.db
```

The unmodified pipeline stores both files and never reaches the byte check, because
SHA-256 and SHA-512 disagree first:

```
[+] /collision_a.bin (128 bytes) - new, stored as content id 1
[+] /collision_b.bin (128 bytes) - new, stored as content id 2
  of which from a caught hash collision (bytes differed): 0
```

Run the same image through the two fault-injected copies to see the failure the
design exists to prevent. Weakening the lookup to MD5 alone reaches the byte check,
which refuses the match:

```
[COLLISION] /collision_b.bin - hashes matched content id 1 but bytes differ!
            Stored as new content id 2
```

Weakening the lookup *and* removing the byte check stores one file for two paths,
which is what every system reviewed in Chapter 2 of the dissertation does:

```
[=] /collision_b.bin (128 bytes) - duplicate, reused content id 1
Duplicates (reused, byte-verified identical): 1
```

Asking that archive for `collision_b.bin` returns `collision_a.bin`. The tool
reports success and hands back the wrong evidence.

---

## Schema

```sql
images(id, name, image_hash, acquisition_date, examiner, notes)
content_store(id, size, md5, sha256, sha512, compressed_content,
              nsrl_known, known_malicious, sha1)
file_refs(id, image_id, content_id, path)
```

Three columns are created by later scripts rather than by `extract_and_hash.py`:
`sha1` by the backfill, and `nsrl_known` and `known_malicious` were provisioned
during planning. `images` records only a name; the acquisition hash, date,
examiner and notes are declared and never written, which the dissertation lists as
a limitation.

`content_store.size` is the size the filesystem reports, which on one evidence set
is not the number of bytes actually stored. Use the decompressed length where that
matters.

---

## Known faults, stated rather than hidden

These are documented in the dissertation and are listed here so that anyone
reading the code finds them named rather than discovering them.

- **`extract_and_hash.py` accumulates file data with `data += chunk`**, so its cost
  rises with the square of the chunk count. Extraction is slower than it should be.
  No published measurement runs through this reader: the byte check is timed around
  the comparison alone, stage timings come from `e13_stage_timing.py`, which uses
  `b"".join`, and image walks from `e15d_from_image.py`, which streams into the
  hash.
- **No index exists on the hash columns during extraction**, so every lookup scans
  the content store.
- **The index `nsrl_match.py` creates is never used** by the query it was created
  for. Its cost is measured in the dissertation.
- **`verify_integrity.py` reports a mismatch after the fact.** Extraction has
  already finished and committed by the time the second hash is taken. Nothing is
  rolled back or quarantined.
- **The original `reverify_storage.py` loaded every stored blob into memory at
  once** and opened the evidence database read-write. The version here fixes both,
  and corrects a throughput figure that divided by 1024 squared while labelling
  the result MB/s.
- **Only allocated files are reached.** Deleted and unallocated content is out of
  scope, and the dissertation measures what that exclusion costs.

---

## Where the published numbers came from

Chapter 4's results were produced by a set of one-off measurement scripts, one per
measurement, each naming the command that produced it and the database it read.
They open every evidence database **read-only**; anything that had to write created
a new database rather than altering a published one.

Those scripts are in the archive accompanying the dissertation rather than here.
They carry hard-coded paths to the machine they were run on and will not run
elsewhere without editing, and Appendix D of the dissertation gives each derivation
in prose. What follows is the list, so that a result can be traced to the script
that produced it.

| Script, in the archive | Produces |
|---|---|
| `e1_storage_stages.py` | the four-stage storage table |
| `e4_union.py` | cross-image deduplication from a real union store |
| `unalloc_dedup.py`, `e3_cross_image.py` | block-level deduplication of unallocated space |
| `e6_compression_check.py` | validation of the compression-only configuration |
| `e7_tiering.py` | engine-consensus tiering across every evidence set |
| `e8_overhead.py` | metadata overhead decomposed by `dbstat` |
| `e2a_make_md5_pair.py`, `e2b_nsrl_rule.py` | the collision experiments |
| `e9_chunk_level.py` | the 4 KB block-level comparison |
| `e13_stage_timing.py` | the share of a run each stage takes |
| `e14_scaling.py` | every way of pooling two or more evidence sets |
| `e15a_counts.py`, `e15e_workingset.py` | the work each stage removes, and the analyst's working set |
| `e15_build_index.py`, `e15c_compare.py`, `e15b_queries.py` | query cost against the store, and against a metadata index of it |
| `e15d_from_image.py` | the same question answered from the image, with no store |
| `e15f_vt_rate.py` | the observed screening submission rate |

The collision experiments also use two fault-injected copies of the extractor,
named so that this is obvious. `extract_and_hash_MD5ONLY.py` weakens the lookup to
MD5 alone. `extract_and_hash_NOBYTECHECK.py` applies that same change and additionally forces
`bytes_match` to true, so it carries two weakenings, not one. `diff` either file
against `pipeline/extract_and_hash.py` to see precisely what moved.

Neither belongs to the pipeline. Both exist to drive a code path that untampered
evidence cannot reach.

---

## A note on the evidence

The evidence images are public reference corpora from NIST CFReDS, Digital Corpora
and the DFRWS 2011 Forensics Challenge. They are not distributed with this code.
See the dissertation's evidence table for the full list and each source.

---

## Paths

The seven scripts in `pipeline/` take their paths as arguments and run anywhere.

The measurement scripts in the archive do not: they carry a hard-coded path to the
layout they were run under, usually `/home/student/dissertation/`. That is left as
it is on purpose. Those scripts produced the figures the dissertation reports, and
rewriting them now would mean publishing something other than the code that
produced those results. To reproduce one, change the path constant at the top and
point it at your own database; each script names the database it expects.

`e2_verify.py` here is the one exception, and carries such a path for the same
reason.

---

## Citing this work

Ramesh, V. (2026) *Identical Until Proven Otherwise: Design and Evaluation of a
Deduplicated Storage System for Forensic Disk Images*. MSc dissertation. University of Plymouth.

The dissertation is the primary output. This repository holds the system it
describes; the complete archive, listed in its Appendix H, accompanies the
submission.

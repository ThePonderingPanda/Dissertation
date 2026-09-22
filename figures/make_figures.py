# -*- coding: utf-8 -*-
"""Corrected dissertation figures.

All values taken from CANONICAL_FIGURES.md. Every figure is the author's own,
generated from the project's own measurements. Nothing is adapted from any
published source.

Fixes in this version:
  4.1  legend moved clear of the bars; rows sorted by the value actually labelled;
       true zeros annotated rather than rendered as an invisible bar
  4.3  section symbol removed from the title; label collisions resolved
  4.4  TRUE ZEROS NO LONGER DRAWN AS 0.005 - a zero now shows no bar and an
       explicit "0.00" label, and the axis label covers both series
  22 September 2026: in-image titles removed (three made claims the data did not
  support), and the dissertation renumbered its figures sequentially. Filenames
  keep their original numbers: fig_4_1 is Figure 3, fig_4_2 Figure 4, fig_4_4
  Figure 6. HOW_THE_FIGURES_WERE_MADE.md gives the full mapping.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import os

# Write beside this script, wherever it happens to live, so it runs on any machine.
OUT = os.path.dirname(os.path.abspath(__file__)) + os.sep

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10,
    "axes.labelsize": 9, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.6,
    "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
})
INK, G1, G2, G3 = "#1a1a1a", "#4a4a4a", "#8c8c8c", "#c8c8c8"

# name, dedup%, comp%, combined%, shortfall pp, overhead%, avg stored bytes
SETS = [
    ("HFS+ test image",  0.00, 99.86, 99.86,  0.00, 72.45,    1034),
    ("Casper-rw",       56.52, 72.71, 85.33, 43.90, 25.75,   37651),
    ("Data Leakage PC", 31.34, 61.76, 75.81, 17.29,  7.41,  115272),
    ("NTFS1",           31.22, 54.92, 61.46, 24.68, 41.72, 1395639),
    ("Hacking Case",    18.03, 51.93, 59.91, 10.05, 19.38,   86135),
    ("Android mtd6",     0.67, 46.33, 46.70,  0.30,  5.59,  110328),
    ("Android mtd8",     0.43, 39.74, 39.83,  0.34,  1.02,  354422),
    ("Android mtd7",     0.46, 38.98, 39.32,  0.13,  0.50, 3546168),
    ("Android sdcard",   0.11, 10.25, 10.25,  0.11,  9.05,   99950),
]
# Android sdcard corrected September 2026: ten files on that volume were
# truncated at 32,768 bytes during extraction while the database recorded their
# full filesystem size, inflating the baseline by 6,301,419 bytes. Figures here
# use the bytes actually stored. See Appendix H, Table H.1 and the correction
# log at the end of HOW_THE_FIGURES_WERE_MADE.md.

# ------------------------------------------------------------ Figure 3 (fig_4_1)
# sorted by combined saving, which is the value labelled on each row
rows = sorted(SETS, key=lambda s: -s[3])
names = [r[0] for r in rows]
y = np.arange(len(names))
h = 0.26
fig, ax = plt.subplots(figsize=(6.9, 4.6))
ax.barh(y + h, [r[1] for r in rows], h, label="Deduplication only",
        color=G3, edgecolor=INK, linewidth=0.6)
ax.barh(y, [r[2] for r in rows], h, label="Compression only",
        color=G2, edgecolor=INK, linewidth=0.6)
ax.barh(y - h, [r[3] for r in rows], h, label="Both together",
        color=G1, edgecolor=INK, linewidth=0.6)
for i, r in enumerate(rows):
    ax.text(r[3] + 1.2, y[i] - h, "%.2f" % r[3], va="center", fontsize=7.6, color=INK)
    if r[1] == 0.0:                       # a true zero, not a missing bar
        ax.text(0.8, y[i] + h, "0.00 (no duplicates)", va="center",
                fontsize=7.0, color=INK, style="italic")
ax.set_yticks(y)
ax.set_yticklabels(names)
ax.invert_yaxis()
ax.set_xlabel("Storage saved against the naive baseline (%)")
ax.set_xlim(0, 116)
ax.legend(frameon=False, fontsize=8, loc="lower center",
          bbox_to_anchor=(0.5, -0.30), ncol=3)
fig.savefig(OUT + "fig_4_1_savings.png")
plt.close(fig)

# ------------------------------------------------------------ Figure 4 (fig_4_2)
x = [s[1] for s in SETS]
yy = [s[4] for s in SETS]
fig, ax = plt.subplots(figsize=(6.2, 4.3))
ax.scatter(x, yy, s=56, facecolor=G2, edgecolor=INK, linewidth=0.9, zorder=3)
m, b = np.polyfit(x, yy, 1)
xs = np.linspace(-2, 60, 50)
ax.plot(xs, m * xs + b, color=INK, linewidth=0.9, linestyle="--", zorder=2,
        label="least squares fit, slope %.2f" % m)
for name, dx, dy in [("Casper-rw", -14, -16), ("NTFS1", -40, 8),
                     ("Data Leakage PC", 8, -13), ("Hacking Case", 9, -3)]:
    p = next(q for q in SETS if q[0] == name)
    ax.annotate(name, (p[1], p[4]), textcoords="offset points",
                xytext=(dx, dy), fontsize=7.6, color=INK)
ax.annotate("HFS+ and the four\nAndroid partitions\n(0.00 to 0.67%)",
            xy=(0.4, 0.2), xytext=(2.0, 20.0), fontsize=7.4, color=INK,
            ha="left", va="bottom", linespacing=1.4,
            arrowprops=dict(arrowstyle="-", color=INK, linewidth=0.7,
                            shrinkA=0, shrinkB=3))
ax.set_xlabel("Deduplication rate on its own (%)")
ax.set_ylabel("Shortfall against the additive prediction\n(percentage points)")
ax.set_xlim(-3, 62)
ax.set_ylim(-3, 50)
ax.legend(frameon=False, fontsize=8, loc="upper left")
fig.savefig(OUT + "fig_4_2_shortfall.png")
plt.close(fig)

# Figure 5 (fig_4_3) is drawn by make_fig_4_3_overhead.py. An older
# single-series version used to be drawn here and overwrote it; it was removed.

# ------------------------------------------------------------ Figure 6 (fig_4_4)
# name, % by file count, % by volume.  A true zero is stored as 0.0 and is
# NOT drawn as a bar; it is labelled instead. No value is substituted.
NSRL = [("Data Leakage PC", 83.02, 57.80), ("Hacking Case", 66.61, 51.15),
        ("HFS+ test image", 16.67, 0.05), ("NTFS1", 13.64, 0.24),
        ("Casper-rw", 9.72, 7.41), ("Android mtd6", 1.62, 3.76),
        ("Android mtd8", 1.34, 0.01), ("Android sdcard", 0.53, 0.00),
        ("Android mtd7", 0.08, 0.00)]
n2 = [r[0] for r in NSRL]
y2 = np.arange(len(n2))
FLOOR = 0.008
fig, ax = plt.subplots(figsize=(6.9, 4.6))
for i, (_, fpc, bpc) in enumerate(NSRL):
    ax.barh(y2[i] + 0.19, fpc, 0.36, color=G2, edgecolor=INK, linewidth=0.6,
            label="By file count" if i == 0 else None)
    if bpc > 0:
        ax.barh(y2[i] - 0.19, bpc, 0.36, color=G1, edgecolor=INK, linewidth=0.6,
                label="By volume" if i == 0 else None)
    else:
        # a genuine zero: no bar, stated explicitly
        ax.text(FLOOR * 1.15, y2[i] - 0.19, "0.00  (no bytes matched)",
                va="center", fontsize=7.0, color=INK, style="italic")
ax.set_xscale("log")
ax.set_xlim(FLOOR, 260)
ax.set_yticks(y2)
ax.set_yticklabels(n2)
ax.invert_yaxis()
ax.set_xlabel("Recognised by the NSRL (%, logarithmic scale)")
ax.axhline(1.5, color=INK, linewidth=0.8, linestyle=":")
ax.text(160, 1.05, "Windows\nworkstations", fontsize=7.2, style="italic",
        color=INK, ha="center", va="center", linespacing=1.3)
ax.text(160, 2.0, "everything else", fontsize=7.2, style="italic",
        color=INK, ha="center", va="center")
ax.legend(frameon=False, fontsize=8, loc="lower center",
          bbox_to_anchor=(0.5, -0.28), ncol=2)
fig.savefig(OUT + "fig_4_4_nsrl.png")
plt.close(fig)

print("regenerated the storage, shortfall and known-file figures")
for f in sorted(os.listdir(OUT)):
    print("   ", f)

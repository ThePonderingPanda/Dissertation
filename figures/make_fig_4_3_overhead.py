# -*- coding: utf-8 -*-
"""Figure 5 (file fig_4_3), rebuilt September 2026.

Supersedes an older block in make_figures.py, which plotted only the
container measure and captioned it as bookkeeping cost. The dbstat/freelist
decomposition reported in section 4.5 shows 87.8% of that measure is free
pages, so the figure now plots both series: the container measure as published,
and schema cost once free pages are removed. Every value is re-derived here
from the figures in Table 10 rather than copied from the old data file.
"""
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

OUT = os.path.dirname(os.path.abspath(__file__)) + os.sep
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9, "axes.titlesize": 10,
    "axes.labelsize": 9, "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "grid.linewidth": 0.6,
    "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
})
INK, G2 = "#1a1a1a", "#8c8c8c"

# name, unique contents, database file size, compressed payload, free-page bytes
SETS = [
    ("HFS+ test image",     12,          45056,          12412,         4096),
    ("Casper-rw",          319,       16175104,       12010745,      3784704),
    ("Hacking Case",      8976,      958959616,      773154912,    175026176),
    ("Android sdcard",     188,       20660224,       18790671,      1622016),
    ("Android mtd6",       557,       65093632,       61452854,      2912256),
    ("Data Leakage PC",  47432,     5905600512,     5467700746,    377954304),
    ("Android mtd8",      4982,     1783988224,     1765734244,     11563008),
    ("NTFS1",               22,       52686848,       30704067,     21909504),
    ("Android mtd7",      1191,     4244504576,     4223485930,     15437824),
]

avg, container, schema, names = [], [], [], []
for name, n, fsize, payload, free in SETS:
    avg.append(payload / float(n))
    container.append((fsize - payload) / float(fsize) * 100)
    schema.append((fsize - payload - free) / float(payload) * 100)
    names.append(name)

fig, ax = plt.subplots(figsize=(6.4, 4.4))
ax.scatter(avg, container, s=62, marker="^", facecolor="white",
           edgecolor=INK, linewidth=1.1, zorder=3,
           label="Container: database file above payload")
ax.scatter(avg, schema, s=56, facecolor=G2, edgecolor=INK, linewidth=0.9,
           zorder=4, label="Schema: rows and indexes, free pages removed")
ax.plot(sorted(avg), [s for _a, s in sorted(zip(avg, schema))],
        color=INK, linewidth=0.8, alpha=0.45, zorder=2)

# Four sets sit almost on top of one another between 1.10% and 1.39%, so they
# carry one shared label rather than four overlapping ones. Table 10 has the
# individual values.
CLUSTER = {"Hacking Case", "Android sdcard", "Android mtd6", "Data Leakage PC"}
OFF = {"HFS+ test image": (12, -4), "Casper-rw": (11, 2),
       "Android mtd8": (12, 5), "NTFS1": (12, 4), "Android mtd7": (-30, -15)}
for i, nm in enumerate(names):
    if nm in CLUSTER:
        continue
    ax.annotate(nm, (avg[i], schema[i]), textcoords="offset points",
                xytext=OFF[nm], fontsize=7.2, color=INK)
ci = [i for i, nm in enumerate(names) if nm in CLUSTER]
cx = sum(avg[i] for i in ci) / len(ci)
cy = sum(schema[i] for i in ci) / len(ci)
ax.annotate("Hacking Case, Android sdcard," + chr(10) + "Android mtd6, Data Leakage PC",
            (cx, cy), textcoords="offset points", xytext=(-208, -38),
            fontsize=7.2, color=INK, ha="left", va="center",
            arrowprops=dict(arrowstyle="-", linewidth=0.6, color=INK,
                            shrinkA=4, shrinkB=6))

ax.set_xscale("log")
ax.set_yscale("log")
ax.set_xlim(500, 9e6)
ax.set_ylim(0.045, 700)
ax.set_xlabel("Average stored size per unique file (bytes, logarithmic scale)")
ax.set_ylabel("Overhead (%, logarithmic scale)")
ax.legend(loc="upper right", frameon=False, fontsize=7.6)
fig.savefig(OUT + "fig_4_3_overhead.png")
plt.close(fig)

with open(OUT + "data/fig_4_3_overhead.csv", "w") as f:
    f.write("Evidence set,Average stored bytes per unique file,"
            "Container overhead (%),Schema overhead (% of payload),"
            "Unique contents,Database file size (bytes),"
            "Compressed content (bytes),Free pages (bytes)\n")
    for i, (name, n, fsize, payload, free) in enumerate(SETS):
        f.write("%s,%d,%.2f,%.2f,%d,%d,%d,%d\n"
                % (name, round(avg[i]), container[i], schema[i],
                   n, fsize, payload, free))
print("wrote fig_4_3_overhead.png and its data file")
for i, nm in enumerate(names):
    print("  %-17s avg %9d  container %6.2f%%  schema %7.2f%%"
          % (nm, round(avg[i]), container[i], schema[i]))

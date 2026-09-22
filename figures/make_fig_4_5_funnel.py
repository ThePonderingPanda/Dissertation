# -*- coding: utf-8 -*-
"""Figure 7 (formerly 4.5): the screening funnel on the Data Leakage PC image.

Every number is read from data/fig_4_5_funnel.csv, which was re-derived from the
evidence database and checked by _work/verify/check_figures.py. Nothing is typed here.
The box widths are stylised rather than proportional: at true scale the last box, 34
against 80,260, would be invisible.

Run:  python3 make_fig_4_5_funnel.py
"""
import csv
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = HERE + os.sep

plt.rcParams.update({
    "font.size": 9, "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
})
INK = "#1a1a1a"

with open(os.path.join(HERE, "data", "fig_4_5_funnel.csv"), encoding="utf-8") as f:
    rows = list(csv.DictReader(f))
stages = [(r["Stage"], int(r["Count remaining"]),
           float(r["Removed at this stage (%)"]) if r["Removed at this stage (%)"] else None)
          for r in rows]

WIDTHS = [8.7, 7.6, 5.0, 2.5]                 # stylised, see docstring
FILLS = ["#c8c8c8", "#8c8c8c", "#4a4a4a", "#1c1c1c"]
TEXT = [INK, INK, "white", "white"]
H, GAP = 1.25, 0.70

fig, ax = plt.subplots(figsize=(7.4, 3.9))
y = 0.0
for i, (label, count, removed) in enumerate(stages):
    w = WIDTHS[i]
    ax.add_patch(FancyBboxPatch((-w / 2, y - H), w, H,
                                boxstyle="round,pad=0,rounding_size=0.12",
                                facecolor=FILLS[i], edgecolor=INK, linewidth=1.0))
    ax.text(0, y - H / 2, "{:,}".format(count), ha="center", va="center",
            fontsize=15, fontweight="bold", color=TEXT[i])
    ax.text(w / 2 + 0.35, y - H / 2, label, ha="left", va="center", fontsize=9.5, color=INK)
    if i < len(stages) - 1:
        top, bot = y - H - 0.08, y - H - GAP + 0.08
        ax.annotate("", xy=(0, bot), xytext=(0, top),
                    arrowprops=dict(arrowstyle="-|>", color=INK, linewidth=1.1,
                                    mutation_scale=10))
        nxt_removed = stages[i + 1][2]
        ax.text(-0.35, (top + bot) / 2, "minus %.1f%%" % nxt_removed,
                ha="right", va="center", fontsize=9.5, style="italic", color=INK)
    y -= H + GAP

ax.set_xlim(-4.7, 9.6)
ax.set_ylim(y + GAP - 0.2, 0.2)
ax.axis("off")
fig.savefig(OUT + "fig_4_5_funnel.png")
plt.close(fig)
print("wrote fig_4_5_funnel.png from data/fig_4_5_funnel.csv")
for label, count, removed in stages:
    print("  %-38s %7s  %s" % (label, "{:,}".format(count),
                               "" if removed is None else "minus %.1f%%" % removed))

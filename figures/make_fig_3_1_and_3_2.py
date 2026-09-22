# -*- coding: utf-8 -*-
"""Figures 1 and 2 (files fig_3_1 and fig_3_2).

Replaces the single crowded diagram that combined a process flow with a schema
diagram. Splitting them fixes four defects the author identified:

  - the image_id arrow was drawn as a curve straight through two other boxes,
    and its label collided with the caption underneath
  - the content_id label sat on top of the content_store border
  - the "bytes differ" arrow crossed diagonally over the images box
  - an arrow ran from VirusTotal screening into file_refs, which is not a
    relationship that exists

Both figures are now laid out on a fixed grid with no crossing arrows and no
diagonal connectors, so either can be redrawn by hand in PowerPoint SmartArt,
draw.io or Visio in a few minutes. See HOW_THE_FIGURES_WERE_MADE.md.

Run:  python make_fig_3_1_and_3_2.py
"""
import os
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon, Rectangle

OUT = os.path.dirname(os.path.abspath(__file__)) + os.sep

plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "figure.dpi": 300, "savefig.dpi": 300, "savefig.bbox": "tight",
})

INK = "#111111"
WHITE, LIGHT, MID = "#ffffff", "#f2f2f2", "#dcdcdc"


def box(ax, cx, cy, w, h, text, fc=LIGHT, lw=1.0, fs=8.6, bold=False):
    """A rounded box centred on (cx, cy)."""
    ax.add_patch(FancyBboxPatch(
        (cx - w / 2, cy - h / 2), w, h,
        boxstyle="round,pad=0.02,rounding_size=0.06",
        facecolor=fc, edgecolor=INK, linewidth=lw))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, color=INK,
            weight="bold" if bold else "normal", linespacing=1.5)


def diamond(ax, cx, cy, w, h, text, fs=8.4):
    ax.add_patch(Polygon([(cx, cy + h / 2), (cx + w / 2, cy),
                          (cx, cy - h / 2), (cx - w / 2, cy)],
                         closed=True, facecolor=WHITE, edgecolor=INK, linewidth=1.3))
    ax.text(cx, cy, text, ha="center", va="center", fontsize=fs, color=INK,
            linespacing=1.5)


def arrow(ax, x1, y1, x2, y2, label=None, side="right", fs=7.6):
    """A straight arrow. Labels sit clear of the line, never on top of it."""
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>",
                                 mutation_scale=11, color=INK, linewidth=1.0,
                                 shrinkA=1, shrinkB=1))
    if label:
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        dx, dy = (0.16, 0) if side == "right" else (-0.16, 0)
        if abs(y2 - y1) < 0.01:                      # horizontal arrow
            dx, dy = 0, 0.16
        ax.text(mx + dx, my + dy, label, fontsize=fs, color=INK, style="italic",
                ha="left" if side == "right" else "right", va="center")


# ===================================================================== Fig 3.1
# One vertical spine. The only branch is the deduplication decision, and both
# of its arms come back to the same box. Nothing crosses anything.
fig, ax = plt.subplots(figsize=(7.0, 8.4))

# Geometry is chosen so that every arrow lands inside the box it points at and
# no label overflows its box. The diamond is 4.2 wide, so its side vertices sit
# at x = 2.9 and x = 7.1; the arms sit outside those, and the database box is
# wide enough to catch all three incoming arrows.
CX, LX, RX = 5.0, 2.20, 7.80          # centre, left arm, right arm
BW, BH = 4.5, 0.68                    # spine box size
AW = 3.9                              # arm box width

box(ax, CX, 12.6, BW, BH, "Evidence image  (E01 or raw)", WHITE, 1.4, bold=True)
box(ax, CX, 11.5, BW, BH, "Mount it read-only  (ewfmount)", WHITE)
box(ax, CX, 10.4, BW, BH, "Walk the filesystem  (pytsk3)", WHITE)
box(ax, CX, 9.25, BW, 0.86,
    "Read each file and hash it\nMD5   |   SHA-256   |   SHA-512", MID)

arrow(ax, CX, 12.26, CX, 11.84)
arrow(ax, CX, 11.16, CX, 10.74)
arrow(ax, CX, 10.06, CX, 9.68)

diamond(ax, CX, 7.85, 4.2, 1.35,
        "Do all three hashes match\nsomething already stored?", fs=8.2)
arrow(ax, CX, 8.82, CX, 8.53)

# yes, to the left
arrow(ax, CX - 2.10, 7.85, LX + 0.02, 7.85, "yes")
box(ax, LX, 6.75, AW, 0.92,
    "Decompress the stored copy\nand compare it byte for byte", MID, 1.5)
arrow(ax, LX, 7.39, LX, 7.21)

# no, to the right
arrow(ax, CX + 2.10, 7.85, RX - 0.02, 7.85, "no", side="left")
box(ax, RX, 6.75, AW, 0.92, "Compress it with zlib\nand store it as new content", LIGHT)
arrow(ax, RX, 7.39, RX, 7.21)

# the two outcomes of the byte comparison
box(ax, LX - 0.98, 5.35, 1.86, 1.0, "Identical:\nreuse it and write\na reference",
    LIGHT, fs=7.6)
box(ax, LX + 0.98, 5.35, 1.86, 1.0, "Different:\nstore it as\nnew content", WHITE, fs=7.6)
arrow(ax, LX - 0.98, 6.29, LX - 0.98, 5.85)
arrow(ax, LX + 0.98, 6.29, LX + 0.98, 5.85)

# everything lands in the database
box(ax, CX, 3.95, 7.4, 0.78, "The SQLite database  (Figure 2)", WHITE, 1.4, bold=True)
arrow(ax, LX - 0.98, 4.85, LX - 0.98, 4.34)
arrow(ax, LX + 0.98, 4.85, LX + 0.98, 4.34)
arrow(ax, RX, 6.29, RX, 4.34)

# screening runs afterwards, on the unique contents only
box(ax, CX, 2.6, 5.4, 0.78, "Look each unique file up in the NSRL\n(SHA-1 and SHA-256)",
    LIGHT)
arrow(ax, CX, 3.56, CX, 2.99)
box(ax, CX, 1.25, 5.4, 0.78,
    "Send what the NSRL does not recognise\nto VirusTotal", LIGHT)
arrow(ax, CX, 2.21, CX, 1.64)

ax.set_xlim(0, 10)
ax.set_ylim(0.6, 13.3)
ax.axis("off")
fig.savefig(OUT + "fig_3_1_pipeline.png")
plt.close(fig)
print("wrote fig_3_1_pipeline.png")

# ===================================================================== Fig 3.2
# file_refs sits in the middle, so both foreign keys point outward and neither
# arrow crosses a box. Three rectangles and two arrows: SmartArt can do this.
fig, ax = plt.subplots(figsize=(7.2, 2.3))

box(ax, 1.55, 2.3, 2.4, 1.2,
    "images\n\none row per\nevidence image", WHITE, fs=8.0)
box(ax, 5.00, 2.3, 2.4, 1.2,
    "file_refs\n\none row per\noccurrence of a file,\nwith its path", LIGHT, 1.5, fs=8.0)
box(ax, 8.60, 2.3, 2.3, 1.2,
    "content_store\n\none row per unique\ncontent, compressed", MID, fs=8.0)

# Foreign keys drawn outward from file_refs. Each label sits in the gap between
# two boxes, just above its arrow, so it touches neither a border nor the line.
for x1, x2, lab in [(3.76, 2.79, "image_id"), (6.24, 7.42, "content_id")]:
    ax.add_patch(FancyArrowPatch((x1, 2.3), (x2, 2.3), arrowstyle="-|>",
                                 mutation_scale=11, color=INK, linewidth=1.0))
    ax.text((x1 + x2) / 2, 2.58, lab, fontsize=7.4, color=INK, style="italic",
            ha="center", va="center")

ax.add_patch(Rectangle((0.15, 1.45), 9.7, 1.65, facecolor="none",
                       edgecolor=INK, linewidth=0.9, linestyle=(0, (2, 2))))
ax.text(0.38, 3.24, "One database per evidence set", fontsize=8.4,
        style="italic", color=INK)

ax.set_xlim(0, 10)
ax.set_ylim(1.3, 3.5)
ax.axis("off")
fig.savefig(OUT + "fig_3_2_schema.png")
plt.close(fig)
print("wrote fig_3_2_schema.png")

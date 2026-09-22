# How the figures were made, and how to remake them

Written so the question "how did you produce these?" has a complete answer, and so
any figure can be rebuilt from scratch without running this project's code.

---

## The short answer

**Every figure is original.** Nothing is reproduced, adapted or traced from any
published paper, textbook or website. There is nothing to attribute.

- **Figures 1 and 2** are diagrams of the system built for this project, drawn from
  the code and schema in Chapter 3.
- **Figures 3 to 7** are charts plotted directly from this project's own
  measurements, which came from SQL queries against the nine evidence databases.

The chain is: **evidence image → extraction pipeline → SQLite database → SQL query →
CSV → chart.** Every step is in this repository.

---

## Figure numbers and filenames

The dissertation numbers its figures 1 to 7. The files keep the chapter-based names
they were first given, so that nothing linking to them broke when the numbering
changed.

| Figure | File | Drawn by | Data file |
|---|---|---|---|
| 1 | `fig_3_1_pipeline.png` | `make_fig_3_1_and_3_2.py` | none: a diagram |
| 2 | `fig_3_2_schema.png` | `make_fig_3_1_and_3_2.py` | none: a diagram |
| 3 | `fig_4_1_savings.png` | `make_figures.py` | `fig_4_1_savings.csv` |
| 4 | `fig_4_2_shortfall.png` | `make_figures.py` | `fig_4_2_shortfall.csv` |
| 5 | `fig_4_3_overhead.png` | `make_fig_4_3_overhead.py` | `fig_4_3_overhead.csv` |
| 6 | `fig_4_4_nsrl.png` | `make_figures.py` | `fig_4_4_nsrl.csv` |
| 7 | `fig_4_5_funnel.png` | `make_fig_4_5_funnel.py` | `fig_4_5_funnel.csv` |

---

## Where the numbers come from

Each chart's underlying data is saved as a spreadsheet in `figures/data/`. The CSVs
carry the raw counts as well as the percentages, so any figure can be checked
arithmetically without opening a database. Every value traces back to an entry in
`project_audit_log.md`, where the query that produced it is recorded.

---

## Rebuilding a figure in Excel or Google Sheets

No programming needed. Open the CSV and:

**Figure 3, grouped bar chart.** Select all four columns → Insert → Bar Chart →
Clustered Bar. Sort rows by "Both together" descending first if you want the same
order. HFS+ has a genuine 0.00 for deduplication, so that bar is absent by design;
label it rather than letting it look like missing data.

**Figure 4, scatter with a trend line.** Select the two numeric columns →
Insert → Scatter. Right-click a point → Add Trendline → Linear, and tick "Display
equation" to get the slope. Add data labels from the evidence-set column.

**Figure 5, log-log scatter.** Insert → Scatter with two series, container
overhead and schema overhead, each plotted against average stored bytes per unique
file. Double-click each axis and tick "Logarithmic scale". Container overhead is
drawn as open triangles; schema overhead as filled circles joined by a line.

**Figure 6, grouped bar on a log axis.** Insert → Bar Chart → Clustered Bar,
then set the value axis to logarithmic. **Two values are true zeros** (Android
sdcard and mtd7, by volume). A logarithmic axis cannot draw a zero, so those bars
are deliberately absent and labelled "0.00 (no bytes matched)". Do not substitute
a small number to make a bar appear: that misrepresents the measurement.

**Figure 7, funnel.** Excel's Insert → Chart → Funnel works directly on the Stage and
Count columns. The box widths in the dissertation are stylised rather than
proportional: at true scale the last box, 34 against 80,260, would be invisible.

**Figures 1 and 2** are diagrams, not charts. They were originally one diagram
that combined a process flow with a schema diagram, which made it crowded: the
`image_id` connector was drawn as a curve straight through two other boxes, the
`content_id` label sat on a border, the "bytes differ" arrow crossed diagonally over
the `images` box, and an arrow ran from VirusTotal screening into `file_refs`, which
is not a relationship that exists. Splitting them fixed all four.

Both are now laid out on a fixed grid, with every box in one of three columns and
every connector either straight down or straight across. **Nothing crosses anything.**
That is what makes them redrawable by hand.

**Figure 1, the pipeline — in PowerPoint.** Insert → SmartArt → Process → *Vertical
Process* gives the four boxes down the spine (evidence image, mount read-only, walk the
filesystem, read and hash). For the branch, leave SmartArt and use Insert → Shapes: one
*Diamond* for the decision, then rectangles for the two arms, and *Arrow* connectors.
Set every shape to the same size, then use Format → Align → Align Center and
Distribute Vertically so the spacing is even. Ten minutes' work.

**Figure 1 — in draw.io (diagrams.net), which is free and needs no account.** Faster
than SmartArt for anything with a branch: drag a rounded rectangle for each box, a
rhombus for the decision, and drag from a shape's edge to draw a connector. Use
Arrange → Align to line the columns up. Export as PNG at 300 dpi.

**Figure 2, the schema.** Three rectangles in a row and two arrows. SmartArt's
Insert → SmartArt → Process → *Basic Process* does it directly; delete the third
arrow, then reverse the first so both point outward from `file_refs` in the middle.
Put the two labels in the gaps between boxes, not on the boxes.

Keeping `file_refs` in the middle is the whole trick. It is the table that points at
the other two, so placing it between them means both foreign-key arrows run outward
and neither has to cross anything.

---

## Rebuilding them exactly as they appear

The originals were plotted with Python and matplotlib. You need Python with matplotlib
installed (`pip install matplotlib`). Each script writes its figure beside itself.

```bash
python make_fig_3_1_and_3_2.py     # Figures 1 and 2
python make_figures.py             # Figures 3, 4 and 6
python make_fig_4_3_overhead.py    # Figure 5
python make_fig_4_5_funnel.py      # Figure 7
```

The order no longer matters. An older version of Figure 5 used to be drawn by
`make_figures.py` as well, and running the two in the wrong order silently replaced
the current figure with the old one. That block has been removed.

Three of the scripts hold their values as literals, which match the CSVs above.
`make_fig_4_5_funnel.py` reads `fig_4_5_funnel.csv` directly, so it cannot disagree
with its own data file. Every derived value in the CSVs was recomputed from their raw
counts and checked against the dissertation's Chapter 4 before submission.

Everything is rendered at 300 dpi in greyscale, so the figures survive black and
white printing and remain readable if the dissertation is photocopied.

---

## Checking a figure against its data

Every chart's values are in `data/` as a CSV, carrying the raw counts as well as
the percentages. Any figure can therefore be checked arithmetically without opening
a database or running a line of this code: divide the counts yourself and compare.

Each value was recomputed from those raw counts and checked against Chapter 4
before submission. Where that checking found an error, it is recorded below rather
than quietly corrected.

---

## Correction log

**4 September 2026, Figure 6 (then 4.4).** An earlier version drew a visible bar at
0.005% for Android sdcard and Android mtd7 under "by volume", where the true measured
value for both is **0.00%**. The substitution had been made so that a bar would
render on a logarithmic axis. It misrepresented the data and was corrected: a zero
now draws no bar and is labelled as zero. Recorded here because a figure that
overstates a result, even slightly, is the kind of error worth documenting rather
than quietly fixing.

**22 September 2026, all seven figures.** Every figure carried a title inside the
image as well as a caption beneath it in the dissertation. The titles were removed,
and checking them first showed that three made claims the data did not support:

- **Figure 6** was titled as if known-file coverage *always* resolves less volume than
  files. It does not: Android mtd6 is 1.62% by file count and 3.76% by volume, and
  the chart's own bars showed it. The dissertation's text had it right, saying eight
  of the nine sets.
- **Figure 2** carried a footnote calling the gap between the two tables' row counts
  "the saving SQ3 measures". The research questions are numbered Q1 to Q4, and the
  footnote mixed two of them: the saving is Q1's, while Q3 measures what the growing
  reference table costs.
- **Figure 7** carried a footnote saying 80,260 files reduced to 34 "needing a human
  decision". That implied the other 8,019 unflagged files were cleared, which the
  dissertation expressly does not claim: a file with no detection has not been shown
  to be clean.

Every plotted value was checked at the same time and none was wrong: the errors were
all in text written onto the charts, not in the data drawn on them. Two label
collisions were also fixed, in Figure 4 and Figure 5, and Figure 7 was given a script
for the first time, having previously been drawn by hand.

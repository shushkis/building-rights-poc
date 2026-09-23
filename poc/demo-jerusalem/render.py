# -*- coding: utf-8 -*-
"""
Slide-ready still of the Beit HaKerem run, drawn straight from buildings.geojson.

No basemap tiles: nothing to re-shoot later, no attribution to place, and the
polygons carry the whole picture anyway. Two panels, because the honest story is
a comparison rather than a single map - what the municipal record already says,
and what the height model reconstructs where the record is silent.

Writes figure-6-beit-hakerem.jpg next to this file.
"""
from __future__ import annotations

import json
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.collections import PatchCollection  # noqa: E402
from matplotlib.patches import Polygon as MplPoly  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
P = lambda n: os.path.join(HERE, n)  # noqa: E731

BG, INK, MUTED, CYAN, GOLD = "#080C12", "#FFFFFF", "#7A8896", "#8ED3E9", "#E8B64C"
RAMP = {1: "#39424E", 2: "#4A5668", 3: "#6E6A54", 4: "#B08B2E",
        5: "#D89A3D", 6: "#E2703A", 7: "#D4553A", 8: "#B8383B"}
TIER = {"granted": "#5FD39A", "approved": "#E8B64C", "planning": "#7B5CD6"}


def colour(n):
    if not n:
        return "#2A2F3C"
    return "#A4243B" if n >= 9 else RAMP.get(n, "#39424E")


gj = json.load(open(P("buildings.geojson"), encoding="utf-8"))
st = json.load(open(P("stats.json"), encoding="utf-8"))
bnd = json.load(open(P("boundary.geojson"), encoding="utf-8"))

feats = [f for f in gj["features"] if f["properties"]["in_neighbourhood"]]
lats = [p[1] for f in feats for r in f["geometry"]["coordinates"] for p in r]
lons = [p[0] for f in feats for r in f["geometry"]["coordinates"] for p in r]
kx = math.cos(math.radians(sum(lats) / len(lats)))

fig = plt.figure(figsize=(16, 9), dpi=110)
fig.patch.set_facecolor(BG)

PANELS = [
    ([0.005, 0.115, 0.495, 0.685], "asbuilt"),
    ([0.500, 0.115, 0.495, 0.685], "gap"),
]

for rect, mode in PANELS:
    ax = fig.add_axes(rect)
    ax.set_facecolor(BG)
    patches, colours = [], []
    for f in feats:
        p = f["properties"]
        if mode == "asbuilt":
            c = colour(p["floors"])
        else:
            # the gap panel lights only the properties the city has ruled on
            c = TIER.get(p.get("tier"), "#181C24")
        for ring in f["geometry"]["coordinates"]:
            patches.append(MplPoly([(x * kx, y) for x, y in ring], closed=True))
            colours.append(c)
    ax.add_collection(PatchCollection(patches, facecolors=colours,
                                      edgecolors="none", linewidths=0))
    for f in bnd["features"]:
        for ring in f["geometry"]["coordinates"]:
            ax.add_patch(MplPoly([(x * kx, y) for x, y in ring], closed=True,
                                 fill=False, edgecolor=GOLD, linewidth=0.9,
                                 linestyle=(0, (4, 3)), alpha=0.55))
    x0, x1 = min(lons) * kx, max(lons) * kx
    y0, y1 = min(lats), max(lats)
    px, py = (x1 - x0) * 0.03, (y1 - y0) * 0.03
    ax.set_xlim(x0 - px, x1 + px)
    ax.set_ylim(y0 - py, y1 + py)
    ax.set_aspect("equal")
    ax.axis("off")

# ---- header ----
fig.text(0.012, 0.962, "Beit HaKerem, Jerusalem", color=INK, fontsize=22,
         fontweight="bold", va="center")
fig.text(0.012, 0.918,
         "Second city. As-built from the record; the gap where the city has ruled.",
         color=MUTED, fontsize=12, va="center")

T = st["tiers"]
cards = [("%d" % st["buildings_analyzed"], "buildings in the neighbourhood"),
         ("%d%%" % st["pct_municipal"], "floor count from the city"),
         ("%d" % st["units_added_headline"], "added units - permitted/approved"),
         ("%d" % st["units_added_planning"], "in planning - not in headline")]
x = 0.385
for big, lab in cards:
    fig.text(x, 0.962, big, color=CYAN, fontsize=19, fontweight="bold", va="center")
    fig.text(x, 0.918, lab, color=MUTED, fontsize=8.8, va="center")
    x += 0.153

# ---- panel captions ----
fig.text(0.253, 0.845, "As-built", color=INK, fontsize=13, fontweight="bold", ha="center")
fig.text(0.253, 0.812, "%d of %d buildings carry a municipal floor count on the polygon"
         % (st["with_municipal_floors"], st["buildings_analyzed"]),
         color=MUTED, fontsize=10, ha="center")
fig.text(0.748, 0.845, "Published entitlement", color=INK, fontsize=13,
         fontweight="bold", ha="center")
fig.text(0.748, 0.812,
         "%d properties the city has ruled on - the rest carry no published quantity"
         % st["buildings_with_gap"], color=MUTED, fontsize=10, ha="center")

# ---- legend ----
lx, ly = 0.016, 0.320
fig.text(lx, ly + 0.038, "floors", color=MUTED, fontsize=10, fontweight="bold")
for i, (lo, txt) in enumerate([(1, "1-2"), (3, "3-4"), (5, "5-6"),
                               (7, "7-8"), (9, "9+")]):
    fig.patches.append(plt.Rectangle((lx, ly - i * 0.034), 0.014, 0.021,
                                     facecolor=colour(lo), edgecolor="none",
                                     transform=fig.transFigure, figure=fig))
    fig.text(lx + 0.021, ly - i * 0.034 + 0.010, txt, color=MUTED, fontsize=9.5,
             va="center")

rx, ry = 0.512, 0.320
fig.text(rx, ry + 0.038, "entitlement", color=MUTED, fontsize=10, fontweight="bold")
_tiers = [("granted", "permit issued  %d units" % T["granted"]["units_added"]),
          ("approved", "approved  %d units" % T["approved"]["units_added"]),
          ("planning", "in planning  %d - NOT a right" % T["planning"]["units_added"])]
for i, (key, txt) in enumerate(_tiers):
    fig.patches.append(plt.Rectangle((rx, ry - i * 0.034), 0.014, 0.021,
                                     facecolor=TIER[key], edgecolor="none",
                                     transform=fig.transFigure, figure=fig))
    fig.text(rx + 0.021, ry - i * 0.034 + 0.010, txt, color=MUTED, fontsize=9.5,
             va="center")

# ---- footer: the claim, and the limit on it ----
ho = st["fallback_heldout"]
fig.text(0.012, 0.072,
         "Jerusalem publishes a floor count on the building polygon: %d of %d buildings (%.0f%%). "
         "Only %d need a model at all, and that fallback was fitted on %d buildings and tested on "
         "%d it never saw - %.0f%% within +/-1 floor."
         % (st["with_municipal_floors"], st["buildings_analyzed"], st["pct_municipal"],
            st["with_derived_only"], st["fallback_train_n"], ho["n"], ho["within1_pct"]),
         color=INK, fontsize=10.5, va="center")
fig.text(0.012, 0.043,
         "The gap is read, not modelled: urban-renewal files publish existing and entitled ADDED "
         "dwelling units per property. %d units are permitted or approved across %d files; a further "
         "%d sit in schemes still in planning and are held out of the headline entirely."
         % (st["units_added_headline"], T["granted"]["files"] + T["approved"]["files"],
            st["units_added_planning"]),
         color=MUTED, fontsize=8.6, va="center")
fig.text(0.012, 0.017,
         "For the other %d buildings no entitlement quantity is published and none is invented: "
         "%d carry the plan, the plot and the land-use class - the join key, not the number.   "
         "Source: Jerusalem Municipality public ArcGIS Server, gisviewer.jerusalem.muni.il."
         % (st["buildings_without_entitlement"], st["with_join_key"]),
         color=MUTED, fontsize=8.6, va="center")

out = P("figure-6-beit-hakerem.jpg")
fig.savefig(out, facecolor=BG, dpi=110,
            pil_kwargs={"quality": 88, "optimize": True, "progressive": True})
print("wrote %s  (%.0f KB)" % (out, os.path.getsize(out) / 1024.0))

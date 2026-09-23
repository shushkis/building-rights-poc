# -*- coding: utf-8 -*-
"""
Beit HaKerem, Jerusalem - build the demo payload from the cached municipal layers.

What this run claims, and what it does not.

  AS-BUILT is read, not modelled. The city publishes a floor count on the
  building polygon (layer 370). Where it is present it is used verbatim. Where
  it is absent, floors are derived from the published height using a constant
  FITTED ON THE LABELLED BUILDINGS AND TESTED ON A HELD-OUT HALF - so the
  fallback ships with a measured error rate rather than an assumed one.

  ENTITLEMENT is read where the city has ruled on it. Urban-renewal files
  (TAMA 38, layer 63; clearance-and-rebuild, layer 183) publish existing and
  entitled ADDED dwelling units per property. That difference is a real, cited
  rights gap, and it is computed only for the properties those files cover.

  NO GAP IS INVENTED FOR ANYTHING ELSE. Every other building carries the plan
  (TABA), the plot inside it (MIGRASH) and the land-use class (YEUD) from the
  compiled land-use layer - the join key an entitlement lookup would need - and
  an explicitly empty gap. Turning that class into a permitted floor count needs
  a rules table authored from the plan documents: the Tel Aviv Rova 3
  construction, deliberately not attempted here.

Outputs, mirroring poc/demo: buildings.geojson, renewal.geojson, plans.geojson,
boundary.geojson, stats.json, validation.json.
"""
from __future__ import annotations

import json
import os
import random
import statistics
from collections import Counter, defaultdict

import fetch

HERE = os.path.dirname(os.path.abspath(__file__))


def P(name):
    return os.path.join(HERE, name)


# ---------------------------------------------------------------- geometry
def ring_bbox(ring):
    xs = [p[0] for p in ring]
    ys = [p[1] for p in ring]
    return min(xs), min(ys), max(xs), max(ys)


def rings_bbox(rings):
    bs = [ring_bbox(r) for r in rings]
    return (min(b[0] for b in bs), min(b[1] for b in bs),
            max(b[2] for b in bs), max(b[3] for b in bs))


def point_in_rings(x, y, rings, bbox=None):
    """Even-odd ray cast across every ring, so holes subtract correctly."""
    if bbox is None:
        bbox = rings_bbox(rings)
    if not (bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]):
        return False
    inside = False
    for ring in rings:
        n = len(ring)
        j = n - 1
        for i in range(n):
            xi, yi = ring[i][0], ring[i][1]
            xj, yj = ring[j][0], ring[j][1]
            if (yi > y) != (yj > y):
                if x < (xj - xi) * (y - yi) / (yj - yi) + xi:
                    inside = not inside
            j = i
    return inside


def ring_centroid(ring):
    a = cx = cy = 0.0
    n = len(ring)
    for i in range(n):
        x0, y0 = ring[i][0], ring[i][1]
        x1, y1 = ring[(i + 1) % n][0], ring[(i + 1) % n][1]
        cross = x0 * y1 - x1 * y0
        a += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    if abs(a) < 1e-14:
        return (sum(p[0] for p in ring) / n, sum(p[1] for p in ring) / n)
    a *= 0.5
    return (cx / (6 * a), cy / (6 * a))


class Grid:
    """Uniform bucket index; enough for a 1.5 km neighbourhood, no shapely."""

    def __init__(self, items, cell=0.0015):
        self.cell = cell
        self.buckets = defaultdict(list)
        for it in items:
            b = it["bbox"]
            for gx in range(int(b[0] / cell), int(b[2] / cell) + 1):
                for gy in range(int(b[1] / cell), int(b[3] / cell) + 1):
                    self.buckets[(gx, gy)].append(it)

    def at(self, x, y):
        return self.buckets.get((int(x / self.cell), int(y / self.cell)), [])


def as_polys(features):
    out = []
    for f in features:
        rings = (f.get("geometry") or {}).get("rings")
        if not rings:
            continue
        out.append({"rings": rings, "bbox": rings_bbox(rings), "a": f["attributes"]})
    return out


def blank(v):
    return v is None or (isinstance(v, str) and not v.strip())


def clean(v):
    return None if blank(v) else (v.strip() if isinstance(v, str) else v)


# ---------------------------------------------------------------- load
data = fetch.main()
BLD = data["buildings"]
T38, PINUI = data["tama38"], data["pinui"]
LU, PARC, PLAN, BND = data["landuse"], data["parcels"], data["plans"], data["boundary"]

boundary = as_polys(BND)
print("neighbourhood boundary polygons: %d" % len(boundary))

# ---------------------------------------------------------------- assemble
lu_polys = as_polys(LU)
parcel_polys = as_polys(PARC)
plan_polys = as_polys(PLAN)
lu_grid = Grid(lu_polys)
parcel_grid = Grid(parcel_polys)
plan_grid = Grid(plan_polys, cell=0.004)

buildings = []
for f in BLD:
    a = f["attributes"]
    rings = (f.get("geometry") or {}).get("rings")
    if not rings:
        continue
    bbox = rings_bbox(rings)
    cx, cy = ring_centroid(max(rings, key=len))

    floors_m = a.get("NUM_FLOORS")
    floors_m = int(floors_m) if floors_m else None
    height = a.get("MAX_rel_he") or a.get("MAX_med_he")
    height = round(float(height), 1) if height else None

    street, num = clean(a.get("StreetName")), clean(a.get("BldNum_1"))
    address = ("%s %s" % (street, num)).strip() if street else None

    inside = any(point_in_rings(cx, cy, b["rings"], b["bbox"]) for b in boundary)

    gush = helka = legal_area = None
    for p in parcel_grid.at(cx, cy):
        if point_in_rings(cx, cy, p["rings"], p["bbox"]):
            gush = clean(p["a"].get("GUSH_NO"))
            helka = clean(p["a"].get("HELKA_SHOW"))
            legal_area = clean(p["a"].get("LEGAL_AREA"))
            break

    taba = migrash = yeud = yeud_descr = None
    for p in lu_grid.at(cx, cy):
        if point_in_rings(cx, cy, p["rings"], p["bbox"]):
            taba = clean(p["a"].get("TABA"))
            migrash = clean(p["a"].get("MIGRASH"))
            yeud = clean(p["a"].get("YEUD"))
            yeud_descr = clean(p["a"].get("Descr"))
            break

    plans = []
    for p in plan_grid.at(cx, cy):
        if point_in_rings(cx, cy, p["rings"], p["bbox"]):
            t = clean(p["a"].get("TABA"))
            if t:
                plans.append(t)

    buildings.append({
        "rings": rings, "bbox": bbox, "cx": cx, "cy": cy,
        "floors_municipal": floors_m, "height": height,
        "apartments": int(a.get("NUM_APTS_C") or 0) or None,
        "entrances": int(a.get("NUM_ENTR_1") or 0) or None,
        "address": address, "gush": gush, "helka": helka, "legal_area": legal_area,
        "taba": taba, "migrash": migrash, "yeud": yeud, "yeud_descr": yeud_descr,
        "plans": sorted(set(plans)),
        "in_neighbourhood": inside,
        "renewals": [],
    })

inn = [b for b in buildings if b["in_neighbourhood"]]
labelled = [b for b in inn if b["floors_municipal"] and b["height"]]
print("buildings pulled: %d  (inside the neighbourhood boundary: %d)"
      % (len(buildings), len(inn)))
print("  with a municipal floor count: %d (%.0f%%)"
      % (sum(1 for b in inn if b["floors_municipal"]),
         100.0 * sum(1 for b in inn if b["floors_municipal"]) / max(len(inn), 1)))

# ------------------------------------------- height fallback, fitted and tested
# Only the buildings the city did not label need a model at all. Fit the
# metres-per-floor constant on half the labelled buildings and score it on the
# half it never saw, so the fallback ships with a measured error rate.
rng = random.Random(20260903)
order = list(range(len(labelled)))
rng.shuffle(order)
half = len(order) // 2
train = [labelled[i] for i in order[:half]]
test = [labelled[i] for i in order[half:]]
MED = statistics.median(b["height"] / b["floors_municipal"] for b in train)
SD = statistics.pstdev(b["height"] / b["floors_municipal"] for b in train)


def derive(h):
    return max(1, int(round(h / MED))) if h else None


d = [derive(b["height"]) - b["floors_municipal"] for b in test]
nt = max(len(d), 1)
heldout = {"n": len(d),
           "exact_pct": round(100.0 * sum(1 for x in d if x == 0) / nt, 1),
           "within1_pct": round(100.0 * sum(1 for x in d if abs(x) <= 1) / nt, 1),
           "mae": round(sum(abs(x) for x in d) / nt, 2),
           "bias": round(sum(d) / nt, 2),
           "dist": dict(sorted(Counter(d).items()))}
print("\nheight fallback: %.2f m/floor (sd %.2f), fitted on %d, tested on %d"
      % (MED, SD, len(train), len(test)))
print("  held out: %.0f%% exact, %.0f%% within +/-1, MAE %.2f, bias %+.2f"
      % (heldout["exact_pct"], heldout["within1_pct"], heldout["mae"], heldout["bias"]))

for b in buildings:
    b["floors_derived"] = derive(b["height"])
    if b["floors_municipal"]:
        b["floors"] = b["floors_municipal"]
        b["floors_source"] = "municipal"
        b["floors_delta"] = (b["floors_derived"] - b["floors_municipal"]
                             if b["floors_derived"] else None)
    else:
        b["floors"] = b["floors_derived"]
        b["floors_source"] = "derived" if b["floors_derived"] else None
        b["floors_delta"] = None
    b["split"] = None
for b in train:
    b["split"] = "train"
for b in test:
    b["split"] = "test"

# ---------------------------------------------------------------- entitlement
# TAMA 38 files are points; clearance schemes are polygons. Each is attached to
# the building it lands on (or that lands inside it). Nothing is spread across
# neighbours: a file the join cannot place stays unplaced and is counted as such.
# Not every published entitlement is a granted one, and folding them together
# overstates the finding by an order of magnitude. Three tiers, on the same
# discipline the Old North run uses for its mixed-use and inferred tiers:
#   granted   - a permit has actually been issued
#   approved  - approved at the licensing committee, or a permit file opened
#   planning  - a scheme in planning. Real pipeline, NOT a right. Never in the
#               headline. Every clearance-and-rebuild scheme sits here.
TIER_BY_STATUS = {
    "הופק הוצא היתר": "granted",
    "היתר אושר בועדת רישוי": "approved",
    "נפתח תיק היתר": "approved",
    "תכנון - טרם כניסה לרישוי": "planning",
}
TIER_LABEL = {"granted": "היתר הוצא",
              "approved": "אושר / בהליך רישוי",
              "planning": "בתכנון בלבד"}

bgrid = Grid(buildings)
renewal, unplaced = [], 0

for f in T38:
    g = f.get("geometry") or {}
    x, y = g.get("x"), g.get("y")
    a = f["attributes"]
    st = clean(a.get("status"))
    rec = {"kind": "tama38", "id": a.get("OBJECTID"),
           "address": clean(a.get("address")), "status": st,
           "tier": TIER_BY_STATUS.get(st, "planning"),
           "units_existing": int(a.get("units_exists") or 0),
           "units_added": int(a.get("units_tosefet") or 0),
           "x": x, "y": y}
    hit = None
    if x is not None and y is not None:
        for b in bgrid.at(x, y):
            if point_in_rings(x, y, b["rings"], b["bbox"]):
                hit = b
                break
    if hit is None:
        unplaced += 1
    else:
        hit["renewals"].append(rec)
    rec["placed"] = hit is not None
    renewal.append(rec)

for f in PINUI:
    rings = (f.get("geometry") or {}).get("rings")
    a = f["attributes"]
    rec = {"kind": "pinui_binui", "id": a.get("OBJECTID"),
           "address": clean(a.get("adress")) or clean(a.get("name")),
           "status": clean(a.get("maslul")),
           "tier": "planning",          # a scheme, never a granted right
           "units_existing": int(a.get("units_e") or 0),
           "units_added": int(a.get("units_a") or 0),
           "units_planned": int(a.get("units_p") or 0),
           "rings": rings}
    n_hit = 0
    if rings:
        bb = rings_bbox(rings)
        for b in buildings:
            if point_in_rings(b["cx"], b["cy"], rings, bb):
                b["renewals"].append(dict(rec, shared=True))
                n_hit += 1
    rec["buildings_covered"] = n_hit
    rec["placed"] = n_hit > 0
    if n_hit == 0:
        unplaced += 1
    renewal.append(rec)

RANK = {"granted": 0, "approved": 1, "planning": 2}
for b in buildings:
    rs = [r for r in b["renewals"] if r.get("units_added")]
    b["renewal_n"] = len(rs)
    b["units_added"] = sum(r["units_added"] for r in rs) or None
    b["units_existing"] = sum(r["units_existing"] for r in rs) or None
    b["renewal_kind"] = rs[0]["kind"] if rs else None
    # a footprint can carry files at different stages; it is coloured by the
    # strongest one, and the popup lists every file behind it
    b["tier"] = min((r["tier"] for r in rs), key=lambda t: RANK[t]) if rs else None
    b["renewal_status"] = (min(rs, key=lambda r: RANK[r["tier"]])["status"]
                           if rs else None)
    b["renewal_addresses"] = [r["address"] for r in rs if r.get("address")]

with_gap = [b for b in inn if b["units_added"]]
t38 = [r for r in renewal if r["kind"] == "tama38"]
pin = [r for r in renewal if r["kind"] == "pinui_binui"]


def tier_totals(tier):
    # units are summed over FILES (each is a distinct property/address);
    # buildings counts the footprints those files render on, which is smaller
    # because one polygon can cover a multi-entrance block.
    rs = [r for r in renewal if r.get("tier") == tier and r.get("units_added")]
    bs = [b for b in inn if b["tier"] == tier and b["units_added"]]
    return {"files": len(rs), "buildings": len(bs),
            "units_existing": sum(r["units_existing"] for r in rs),
            "units_added": sum(r["units_added"] for r in rs)}


TIERS = {t: tier_totals(t) for t in ("granted", "approved", "planning")}
headline = TIERS["granted"]["units_added"] + TIERS["approved"]["units_added"]
buildings_headline = TIERS["granted"]["buildings"] + TIERS["approved"]["buildings"]
units_existing = sum(r["units_existing"] for r in renewal)
units_added = sum(r["units_added"] for r in renewal)
print("")
print("renewal files: %d TAMA 38 + %d clearance  (%d unplaceable on a footprint)"
      % (len(t38), len(pin), unplaced))
for t in ("granted", "approved", "planning"):
    v = TIERS[t]
    print("  %-9s %3d files / %3d buildings   %5d existing -> %5d added units"
          % (t, v["files"], v["buildings"], v["units_existing"], v["units_added"]))
print("  HEADLINE (granted + approved): %d added units on %d buildings"
      % (headline, buildings_headline))
print("  held separate (planning only): %d added units - real pipeline, not a right"
      % TIERS["planning"]["units_added"])
print("  buildings carrying any published entitlement: %d" % len(with_gap))

no_gap = [b for b in inn if not b["units_added"]]
print("  buildings with NO entitlement published: %d  "
      "(of which %d carry a plan + plot + land-use class)"
      % (len(no_gap), sum(1 for b in no_gap if b["taba"] and b["yeud_descr"])))

# ---------------------------------------------------------------- stats
stats = {
    "neighborhood": "בית הכרם, ירושלים",
    "neighborhood_en": "Beit HaKerem, Jerusalem",
    "buildings_analyzed": len(inn),
    "buildings_in_bbox": len(buildings),
    "with_municipal_floors": sum(1 for b in inn if b["floors_municipal"]),
    "with_derived_only": sum(1 for b in inn if b["floors_source"] == "derived"),
    "pct_municipal": round(100.0 * sum(1 for b in inn if b["floors_municipal"])
                           / max(len(inn), 1), 1),
    "apartments": sum(b["apartments"] or 0 for b in inn),
    "median_m_per_floor": round(MED, 2),
    "fallback_sd": round(SD, 2),
    "fallback_train_n": len(train),
    "fallback_heldout": heldout,
    "renewal_files": len(renewal),
    "renewal_tama38": len(t38),
    "renewal_pinui": len(pin),
    "renewal_unplaced": unplaced,
    "buildings_with_gap": len(with_gap),
    "tiers": TIERS,
    "units_added_headline": headline,
    "buildings_headline": buildings_headline,
    "units_added_planning": TIERS["planning"]["units_added"],
    "gap_rows": sum(1 for r in renewal if r.get("units_added")),
    "gap_rows_unplaced": sum(1 for r in renewal
                             if r.get("units_added") and not r.get("placed")),
    "units_headline_unplaced": sum(r["units_added"] for r in renewal
                                   if r.get("units_added") and not r.get("placed")
                                   and r.get("tier") in ("granted", "approved")),
    "buildings_without_entitlement": len(no_gap),
    "with_join_key": sum(1 for b in no_gap if b["taba"] and b["yeud_descr"]),
    "units_existing": units_existing,
    "units_added": units_added,
    "units_uplift_pct": round(100.0 * units_added / max(units_existing, 1), 1),
    "plans_overlapping": len({t for b in inn for t in b["plans"]}),
    "landuse_classes": dict(Counter(b["yeud_descr"] for b in inn
                                    if b["yeud_descr"]).most_common(12)),
    "renewal_status": dict(Counter(r["status"] for r in t38 if r["status"]).most_common(8)),
    "source": ("Jerusalem Municipality public ArcGIS Server "
               "(gisviewer.jerusalem.muni.il), layers 370 buildings-2022, "
               "63 TAMA 38, 183 clearance schemes, 50 compiled land use, "
               "46 parcels, 49 plan boundaries, 40 neighbourhoods"),
}


# ---------------------------------------------------------------- write
def rd(rings, nd=6):
    return [[[round(p[0], nd), round(p[1], nd)] for p in r] for r in rings]


EXPORT = ["address", "gush", "helka", "legal_area", "height", "floors",
          "floors_source", "floors_derived", "floors_municipal", "floors_delta",
          "apartments", "entrances", "taba", "migrash", "yeud", "yeud_descr",
          "in_neighbourhood", "split"]

features = []
for i, b in enumerate(buildings):
    b["id"] = i
    props = {k: b.get(k) for k in EXPORT}
    props["id"] = i
    props["gush_helka"] = ("%s/%s" % (b["gush"], b["helka"])) if b["gush"] else None
    props["plans_n"] = len(b["plans"])
    props["plans"] = ", ".join(b["plans"][:6])
    for k in ("renewal_kind", "renewal_status", "units_existing", "units_added",
              "tier", "renewal_n"):
        props[k] = b.get(k)
    props["tier_label"] = TIER_LABEL.get(b.get("tier"))
    props["renewal_addresses"] = ", ".join(b.get("renewal_addresses") or [])[:160]
    props["has_gap"] = bool(b.get("units_added"))
    props["in_headline"] = bool(b.get("units_added")
                                and b.get("tier") in ("granted", "approved"))
    features.append({"type": "Feature",
                     "geometry": {"type": "Polygon", "coordinates": rd(b["rings"])},
                     "properties": props})

with open(P("buildings.geojson"), "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": features}, fh,
              ensure_ascii=False, separators=(",", ":"))

ren_feats = []
for r in renewal:
    if r["kind"] == "tama38" and r.get("x") is not None:
        geom = {"type": "Point", "coordinates": [round(r["x"], 6), round(r["y"], 6)]}
    elif r.get("rings"):
        geom = {"type": "Polygon", "coordinates": rd(r["rings"], 5)}
    else:
        continue
    ren_feats.append({"type": "Feature", "geometry": geom,
                      "properties": {k: v for k, v in r.items()
                                     if k not in ("rings", "x", "y")}})
with open(P("renewal.geojson"), "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection", "features": ren_feats}, fh,
              ensure_ascii=False, separators=(",", ":"))

with open(P("plans.geojson"), "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection",
               "features": [{"type": "Feature",
                             "geometry": {"type": "Polygon",
                                          "coordinates": rd(p["rings"], 5)},
                             "properties": {"taba": clean(p["a"].get("TABA"))}}
                            for p in plan_polys]},
              fh, ensure_ascii=False, separators=(",", ":"))

with open(P("boundary.geojson"), "w", encoding="utf-8") as fh:
    json.dump({"type": "FeatureCollection",
               "features": [{"type": "Feature",
                             "geometry": {"type": "Polygon",
                                          "coordinates": rd(b["rings"], 5)},
                             "properties": {}} for b in boundary]},
              fh, ensure_ascii=False, separators=(",", ":"))

# The gap table: one row per property the city has actually ruled on.
TIER_ORDER = {"granted": 0, "approved": 1, "planning": 2}
# One row per renewal FILE - the unit the city actually rules on. A footprint
# carrying several files appears once per file, which is why the row count
# exceeds the building count.
placed = {id(r): b for b in buildings for r in b["renewals"]}
out_rows = []
for r in sorted((r for r in renewal if r.get("units_added")),
                key=lambda r: (TIER_ORDER.get(r.get("tier"), 3), -r["units_added"])):
    b = placed.get(id(r))
    out_rows.append({
        "id": b["id"] if b else None,
        "address": r.get("address") or (b.get("address") if b else None),
        "gush_helka": ("%s/%s" % (b["gush"], b["helka"])) if b and b["gush"] else None,
        "kind": r["kind"], "status": r.get("status"),
        "tier": r.get("tier"), "tier_label": TIER_LABEL.get(r.get("tier")),
        "floors": b["floors"] if b else None,
        "floors_source": b["floors_source"] if b else None,
        "apartments": b["apartments"] if b else None,
        "units_existing": r.get("units_existing"),
        "units_added": r.get("units_added"),
        "uplift_pct": (round(100.0 * r["units_added"] / r["units_existing"])
                       if r.get("units_existing") else None),
        "placed": bool(r.get("placed")),
    })
with open(P("validation.json"), "w", encoding="utf-8") as fh:
    json.dump(out_rows, fh, ensure_ascii=False, indent=1)

with open(P("stats.json"), "w", encoding="utf-8") as fh:
    json.dump(stats, fh, ensure_ascii=False, indent=2)

for f in ("buildings.geojson", "renewal.geojson", "plans.geojson",
          "boundary.geojson", "validation.json", "stats.json"):
    print("  %-20s %7.2f MB" % (f, os.path.getsize(P(f)) / 1e6))
print("\n" + json.dumps(stats, ensure_ascii=False, indent=2))

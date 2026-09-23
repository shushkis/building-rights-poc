# Second City — 3-Minute Walkthrough (Beit HaKerem, Jerusalem)

**Setup:** `cd poc/demo-jerusalem && python -m http.server 8000` → open http://localhost:8000
Allow ~10s for the basemap on a cold load. Start on the **מפה** tab.

**Rebuild from scratch:** `python fetch.py --force && python build.py && python render.py`
Seven public Jerusalem layers into `_cache.json`; everything after that runs offline.

**What this is.** The Old North demo answers *how much unused right does this building
hold*. This one answers *what happens when you point the pipeline at a second city* —
and it is the corrected version of that answer. Run it after Tel Aviv, never instead.

---

## 0:00 — Start by admitting the first run was wrong (30s)

> "We ran Jerusalem two weeks ago and concluded the city publishes only half the
> computation — as-built but no rights. That conclusion was wrong, and how it was wrong
> is the most useful thing in this demo.
>
> We had queried Jerusalem's ArcGIS *Online* services. The city also runs its own ArcGIS
> Server behind its public map viewer. Its catalogue lists 157 layers; 153 returned a
> schema to an anonymous request, and we read every one of those. We had tested one
> endpoint and generalised to a city."

*This is not self-flagellation. It is the strongest possible setup for the number that follows,
because it tells the room the failure mode you look for is your own.*

---

## 0:30 — The as-built half now needs no model at all (35s)

| | |
|---|---|
| **1,100** | buildings inside the municipal neighbourhood boundary |
| **996 (90%)** | carry a **municipal floor count on the building polygon itself** |
| **104** | need a height model at all |
| **7,821** | dwelling units |

> "The first run reconstructed floors from height and reached 71% coverage through an
> address-point join, with a hundred and twenty points that landed outside every
> footprint. This layer puts the floor count on the polygon. Ninety per cent, read, not
> derived — and the join errors that topped our own validation table are simply gone."

*Click any building.* Address, gush/helka, floors, height, apartments, entrances — and the
popup says which source the floor count came from.

**The 104 that still need a model** are covered by a fallback fitted on half the labelled
buildings and tested on the half it never saw: **3.83 m/floor, 84% within ±1 floor,
bias +0.29**. It ships with a measured error rate, and it applies to under a tenth of the
neighbourhood.

---

## 1:05 — The gap, and why the number is small (60s)

*Switch to the **פער הזכויות** tab.*

> "Here is the part we said did not exist. Jerusalem's urban-renewal files publish, per
> property, how many dwelling units exist and how many may be added. That difference is
> a rights gap that we did not model, did not infer and did not price. We read it."

*Point at the four cards, in order. The order is the argument.*

| tier | files | units | what it is |
|---|---|---|---|
| **Permit issued** | 16 | **+114** | a right already granted |
| **Approved / in licensing** | 11 | **+83** | approved at committee, or a permit file opened |
| **Headline** | 27 | **197** | the only number we call a gap |
| **In planning** | 61 | *3,364* | real pipeline — **not a right** — held out entirely |

> "Three and a half thousand units are in planning across this neighbourhood, and every
> one of them is in our data. We are not putting them in the headline, because a scheme
> in planning is not an entitlement. The number we stand behind is a hundred and
> ninety-seven, and it is the smaller, boring, defensible one.
>
> If you want to know whether to trust the rest of this deck, that's the slide."

*The table is one row per file* — the file being the unit the city rules on. A single
footprint can carry several, which is why there are more rows than buildings; the popup
lists every file behind a building. Six files could not be placed on any footprint — they
are flagged in the table and still counted, so the table sums to the headline rather than
quietly falling short of it. Click any row to fly to it.

**קרית משה 7 — 18 units standing, 10 permitted, permit issued.** That is the whole product
in one line: an address, a published entitlement, and a status you could take to a
committee.

---

## 2:05 — What is still missing, precisely (40s)

*Switch to the **שאר השכונה** tab.*

> "Nine hundred and ninety-three buildings are covered by no renewal file, and we compute
> no gap for them. Not a modelled one, not an inferred one. Zero.
>
> But they are not blank. Nine hundred and twenty carry the plan that applies, the plot
> number inside that plan, and the land-use class — `5 מגורים`, `מגורים ב׳`, and about
> twenty others. That is the join key. What's missing is the *quantity* each class
> entitles."

*Point at the last table — the two empty columns are the point.*

> "So the missing input is not three hundred plan PDFs. It's a lookup table from
> land-use class to permitted floors — **38 distinct classes in this neighbourhood,
> 15 of them residential.** That is the same object we already authored for Rova 3 in
> Tel Aviv. We have deliberately not built it here, because the moment we do, this demo
> stops being something you can check."

---

## 2:45 — What the second city actually proved (25s)

> "Our report says the rules engine is the only bespoke part per city. Two weeks ago we
> said the real constraint was as-built data availability. On the evidence of two
> neighbourhoods, that is not what separates them either.
>
> Both cities publish a municipal floor count on the building. Tel Aviv's coverage is
> higher — 2,304 of 2,318, against 996 of 1,100 here — so Jerusalem is not better, it is
> comparable and slightly thinner. As-built is not the thing that varies.
>
> What varies is **where the entitlement quantity lives**. Where a renewal file exists,
> the city publishes the number. Where only a statutory plan exists, it publishes the
> class and keeps the number in the document.
>
> **That is a hypothesis from two cities and two neighbourhoods, not a finding.** A third
> city is what would make it one. But it is sharper and cheaper to test than 'the data
> doesn't travel'."

---

## Anticipated questions

**"Why is the gap only 197 units when you showed me 3,364?"**
Because 3,364 are schemes in planning, and a scheme in planning is not a right. They're on
the map in purple, in the data, and in this document — just not in the headline. We would
rather you find our caveats in our own material than in cross-examination.

**"You said Jerusalem published no rights data two weeks ago."**
We did, and we were wrong. We tested one endpoint and generalised to a city. The correction
is filed in the room with the date on it. The reason we caught it is that a colleague
opened the city's own map viewer and asked why we couldn't use it.

**"Is the municipal floor count ground truth?"**
It's a municipal record, not a survey. It's the best independent label available without
fieldwork, and where a building has both a floor count and a height, the implied 3.76 m per
floor corroborates our fitted 3.83 — two sources agreeing.

**"So Jerusalem is better documented than Tel Aviv?"**
No. Tel Aviv has a municipal floor count on 2,304 of 2,318 buildings (99.4%); Beit HaKerem
has 996 of 1,100 (90.5%). Both publish it on the building. The correction is that Jerusalem
publishes it at all — our first run said it did not.

**"Could you compute a gap for the other 993?"**
Yes, with a class→entitlement table authored from the Jerusalem 2000 master plan and the
per-TABA documents. It's a few weeks of reading, not a data problem. Pricing that is the
next question, and this run is what makes it a costable one.

**"Is Beit HaKerem representative?"**
No. It's plan-dense, low-rise and unusually renewal-active. Neither is the Old North. A
third neighbourhood with a worse data profile is the honest next test, and we'd rather run
it than argue about it.

---

## Files

| | |
|---|---|
| `fetch.py` | seven layers off Jerusalem's own ArcGIS Server → `_cache.json` |
| `build.py` | as-built join, tested height fallback, tiered entitlement, payload |
| `render.py` | slide-ready still → `figure-6-beit-hakerem.jpg` |
| `index.html` | the demo — map, the gap table, and what's still missing |
| `buildings.geojson` | 1,859 footprints: floors, source, plan, plot, land-use, entitlement |
| `renewal.geojson` | 105 urban-renewal files with existing/added units and status |
| `validation.json` | the 88-row gap table, tiered, one row per file |
| `stats.json` | every headline number on the page |
| `*_arcgisonline.*.bak` | the superseded first run, kept so the correction is auditable |

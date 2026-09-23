# 3-Minute Investor Walkthrough

**Setup:** `cd poc/demo && python -m http.server 8000` → open http://localhost:8000
Allow ~10s for the basemap on a cold load. Start on the **מפה** tab, zoomed to the neighbourhood.

---

## 0:00 — The market problem (25s)

> "Tel Aviv approved a plan in 2018 — תא/3616א, Rova 3 — that granted thousands of
> existing buildings the right to add floors. The rights are real, they're public,
> and they're written down. But nobody knows which specific buildings hold how much,
> because answering that means joining seven municipal GIS layers against a legal
> rights table, building by building.
>
> Developers and appraisers do this one address at a time, by hand, for a fee.
> We did the whole neighbourhood in ten seconds."

*Gesture at the map: 2,318 buildings, every one colour-coded by its unused rights.*

---

## 0:25 — The four numbers (30s)

*Point to the banner.*

| | |
|---|---|
| **2,318** | buildings analysed — every structure in the Old North (northern part) |
| **357,426 m²** | unexploited building rights, cited clauses only |
| **₪5.81B – ₪11.62B** | net value range to rights-holders |
| **58.8%** | analysed at HIGH confidence |

> "That range isn't hedging. The low end assumes the betterment levy applies and takes
> half. The high end assumes it doesn't — which is genuinely contested for this plan
> and currently being litigated. We show you both ends and tell you which question
> decides it. Anyone quoting a single number here is guessing."

---

## 0:55 — One building, fully traceable (50s)

*Zoom to **פרי אליעזר 11** (גוש/חלקה 6966/34) and click it.*

The popup shows:

- **Built 1958 · 4 floors today** (municipal record, corroborated by two independent height models)
- **5 floors + partial roof permitted**
- **Gap: 1 floor · 660 m²**
- **₪10.7M – ₪21.5M** net to the owner
- **Rule `R-EX-OTHER-3-6`** — *מבנה קיים 3-6 קומות ברחוב רגיל: תוספת קומה אחת + גג חלקי*
- **Confidence: HIGH**

> "Every number on this card traces back to a clause. Not a model output — a citation.
> That `rule_id` is the audit trail: building → rule → plan clause → source document.
> This is the part that survives a lawyer."

*Click a grey building nearby.* → the popup names why it scores zero: a permit already
consumed the rights, or it's listed for preservation, or a newer site-specific plan
supersedes Rova 3. **Nothing is silently dropped.**

---

## 1:45 — The ranked list (35s)

*Switch to the **50 המובילים** tab.*

> "Sorted by conservative net value. Confidence badge on every row, rule citation on
> every row. This is the acquisition target list — and it's the product. A developer
> pays for exactly this, today, produced by hand, one building at a time."

*Click any row → it flies to that building on the map.*

---

## 2:20 — Why you should believe it (25s)

> "A court ruling quantified one of these cases: a 4-floor building on a sub-500 m²
> lot, at about 369 m². Our model, run blind across 290 comparable buildings, lands at
> a median of **319 m² — 13.6% off**, inside the ±20% gate we set before looking.
>
> And we publish what's weak. The validation memo lists six systematic errors in our
> own numbers, including two where we're probably overstating. The 1-floor cohort is
> held out of the headline entirely because that entitlement is inferred, not cited.
> The purple buildings on Dizengoff and Ben Yehuda — ₪1.2B–2.4B — are shown separately
> because their residential eligibility needs per-lot confirmation.
>
> We'd rather show you the asterisk than have you find it."

---

## 2:45 — Scale (15s)

> "This neighbourhood is 1.8 km² and 2,318 buildings. Same pipeline, no new code:
> the rest of Rova 3 and Rova 4, then all of Tel Aviv, then national — the TABA layer
> that drives the rule engine is published for the whole country on GovMap.
>
> UpFactor raised €2.5M doing a weaker version of this in France. Syte raised €5M in
> Germany. Spacemaker exited to Autodesk for $240M. Nobody is doing it for Israel."

---

## Anticipated questions

**"Where does the price come from?"**
₪65,000/m² researched median for the Old North. The nadlan.gov.il deals API went behind
auth, so it's a cited published figure carried with a ±11% sensitivity band, not a live
feed. Wiring the live deal history is a known next step, not a hidden assumption.

**"Is footprint really floor area?"**
No, and we say so — it's systematic error #1 in the memo. Real added floor-plates are
smaller than the ground footprint after setbacks and cores, so gap_m² is biased upward
by an estimated 5–15%. Correcting it needs per-building envelope modelling.

**"What about the tall buildings in the top-50?"**
The plan's table grants 7+ floor buildings +2 floors, and applied literally that
includes towers. Many are caught by the newer-plan exclusion; the rest are a known
soft spot flagged in the memo.

**"Has a human checked any of this?"**
Not yet — and that's stated plainly. `validate/sample.csv` is a stratified 15-building
worksheet built for exactly that review. Appraiser sign-off is the next gate, and it is
deliberately not claimed as done.

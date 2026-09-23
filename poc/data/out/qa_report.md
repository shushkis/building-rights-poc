# QA Report — Unused Building Rights PoC

Generated: 2026-08-18 20:55
AOI: **הצפון הישן - החלק הצפוני**
Source: `https://gisn.tel-aviv.gov.il/arcgis/rest/services/WM/IView2WM/MapServer` (public, no auth)

## T1.2 — AOI

- Polygons returned: **1** (AC: exactly 1) — PASS
- Area: **1.804 km²** (AC: 0.5–2.5) — PASS

## T1.3 — Buildings

- Buildings in AOI: **2,318** (AC: > 1,000) — PASS

| field | non-null | coverage |
|---|---:|---:|
| `ms_komot` | 2,304 | 99.4% |
| `gova_simplex_2019` | 2,268 | 97.8% |
| `dsm_max` | 2,293 | 98.9% |
| `dsm_mean` | 2,306 | 99.5% |
| `min_height` | 2,268 | 97.8% |
| `year` | 2,007 | 86.6% |
| `t_amudim` | 2,226 | 96.0% |
| `t_sug_mivne` | 2,305 | 99.4% |

- `ms_komot` null: **14** (0.6%) — expected small.

### Floor-count distribution (`ms_komot`)

| floors | buildings |
|---:|---:|
| 0 | 5 |
| 1 | 392 |
| 2 | 121 |
| 3 | 617 |
| 4 | 838 |
| 5 | 209 |
| 6 | 53 |
| 7 | 29 |
| 8 | 18 |
| 9 | 1 |
| 10 | 8 |
| >10 | 13 |

### Structure types

| type | count |
|---|---:|
| מבנה רגיל | 2,085 |
| מבנה ארעי | 106 |
| מבנה ציבור | 87 |
| תחנת אוטובוס | 21 |
| לא ידוע | 3 |
| מבנה בבנייה | 2 |
| מיכל | 1 |

- Excluded as non-building type: **128**
- Excluded as footprint < 40 m²: **234**
- **Candidate buildings: 2,066**

## T1.4 — Land-use lot coverage

- Building footprint area: **508,184 m²**
- Covered by land-use lots: **508,237 m²**
- Coverage: **100.0%** (AC: ≥ 95%) — PASS

## T1.6 — Join rates

- Building → lot: **100.0%** (AC: ≥ 95%) — PASS
- Building → parcel: **100.0%**
- Buildings with ≥1 permit: **678** (29.2%)
- Buildings flagged for preservation: **77**

## T1.7 — Street assignment

| method | count | share |
|---|---:|---:|
| address_within | 2,077 | 89.6% |
| address_near | 225 | 9.7% |
| centerline | 11 | 0.5% |
| none | 5 | 0.2% |

- Assigned a street: **2,313** (99.8%)
- On Dizengoff / Ben Yehuda (enhanced rule branch): **256**

### Top streets by building count

| street | buildings |
|---|---:|
| דיזנגוף | 133 |
| בן יהודה | 123 |
| הירקון | 84 |
| סוקולוב | 79 |
| ארלוזורוב | 76 |
| נורדאו | 70 |
| יהושע בן נון | 63 |
| אבן גבירול | 53 |
| ז'בוטינסקי | 49 |
| אוסישקין | 48 |
| ירמיהו הנביא | 48 |
| בזל | 47 |
| עמוס | 46 |
| בן גוריון | 44 |
| ישעיהו | 41 |

---

## Phase 3 — Gap sanity dashboard

### As-built confidence (T3.1)

| confidence | buildings | share |
|---|---:|---:|
| HIGH | 1,363 | 58.8% |
| MEDIUM | 941 | 40.6% |
| LOW | 14 | 0.6% |

Agreement band: ±2 floors (~1σ of the DSM cross-checks; a ±1 band would read genuine agreement as disagreement).

### Exclusions (T2.2) — flagged, not dropped

| exclusion | buildings |
|---|---:|
| `EXCL_NEWER_PLAN` | 176 |
| `EXCL_PRESERVATION` | 77 |
| `EXCL_NON_RESIDENTIAL` | 648 |
| `EXCL_UNDER_CONSTRUCTION` | 84 |
| `EXCL_NOT_A_BUILDING` | 252 |
| **any** | **980** |

### Rights consumption (T2.3)

| state | buildings |
|---|---:|
| none | 1,726 |
| likely_full | 592 |

### Gap distribution

| gap_floors | buildings |
|---:|---:|
| 0 | 1,235 |
| 1 | 853 |
| 2 | 67 |
| 3 | 93 |
| 4 | 64 |
| 6 | 6 |

- Buildings with gap ≥ 1 floor: **1,083** (46.7%)

### Gap by rule clause

| rule_id | buildings | gap m² | cited? |
|---|---:|---:|---|
| `R-EX-1FL-EXTRAP` | 55 | 41,825 | extrapolated |
| `R-EX-2FL` | 59 | 38,472 | cited |
| `R-EX-7P` | 27 | 25,090 | cited |
| `R-EX-OTHER-3-6` | 847 | 295,348 | cited |
| `R-EX-SPECIAL-3P` | 95 | 65,493 | cited |

### Mean gap by street class

| street class | buildings | mean gap_floors | mean gap m² |
|---|---:|---:|---:|
| other | 980 | 1.30 | 401 |
| special | 103 | 2.80 | 709 |

### Headline vs identified upside

- **Headline** (cited clauses only): **931** buildings, **357,426 m²**
- **Upside** (extrapolated 1-floor clause): 55 buildings, 41,825 m²

The 1-floor entitlement is inferred from the 2-floor completion clause rather than cited from the plan text, and it is where the largest per-building gaps land. It is excluded from the headline by default (`config.INCLUDE_EXTRAPOLATED_IN_HEADLINE`).

### Outlier audit

- Headline rows with gap ≥ 4 floors on a non-special street: **0** (target: 0)
- Max headline gap_floors: **3**
- Headline rows with footprint < 40 m²: **0** (target: 0)

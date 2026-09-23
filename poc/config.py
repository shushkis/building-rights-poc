"""Central configuration: endpoints, layer IDs, constants.

All layer IDs below were verified live against the MapServer metadata
(see data/out/qa_report.md for the verification stamp).
"""
from pathlib import Path

# --- Data source of record -------------------------------------------------
BASE_URL = (
    "https://gisn.tel-aviv.gov.il/arcgis/rest/services/WM/IView2WM/MapServer"
)

# --- Layer IDs (verified against live service metadata) ---------------------
LAYER_NEIGHBORHOODS = 511   # שכונות
LAYER_BUILDINGS = 513       # מבנים
LAYER_LANDUSE_LOTS = 837    # מגרשי ייעודי קרקע - מפורט
LAYER_PARCELS = 524         # חלקות
LAYER_BLOCKS = 525          # גושים
LAYER_PERMITS = 772         # בקשות והיתרי בניה
LAYER_PRESERVATION = 682    # מבנים ואתרים לשימור
LAYER_TABA = 528            # תוכניות בניין עיר
LAYER_ADDRESSES = 527       # כתובות (official address points)
LAYER_STREET_LINES = 507    # צירי רחוב (street centerlines)

# --- Area of interest ------------------------------------------------------
NEIGHBORHOOD_NAME = "הצפון הישן - החלק הצפוני"
NEIGHBORHOOD_FIELD = "shem_shchuna"

# --- CRS -------------------------------------------------------------------
CRS_ITM = 2039      # Israeli Transverse Mercator - all geometry work here
CRS_WGS84 = 4326    # only at GeoJSON export

# --- Physical / plan constants --------------------------------------------
FLOOR_HEIGHT_M = 3.0

# Height cross-check model, fitted on 1,874 AOI buildings with a known
# ms_komot (see data/out/qa_report.md). `gova_simplex_2019` is exactly
# max_height - min_height, and it is NOT floors x 3.0: the DSM roof includes
# parapets, stairwell housing and water tanks, and min_height is the lowest
# ground point on sloping terrain. That fixed overhead makes naive
# height/3.0 overestimate floors badly (11% within 1 floor vs 59% for the
# fitted inverse). Used ONLY as a corroborating check on ms_komot.
HEIGHT_MODEL_INTERCEPT_M = 9.031
HEIGHT_MODEL_SLOPE_M = 2.164
HEIGHT_MODEL_RESID_FLOORS = 1.66

# `dsm_max` sits in a DIFFERENT vertical datum from `max_height`: reusing the
# model above for the DSM channel biases it by a median of ~4 floors, which
# would make the two cross-checks look like they disagree when they do not.
# The DSM channel therefore gets its own fitted inversion.
DSM_MODEL_INTERCEPT_M = 0.952
DSM_MODEL_SLOPE_M = 2.181
DSM_MODEL_RESID_FLOORS = 2.17

# Agreement band for the confidence grade. The cross-checks are DSM-derived
# and carry ~1.7-2.2 floors of noise, so a +/-1 floor band would label genuine
# agreement as disagreement. +/-2 floors is ~1 sigma: "agrees to within the
# precision of the instrument" is the honest claim, and it is the claim made.
AGREEMENT_TOLERANCE_FLOORS = 2.0
PARTIAL_ROOF_FACTOR = 0.65

# Streets that get the enhanced rule branch under תא/3616א
SPECIAL_STREETS = ("דיזנגוף", "בן יהודה")

# תא/3616א "תכנית רובע 3 (4)" -- confirmed in force (בתוקף) from the live
# TABA layer 528, tr_matan_tokef = 2018-01-09.
ROVA3_PLAN_CODE = "3616א"
ROVA3_EFFECTIVE_DATE = "2018-01-09"
# Permits at/after this date are treated as potentially consuming Rova 3 rights.
RIGHTS_CONSUMED_SINCE = "2018-01-01"

# --- Valuation defaults ----------------------------------------------------
# Median ₪/m² for Old North (northern part) residential. Overridden at runtime
# by the nadlan.gov.il fetch when that succeeds; this is the cited fallback.
# --- Price benchmark (T4.1) -------------------------------------------------
# The nadlan.gov.il REST endpoints (GetAssestAndDeals / GetDataByQuery) now
# answer 302 to unauthenticated callers, so the plan's documented fallback
# applies: a researched median carried with its citation.
#
# Sources (retrieved 2026-08):
#   harova.co.il 2025 Tel Aviv price guide -- Old North ~65,000 NIS/m2
#   concord-tlv.co.il analysis of CBS data -- Old North avg ~3.6M NIS/apartment
#   Reported ~2% YoY growth in NIS/m2, H1-2025 -> H1-2026.
PRICE_PER_M2 = 65000
PRICE_PER_M2_LOW = 58000
PRICE_PER_M2_HIGH = 72000
PRICE_SOURCE_NOTE = (
    "Researched median for הצפון הישן, ~65,000 NIS/m2 (harova.co.il 2025 "
    "price guide; concord-tlv.co.il CBS analysis). nadlan.gov.il REST API "
    "returned HTTP 302 to unauthenticated callers at build time."
)
PRICE_IS_LIVE = False

BUILD_COST_RATIO = 0.5

# The 1-floor entitlement (R-EX-1FL-EXTRAP) is extrapolated from the 2-floor
# clause, not cited from the plan, and it is where the largest per-building
# gaps land. Keeping it OUT of the headline is the conservative choice: it is
# reported separately as identified upside rather than booked as fact.
INCLUDE_EXTRAPOLATED_IN_HEADLINE = False
LEVY_SHARE = 0.5  # betterment levy scenario for net_low

# --- HTTP politeness -------------------------------------------------------
MAX_REQUESTS_PER_SEC = 2
REQUEST_TIMEOUT = 90
CHUNK_SIZE = 1000

# --- Paths -----------------------------------------------------------------
POC_DIR = Path(__file__).resolve().parent
DATA_DIR = POC_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
OUT_DIR = DATA_DIR / "out"

for _d in (RAW_DIR, PROCESSED_DIR, OUT_DIR):
    _d.mkdir(parents=True, exist_ok=True)

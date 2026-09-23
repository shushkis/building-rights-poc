"""Rights table for תא/3616א (Rova 3), area OUTSIDE the UNESCO zone.

Our AOI (הצפון הישן - החלק הצפוני, north of Arlozorov) sits outside the
UNESCO White City conservation zone, so the non-UNESCO branch applies.

Sources:
  - Barnea client update on the Rova 3 plan
    https://barlaw.co.il/practice_areas/urban-renewal/client_updates/
    main-aspects-of-plan-for-tel-aviv-3rd-quarter-will-enable-construction-
    of-8000-new-apartments-through-tama-38/
  - sylaw summary of רובע 3
    https://www.sylaw.co.il/רובע-3-תל-אביב.html
  - Court ruling quantifying the 4-floor / <500 m² case
    https://storage.nadlancenter.co.il/media/Storage/41328.pdf

Floor counts INCLUDE the ground or pillar floor
("כולל קומת קרקע או קומת עמודים").

Every result carries a `rule_id` so each output row is traceable to a clause.
"""
from __future__ import annotations

from dataclasses import dataclass

# --- Rule identifiers -------------------------------------------------------
R_NEW_SPECIAL = "R-NEW-SPECIAL"      # new build, Dizengoff / Ben Yehuda
R_NEW_OTHER = "R-NEW-OTHER"          # new build, other streets
R_EX_2FL = "R-EX-2FL"                # existing 2 floors -> complete to 5
R_EX_SPECIAL_3P = "R-EX-SPECIAL-3P"  # existing 3+ on Dizengoff / Ben Yehuda -> 7
R_EX_OTHER_3_6 = "R-EX-OTHER-3-6"    # existing 3-6, other streets -> +1
R_EX_7P = "R-EX-7P"                  # existing 7+ -> +2
R_EX_1FL_EXTRAP = "R-EX-1FL-EXTRAP"  # existing 1 floor -> EXTRAPOLATED, not cited
R_UNESCO = "R-UNESCO-OUT-OF-SCOPE"   # inside UNESCO zone: different regime

# Rule ids whose entitlement is extrapolated rather than directly cited.
EXTRAPOLATED_RULES = frozenset({R_EX_1FL_EXTRAP})

RULE_DESCRIPTIONS = {
    R_NEW_SPECIAL: "בנייה חדשה על דיזנגוף/בן יהודה: 7 קומות + קומת גג חלקית",
    R_NEW_OTHER: "בנייה חדשה ברחוב רגיל: 6 קומות + קומת גג חלקית",
    R_EX_2FL: "מבנה קיים בן 2 קומות: השלמה ל-5 קומות + קומת גג חלקית",
    R_EX_SPECIAL_3P: "מבנה קיים 3+ קומות על דיזנגוף/בן יהודה: השלמה ל-7 + גג חלקי",
    R_EX_OTHER_3_6: "מבנה קיים 3-6 קומות ברחוב רגיל: תוספת קומה אחת + גג חלקי",
    R_EX_7P: "מבנה קיים 7+ קומות: תוספת 2 קומות + גג חלקי",
    R_EX_1FL_EXTRAP: "מבנה קיים בן קומה אחת: הרחבה בהיקש מסעיף 2 הקומות (לא מצוטט במפורש)",
    R_UNESCO: "בתחום מתחם אונסקו — חלה מדיניות שימור נפרדת",
}

NEW_BUILD_SPECIAL_FLOORS = 7
NEW_BUILD_OTHER_FLOORS = 6
COMPLETE_2FL_TO = 5
COMPLETE_SPECIAL_TO = 7


@dataclass(frozen=True)
class AllowedResult:
    total_floors: int
    partial_roof: bool
    rule_id: str

    @property
    def description(self) -> str:
        return RULE_DESCRIPTIONS.get(self.rule_id, "")


def allowed_floors(
    street_class: str,
    current_floors: int | float | None,
    lot_area_m2: float | None = None,
    in_unesco_zone: bool = False,
    permit_pre_1980: bool = False,
) -> AllowedResult:
    """Total permitted floors under תא/3616א.

    Args:
        street_class: 'special' (Dizengoff / Ben Yehuda) or 'other'.
        current_floors: as-built floor count incl. ground/pillar floor.
            None or 0 is treated as a new build (vacant lot).
        lot_area_m2: lot area; carried for traceability and future
            area-conditioned clauses. Does not change the floor entitlement
            in the published table.
        in_unesco_zone: if True the non-UNESCO table does not apply.
        permit_pre_1980: carried through for downstream reporting.

    Returns:
        AllowedResult(total_floors, partial_roof, rule_id)

    The returned total is never below `current_floors`: the plan grants
    rights, it does not remove existing ones.
    """
    special = street_class == "special"

    if in_unesco_zone:
        base = int(current_floors) if current_floors else 0
        return AllowedResult(base, False, R_UNESCO)

    cf = 0 if current_floors is None else int(current_floors)

    # --- new build / vacant lot ---
    if cf <= 0:
        if special:
            return AllowedResult(NEW_BUILD_SPECIAL_FLOORS, True, R_NEW_SPECIAL)
        return AllowedResult(NEW_BUILD_OTHER_FLOORS, True, R_NEW_OTHER)

    # --- existing buildings, most specific clause first ---
    if cf >= 7:
        return AllowedResult(cf + 2, True, R_EX_7P)

    if special and cf >= 3:
        total = max(COMPLETE_SPECIAL_TO, cf)
        return AllowedResult(total, True, R_EX_SPECIAL_3P)

    if cf == 2:
        target = COMPLETE_SPECIAL_TO if special else COMPLETE_2FL_TO
        rule = R_EX_SPECIAL_3P if special else R_EX_2FL
        return AllowedResult(max(target, cf), True, rule)

    if cf == 1:
        # The published table addresses 2-floor buildings explicitly and is
        # SILENT on single-floor structures. Applying the 2-floor completion
        # clause here is an EXTRAPOLATION, not a citation, so it gets its own
        # rule_id and is reported separately in the validation memo. Many
        # single-floor footprints are annexes rather than standalone dwellings.
        target = COMPLETE_SPECIAL_TO if special else COMPLETE_2FL_TO
        return AllowedResult(max(target, cf), True, R_EX_1FL_EXTRAP)

    # cf in 3..6, other streets
    return AllowedResult(cf + 1, True, R_EX_OTHER_3_6)

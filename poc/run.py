"""End-to-end pipeline: `python -m poc.run` runs Phases 1-4 (+5/6 artifacts).

From an empty data/ this performs the full ingest, rule, gap, value and
export chain. Cached raw responses in data/raw/ are reused, so a second run
is fast and makes no network calls.
"""
from __future__ import annotations

import argparse
import time


def main() -> None:
    ap = argparse.ArgumentParser(description="Unused building rights pipeline")
    ap.add_argument("--force", action="store_true",
                    help="recompute all derived artifacts (raw cache still reused)")
    args = ap.parse_args()

    t0 = time.time()

    def step(n, label):
        print(f"\n[{n}] {label}")

    step(1, "Ingest AOI + layers")
    from poc.ingest.aoi import fetch_aoi
    from poc.ingest.fetch import fetch_all
    aoi = fetch_aoi()
    print(f"    AOI area: {aoi.geometry.area.iloc[0] / 1e6:.3f} km²")
    fetch_all()

    step(2, "Spatial joins -> master")
    from poc.ingest.joins import build_master
    m = build_master(force=args.force)
    print(f"    master rows: {len(m):,}")

    step(3, "QA report")
    from poc.ingest.qa import build_report
    build_report()

    step(4, "Rules + gap computation")
    from poc.gap.compute import compute_gaps
    g = compute_gaps(force=True)
    print(f"    buildings with gap: {int((g['gap_m2'] > 0).sum()):,}")

    step(5, "Sanity dashboard")
    from poc.gap.sanity import build_sanity
    build_sanity(g)

    step(6, "Valuation")
    from poc.value.model import build as build_valued
    from poc.value.model import totals
    v = build_valued(force=True)
    t = totals(v)
    print(f"    headline: {t['gap_m2_headline']:,.0f} m² · "
          f"₪{t['net_low']/1e9:.2f}B–₪{t['net_high']/1e9:.2f}B")

    step(7, "Validation sample + memo")
    from poc.validate.memo import build_memo
    from poc.validate.sample import build_sample
    s = build_sample()
    build_memo()
    print(f"    worksheet rows: {len(s)}")

    step(8, "Demo export")
    from poc.demo.export import export
    export(force=False)

    print(f"\nDone in {time.time() - t0:.1f}s.")
    print("Serve the demo:  cd poc/demo && python -m http.server 8000")


if __name__ == "__main__":
    main()

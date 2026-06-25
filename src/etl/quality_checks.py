"""
Plausibility & data-quality checks over the built database. Run from src/:
    python -m etl.quality_checks
PASS = good, WARN = known limitation, FAIL = likely import bug. Exits non-zero on FAIL.
"""
import sys
from etl.db import get_connection
from etl.config import STATE_NAMES

LON_MIN, LON_MAX = 5.5, 15.5
LAT_MIN, LAT_MAX = 47.0, 55.3
results = []


def check(label, status, detail=""):
    results.append(status)
    print(f"  [{status:^4}] {label}" + (f"  ({detail})" if detail else ""))


def main():
    conn = get_connection()
    q = lambda sql, p=(): conn.execute(sql, p).fetchone()[0]
    total = q("SELECT COUNT(*) FROM accidents")
    print(f"\nData-quality report — {total:,} accidents\n" + "-" * 54)

    check("accidents table populated", "PASS" if total else "FAIL", f"{total:,} rows")
    ymin, ymax = conn.execute("SELECT MIN(year), MAX(year) FROM accidents").fetchone()
    check("years within 2016-2026", "PASS" if ymin and 2016 <= ymin <= ymax <= 2026 else "WARN",
          f"{ymin}-{ymax}")
    bad = q("SELECT COUNT(*) FROM accidents WHERE lon IS NOT NULL AND "
            "(lon NOT BETWEEN ? AND ? OR lat NOT BETWEEN ? AND ?)", (LON_MIN, LON_MAX, LAT_MIN, LAT_MAX))
    check("coordinates inside Germany", "PASS" if bad == 0 else "FAIL", f"{bad} out of range")
    check("coordinates present", "PASS" if q("SELECT COUNT(*) FROM accidents WHERE lon IS NULL")==0 else "WARN",
          f"{q('SELECT COUNT(*) FROM accidents WHERE lon IS NULL')} missing")
    check("category in {1,2,3}", "PASS" if q("SELECT COUNT(*) FROM accidents WHERE category NOT IN (1,2,3)")==0 else "FAIL")
    check("month in 1-12", "PASS" if q("SELECT COUNT(*) FROM accidents WHERE month NOT BETWEEN 1 AND 12")==0 else "FAIL")
    check("hour in 0-23", "PASS" if q("SELECT COUNT(*) FROM accidents WHERE hour NOT BETWEEN 0 AND 23")==0 else "FAIL")
    flags = ["is_bicycle","is_car","is_pedestrian","is_motorcycle","is_goods","is_other"]
    bad_flags = sum(q(f"SELECT COUNT(*) FROM accidents WHERE {c} NOT IN (0,1)") for c in flags)
    check("participant flags are 0/1", "PASS" if bad_flags == 0 else "FAIL", f"{bad_flags} bad")
    check("municipality_ags is 8 digits",
          "PASS" if q("SELECT COUNT(*) FROM accidents WHERE length(municipality_ags)<>8")==0 else "FAIL")
    bad_state = q("SELECT COUNT(*) FROM accidents WHERE substr(municipality_ags,1,2) NOT IN (%s)"
                  % ",".join(f"'{k}'" for k in STATE_NAMES))
    check("state prefix is 01-16", "PASS" if bad_state == 0 else "FAIL", f"{bad_state} bad")
    check("every accident linked to a region",
          "PASS" if q("SELECT COUNT(*) FROM accidents WHERE region_id IS NULL")==0 else "FAIL")
    check("districts have a parent state",
          "PASS" if q("SELECT COUNT(*) FROM regions WHERE level='district' AND parent_region_id IS NULL")==0 else "FAIL")
    dupes = q("SELECT COUNT(*) FROM (SELECT source_uid FROM accidents WHERE source_uid IS NOT NULL "
              "GROUP BY source_uid HAVING COUNT(*)>1)")
    check("no duplicate source ids", "PASS" if dupes == 0 else "WARN", f"{dupes} duplicated")
    check("road_condition populated", "PASS" if q("SELECT COUNT(*) FROM accidents WHERE road_condition IS NOT NULL")>0 else "WARN",
          f"{q('SELECT COUNT(*) FROM accidents WHERE road_condition IS NOT NULL'):,} rows")
    dist = q("SELECT COUNT(*) FROM regions WHERE level='district'")
    geo = q("SELECT COUNT(*) FROM regions WHERE level='district' AND geometry IS NOT NULL")
    check("districts have geometry", "PASS" if geo else "WARN", f"{geo}/{dist} covered")

    fails = results.count("FAIL"); warns = results.count("WARN")
    print("-" * 54)
    print(f"  {fails} FAIL · {warns} WARN · {results.count('PASS')} PASS")
    conn.close()
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
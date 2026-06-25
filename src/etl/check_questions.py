"""
Answer the mandatory and bonus examiner questions directly from the database.
Run from src/:  python -m etl.check_questions
"""
from etl.db import get_connection
from etl.config import STATE_NAMES


def main():
    conn = get_connection()
    q = lambda sql, p=(): conn.execute(sql, p).fetchone()[0]

    print("=" * 60)
    print("MANDATORY QUESTIONS (5 required)")
    print("=" * 60)

    print("\n1. Earliest accident year overall:",
          q("SELECT MIN(year) FROM accidents"))

    print("\n2. Accidents in Saxony 2023:",
          q("SELECT COUNT(*) FROM accidents WHERE municipality_ags LIKE '14%' AND year=2023"))

    print("\n3. First data year for NRW:",
          q("SELECT MIN(year) FROM accidents WHERE municipality_ags LIKE '05%'"))

    print("\n4. First data year for Mecklenburg-Vorpommern:",
          q("SELECT MIN(year) FROM accidents WHERE municipality_ags LIKE '13%'"))

    print("\n5. Pedestrian accidents in Berlin 2023:",
          q("SELECT COUNT(*) FROM accidents WHERE municipality_ags LIKE '11%' AND year=2023 AND is_pedestrian=1"))

    print("\nFirst available year per state (shows staggered rollout):")
    for ags, name in sorted(STATE_NAMES.items()):
        fy = q("SELECT MIN(year) FROM accidents WHERE municipality_ags LIKE ?", (ags + "%",))
        print(f"   {ags} {name:<28} {fy}")

    print("\n" + "=" * 60)
    print("MULTI-SOURCE QUESTIONS (min 2 required)")
    print("=" * 60)

    print("\n6. Accidents per 100,000 registered cars — top 5 districts (2024):")
    rows = conn.execute("""
        SELECT r.name, COUNT(*) AS acc,
               iv.value AS cars,
               ROUND(COUNT(*) * 100000.0 / iv.value, 2) AS rate
        FROM accidents a
        JOIN regions r ON r.region_id = a.region_id
        JOIN indicator_values iv ON iv.region_id = r.region_id
        JOIN indicators i ON i.indicator_id = iv.indicator_id
        WHERE i.code='CARS' AND iv.year=2024
          AND a.year=2024 AND length(r.ags)=5
        GROUP BY r.region_id
        ORDER BY rate DESC LIMIT 5
    """).fetchall()
    if rows:
        for r in rows:
            print(f"   {r['name']}: {r['acc']:,} accidents / {int(r['cars']):,} cars = {r['rate']} per 100k")
    else:
        print("   (No car data loaded — re-export GENESIS 46251 for all Kreise)")

    print("\n7. Accidents per 10,000 inhabitants — top 5 districts 2023")
    print("   (cross-source: Unfallatlas accidents joined to Regionalstatistik):")
    rows = conn.execute("""
        SELECT r.name, COUNT(*) AS acc, iv.value AS official_rate
        FROM accidents a
        JOIN regions r ON r.region_id = a.region_id
        JOIN indicator_values iv ON iv.region_id = r.region_id
        JOIN indicators i ON i.indicator_id = iv.indicator_id
        WHERE i.code='ACC_PER_10K' AND iv.year=2023
          AND a.year=2023 AND length(r.ags)=5
        GROUP BY r.region_id
        ORDER BY official_rate DESC LIMIT 5
    """).fetchall()
    if rows:
        for r in rows:
            print(f"   {r['name']}: {r['acc']:,} accidents | official rate: {r['official_rate']} per 10k")
    else:
        print("   (No per-10k indicator data loaded)")

    print("\n" + "=" * 60)
    print("BONUS QUESTIONS")
    print("=" * 60)

    print("\n8. Top 5 districts by fatal accidents in 2024:")
    rows = conn.execute("""
        SELECT substr(a.municipality_ags,1,5) AS ags, r.name, COUNT(*) AS fatal
        FROM accidents a
        LEFT JOIN regions r ON r.ags = substr(a.municipality_ags,1,5)
        WHERE a.year=2024 AND a.category=1
        GROUP BY ags ORDER BY fatal DESC LIMIT 5
    """).fetchall()
    for r in rows:
        print(f"   {r['name'] or r['ags']}: {r['fatal']} fatal accidents")

    print("\n9. Bicycle accidents in Dresden in 2024:")
    n = q("""SELECT COUNT(*) FROM accidents
             WHERE municipality_ags LIKE '14612%' AND year=2024 AND is_bicycle=1""")
    print(f"   {n:,} bicycle accidents in Dresden (AGS 14612) in 2024")

    print("\n10. Cyclist vs pedestrian accidents — Berlin 2023:")
    ped = q("SELECT COUNT(*) FROM accidents WHERE municipality_ags LIKE '11%' AND year=2023 AND is_pedestrian=1")
    bike = q("SELECT COUNT(*) FROM accidents WHERE municipality_ags LIKE '11%' AND year=2023 AND is_bicycle=1")
    print(f"   Pedestrians: {ped:,}  |  Cyclists: {bike:,}")

    print("\n11. Worst severity-weighted hotspot in Germany 2023:")
    rows = conn.execute("""
        SELECT ROUND(lon,3) AS rlon, ROUND(lat,3) AS rlat,
               COUNT(*) AS total,
               SUM(category=1) AS fatal,
               SUM(category=2) AS serious,
               SUM(category=3) AS light,
               SUM(category=1)*10 + SUM(category=2)*3 + SUM(category=3) AS score,
               substr(MIN(municipality_ags),1,5) AS dist_ags
        FROM accidents WHERE year=2023 AND lon IS NOT NULL
        GROUP BY rlon, rlat HAVING COUNT(*) >= 3
        ORDER BY score DESC LIMIT 3
    """).fetchall()
    for r in rows:
        name = conn.execute("SELECT name FROM regions WHERE ags=?",
                            (r['dist_ags'],)).fetchone()
        print(f"   ({r['rlat']},{r['rlon']}) {name[0] if name else r['dist_ags']}: "
              f"{r['total']} crashes, {r['fatal']} fatal, {r['serious']} serious "
              f"— severity score {r['score']}")

    print("\n12. Year-over-year trend — Saxony (all loaded years):")
    rows = conn.execute("""
        SELECT year, COUNT(*) AS acc,
               SUM(category=1) AS fatal,
               SUM(category=2) AS serious
        FROM accidents WHERE municipality_ags LIKE '14%'
        GROUP BY year ORDER BY year
    """).fetchall()
    for r in rows:
        print(f"   {r['year']}: {r['acc']:>7,} total  ({r['fatal']} fatal, {r['serious']} serious)")

    print("\n13. Municipalities in Saxony with zero accidents in 2023:")
    zero = q("""
        SELECT COUNT(*) FROM regions r
        WHERE r.level='municipality' AND r.ags LIKE '14%'
          AND NOT EXISTS (
              SELECT 1 FROM accidents a
              WHERE a.region_id=r.region_id AND a.year=2023)
    """)
    total_mun = q("SELECT COUNT(*) FROM regions WHERE level='municipality' AND ags LIKE '14%'")
    print(f"   {zero} of {total_mun} Saxon municipalities have zero recorded accidents in 2023")
    print("   (Caveat: municipalities only exist if they appear in the data —")
    print("    true zero-case count needs the full Gemeindeverzeichnis)")

    print("\n14. National accident count by severity in 2023:")
    for cat, label in [(1,'Fatal'),(2,'Serious'),(3,'Light')]:
        cnt = q("SELECT COUNT(*) FROM accidents WHERE year=2023 AND category=?", (cat,))
        print(f"   {label}: {cnt:,}")

    conn.close()


if __name__ == "__main__":
    main()
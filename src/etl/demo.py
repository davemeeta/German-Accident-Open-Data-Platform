"""
Live defense demonstration script.
Run from src/ with the API running:
    python3 -m etl.demo
"""
import time
import sys
from etl.db import get_connection
from etl.config import STATE_NAMES

BOLD  = "\033[1m"
CYAN  = "\033[96m"
GREEN = "\033[92m"
RED   = "\033[91m"
AMBER = "\033[93m"
BLUE  = "\033[94m"
DIM   = "\033[2m"
RESET = "\033[0m"

def pause(s=0.8):
    time.sleep(s)

def header(text):
    width = 62
    print()
    print(f"{CYAN}{'─' * width}{RESET}")
    print(f"{BOLD}{CYAN}  {text}{RESET}")
    print(f"{CYAN}{'─' * width}{RESET}")
    pause(0.5)

def question(num, text):
    print(f"\n{DIM}  Q{num}.{RESET} {text}")
    pause(0.6)

def answer(text, color=GREEN):
    print(f"  {color}{BOLD}→  {text}{RESET}")
    pause(0.9)

def subline(text):
    print(f"     {DIM}{text}{RESET}")

def main():
    conn = get_connection()
    q = lambda sql, p=(): conn.execute(sql, p).fetchone()[0]

    # ── Opening ──────────────────────────────────────────────────────────────
    print()
    print(f"{BOLD}{CYAN}  Unfallatlas Risk Lens — Live Demonstration{RESET}")
    print(f"  {DIM}German road-accident open data, harmonised 2016–2024{RESET}")
    pause(1.0)

    total = q("SELECT COUNT(*) FROM accidents")
    years = q("SELECT GROUP_CONCAT(DISTINCT year) FROM accidents")
    regions = q("SELECT COUNT(*) FROM regions")
    print(f"\n  {DIM}Database loaded:{RESET} "
          f"{BOLD}{total:,}{RESET} accidents · "
          f"years {BOLD}{years}{RESET} · "
          f"{BOLD}{regions:,}{RESET} regions")
    pause(1.2)

    # ── Mandatory questions ───────────────────────────────────────────────────
    header("THE MANDATORY QUESTIONS")

    question(1, "What is the earliest accident year in the complete dataset?")
    answer(f"{q('SELECT MIN(year) FROM accidents')}")

    question(2, "How many accidents with personal injury occurred in Saxony in 2023?")
    n = q("SELECT COUNT(*) FROM accidents WHERE municipality_ags LIKE '14%' AND year=2023")
    answer(f"{n:,} accidents")
    subline("endpoint: /aggregates/accidents?state=SN&year=2023")

    question(3, "From which year is data available for North Rhine-Westphalia?")
    nrw = q("SELECT MIN(year) FROM accidents WHERE municipality_ags LIKE '05%'")
    answer(f"{nrw}")
    subline("NRW joined the Unfallatlas in 2019 — only knowable from the full 9-year history")

    question(4, "From which year is data available for Mecklenburg-Western Pomerania?")
    mv = q("SELECT MIN(year) FROM accidents WHERE municipality_ags LIKE '13%'")
    answer(f"{mv}")
    subline("MV joined in 2020 — one year after NRW")

    question(5, "How many pedestrian accidents occurred in Berlin in 2023?")
    n = q("SELECT COUNT(*) FROM accidents WHERE municipality_ags LIKE '11%' AND year=2023 AND is_pedestrian=1")
    answer(f"{n:,} pedestrian accidents")
    subline("endpoint: /aggregates/accidents?state=BE&year=2023&pedestrian=true")

    # ── Multi-source ──────────────────────────────────────────────────────────
    header("MULTI-SOURCE QUESTIONS  (These cannot be answered from one dataset alone)")

    question(6, "Accidents per 100,000 registered passenger cars — top districts 2024?")
    subline("source 1: Unfallatlas (accidents)  ⋈  source 2: GENESIS 46251 (cars)  on AGS key")
    rows = conn.execute("""
        SELECT r.name, r.ags,COUNT(*) AS acc,iv.value AS cars,
        ROUND(COUNT(*) * 100000.0 / iv.value, 2) AS rate
        FROM accidents a
        JOIN regions r ON r.ags = substr(a.municipality_ags, 1, 5)
        JOIN indicator_values iv ON iv.region_id = r.region_id
        JOIN indicators i ON i.indicator_id = iv.indicator_id
        WHERE i.code = 'CARS'
        AND iv.year = 2024
        AND a.year = 2024
        AND length(r.ags) = 5
        GROUP BY r.region_id
        ORDER BY rate DESC
        LIMIT 5
    """).fetchall()
    if rows:
        pause(0.3)
        for r in rows:
            print(f"  {GREEN}{BOLD}  {r['name']:<30}{RESET}  "
                  f"{r['acc']:>6,} acc / {int(r['cars']):>7,} cars  "
                  f"{AMBER}{BOLD}= {r['rate']:>8} per 100k{RESET}")
            pause(0.3)
        subline("endpoint: /aggregates/rate?indicator=CARS&level=district&year=2024")
    else:
        answer("No car data found — check indicator_values table", AMBER)

    question(7, "Which districts have the highest accident rate per 10,000 inhabitants? (2023)")
    subline("source 1: Unfallatlas  ⋈  source 2: Regionalstatistik ACC_PER_10K  on AGS key")
    rows = conn.execute("""
        SELECT r.name,r.ags, iv.value AS official_rate,(SELECT COUNT(*) FROM accidents a
        WHERE a.municipality_ags LIKE r.ags || '%' AND a.year=2023) AS acc
        FROM indicator_values iv
        JOIN indicators i ON i.indicator_id = iv.indicator_id
        JOIN regions r ON r.region_id = iv.region_id
        WHERE i.code='ACC_PER_10K' AND iv.year=2023
        AND length(r.ags)=5
        ORDER BY official_rate DESC LIMIT 5
    """).fetchall()
    if rows:
        pause(0.3)
        for r in rows:
            print(f"  {GREEN}{BOLD}  {r['name']:<30}{RESET}  "
                  f"{r['acc']:>6,} accidents  "
                  f"{AMBER}{BOLD}= {r['official_rate']} per 10k{RESET}")
            pause(0.3)
    else:
        answer("No per-10k data loaded", AMBER)

    # ── Bonus questions ───────────────────────────────────────────────────────
    header("BONUS QUESTIONS  (self-formulated for testing the API)")

    question(8, "Which 5 districts recorded the most fatal accidents in 2024?")
    rows = conn.execute("""
        SELECT substr(a.municipality_ags,1,5) AS ags, r.name, COUNT(*) AS fatal
        FROM accidents a
        LEFT JOIN regions r ON r.ags=substr(a.municipality_ags,1,5)
        WHERE a.year=2024 AND a.category=1
        GROUP BY ags ORDER BY fatal DESC LIMIT 5
    """).fetchall()
    pause(0.3)
    for r in rows:
        print(f"  {RED}{BOLD}  {r['name'] or r['ags']:<30}{RESET}  {r['fatal']} fatal accidents")
        pause(0.3)

    question(9, "How many bicycle accidents occurred in Dresden in 2024?")
    n = q("SELECT COUNT(*) FROM accidents WHERE municipality_ags LIKE '14612%' AND year=2024 AND is_bicycle=1")
    answer(f"{n:,} bicycle accidents in Dresden (AGS 14612) in 2024")

    question(10, "Pedestrians vs cyclists in Berlin 2023 — who is more at risk?")
    ped  = q("SELECT COUNT(*) FROM accidents WHERE municipality_ags LIKE '11%' AND year=2023 AND is_pedestrian=1")
    bike = q("SELECT COUNT(*) FROM accidents WHERE municipality_ags LIKE '11%' AND year=2023 AND is_bicycle=1")
    print(f"  {AMBER}{BOLD}  Pedestrians: {ped:,}{RESET}   {BLUE}{BOLD}Cyclists: {bike:,}{RESET}")
    pause(0.9)

    question(11, "What is the worst crash hotspot in Germany in 2023? (severity-weighted)")
    row = conn.execute("""
        SELECT ROUND(lon,3) AS rlon, ROUND(lat,3) AS rlat,
        COUNT(*) AS total,
        SUM(category=1) AS fatal, SUM(category=2) AS serious,
        SUM(category=1)*10+SUM(category=2)*3+SUM(category=3) AS score, substr(MIN(municipality_ags),1,2) AS state_ags
        FROM accidents WHERE year=2023 AND lon IS NOT NULL
        GROUP BY rlon, rlat HAVING COUNT(*) >= 3
        ORDER BY score DESC LIMIT 1
    """).fetchone()
    if row:
        name = conn.execute(
            "SELECT name FROM regions WHERE ags=?",
            (row['state_ags'],)).fetchone()
        answer(f"{name[0] if name else 'Germany'} — {row['total']} crashes "
               f"({row['fatal']} fatal, {row['serious']} serious) "
               f"· severity score {row['score']}")
        subline(f"coordinates: ({row['rlat']}, {row['rlon']})")

    question(12, "Year-over-year trend — is Germany getting safer? (Saxony as example)")
    rows = conn.execute("""
        SELECT year, COUNT(*) AS acc, SUM(category=1) AS fatal
        FROM accidents WHERE municipality_ags LIKE '14%'
        GROUP BY year ORDER BY year
    """).fetchall()
    pause(0.3)
    for r in rows:
        bar = "█" * (r['acc'] // 1000)
        print(f"  {DIM}  {r['year']}{RESET}  {CYAN}{bar:<15}{RESET}  "
              f"{r['acc']:>7,}  {DIM}({r['fatal']} fatal){RESET}")
        pause(0.2)

    question(13, "Municipalities in Saxony with zero accidents in 2023?")
    zero = q("""
        SELECT COUNT(*) FROM regions r WHERE r.level='municipality' AND r.ags LIKE '14%'
        AND NOT EXISTS (SELECT 1 FROM accidents a WHERE a.region_id=r.region_id AND a.year=2023)
    """)
    total_mun = q("SELECT COUNT(*) FROM regions WHERE level='municipality' AND ags LIKE '14%'")
    answer(f"{zero} of {total_mun} Saxon municipalities (known limitation: needs full Gemeindeverzeichnis)")

    question(14, "Accidents per 100,000 registered cars — top districts 2023?")
    subline("cross-source: Unfallatlas 2023 accidents ⋈ GENESIS 46251 cars (ref. 01.01.2024)")
    rows = conn.execute("""
        SELECT r.name, r.ags,COUNT(*) AS acc,iv.value AS cars,ROUND(COUNT(*) * 100000.0 / iv.value, 2) AS rate
        FROM accidents a
        JOIN regions r ON r.ags = substr(a.municipality_ags, 1, 5)
        JOIN indicator_values iv ON iv.region_id = r.region_id
        JOIN indicators i ON i.indicator_id = iv.indicator_id
        WHERE i.code = 'CARS'
        AND iv.year = 2023
        AND a.year = 2023
        AND length(r.ags) = 5
        GROUP BY r.region_id
        ORDER BY rate DESC
        LIMIT 5
    """).fetchall()
    if rows:
        pause(0.3)
        for r in rows:
            print(f"  {GREEN}{BOLD}  {r['name']:<30}{RESET}  "
                  f"{r['acc']:>6,} acc / {int(r['cars']):>7,} cars  "
                  f"{AMBER}{BOLD}= {r['rate']:>8} per 100k{RESET}")
            pause(0.3)
        subline("endpoint: /aggregates/rate?indicator=CARS&level=district&year=2023")
    else:
        answer("No car data found for 2023", AMBER)
    
    question(15,"Multi-source risk summary — which districts are dangerous AND busy? (2023)")
    subline("3 sources: Unfallatlas accidents ⋈ GENESIS cars ⋈ Regionalstatistik per-10k")
    subline("Composite score = normalised accident count + normalised per-100k-cars rate")
    rows = conn.execute("""
        WITH acc_counts AS (
            SELECT substr(a.municipality_ags,1,5) AS ags,
                   COUNT(*) AS total,
                   SUM(a.category=1) AS fatal
            FROM accidents a
            WHERE a.year = 2023
            GROUP BY ags
        ),
        car_rates AS (
            SELECT r.ags,
                   r.name,
                   ac.total,
                   ac.fatal,
                   ROUND(ac.total * 100000.0 / iv_cars.value, 2) AS rate_per_100k_cars,
                   iv_10k.value AS official_rate_per_10k
            FROM acc_counts ac
            JOIN regions r ON r.ags = ac.ags
            JOIN indicator_values iv_cars ON iv_cars.region_id = r.region_id
            JOIN indicators i_cars ON i_cars.indicator_id = iv_cars.indicator_id
                 AND i_cars.code = 'CARS' AND iv_cars.year = 2023
            JOIN indicator_values iv_10k ON iv_10k.region_id = r.region_id
            JOIN indicators i_10k ON i_10k.indicator_id = iv_10k.indicator_id
                 AND i_10k.code = 'ACC_PER_10K' AND iv_10k.year = 2023
            WHERE length(r.ags) = 5
        )
        SELECT name, total, fatal,
               rate_per_100k_cars,
               official_rate_per_10k,
               ROUND(rate_per_100k_cars + (official_rate_per_10k * 10), 2) AS composite_score
        FROM car_rates
        ORDER BY composite_score DESC
        LIMIT 5
    """).fetchall()
    if rows:
        pause(0.3)
        print(f"  {'District':<32} {'Total':>6}  {'Fatal':>5}  {'per 100k cars':>14}  {'per 10k inh':>12}  {'Risk Score':>10}")
        print(f"  {'─'*90}")
        for r in rows:
            print(f"  {GREEN}{BOLD}{r['name']:<32}{RESET}"
                  f"  {r['total']:>6,}"
                  f"  {RED}{r['fatal']:>5}{RESET}"
                  f"  {AMBER}{r['rate_per_100k_cars']:>14.1f}{RESET}"
                  f"  {BLUE}{r['official_rate_per_10k']:>12.1f}{RESET}"
                  f"  {BOLD}{r['composite_score']:>10.1f}{RESET}")
            pause(0.3)
        subline("composite score = rate_per_100k_cars + (official_rate_per_10k × 10)")
        subline("higher score = district is risky relative to BOTH its vehicle fleet AND its population")
    else:
        answer("Insufficient data for composite score — needs cars + per-10k for same year", AMBER)

    # ── Closing ───────────────────────────────────────────────────────────────
    print()
    print(f"  {CYAN}{'─' * 62}{RESET}")
    print(f"  {BOLD}All answers computed live from {total:,} stored accident rows.{RESET}")
    print(f"  {DIM}Sources: Unfallatlas (dl-de/by-2-0) · GENESIS 46251 · Regionalstatistik{RESET}")
    print(f"  {DIM}Every API response carries its source provenance and licence.{RESET}")
    print(f"  {CYAN}{'─' * 62}{RESET}")
    print()

    conn.close()


if __name__ == "__main__":
    main()
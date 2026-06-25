"""
Reproducible import / update script. Run from src/:
    python -m etl.run_import

Builds a fresh schema, seeds states, then loads (recording provenance for each):
  1. all Unfallatlas accident files under data/raw/unfallatlas/  (auto-discovered)
  2. registered cars              data/raw/regional-stats/registered_cars_2023.csv
  3. accidents per 10k            data/raw/regional-stats/accident_per_10000_per_city.csv
  4. district geometries          data/raw/boundaries/districts.geojson
"""
from datetime import datetime, timezone
import sqlite3

from etl.config import (CARS_FILE, CARS_YEAR, PER10K_FILE, PER10K_YEAR,
                        DISTRICTS_GEOJSON, DL_DE_BY_2_0, DL_DE_BY_2_0_URL)
from etl.db import get_connection, init_schema, reset_database
from etl.load_regions import seed_states
from etl.load_accidents import discover_files, load_file
from etl.load_indicators import load_registered_cars, load_accidents_per_10k
from etl.load_geometries import load_geometries


def _source(conn, name, url):
    cur = conn.execute("INSERT INTO data_sources (name, url, license, license_url) VALUES (?,?,?,?)",
                       (name, url, DL_DE_BY_2_0, DL_DE_BY_2_0_URL))
    conn.commit(); return cur.lastrowid


def _run(conn, source_id, snapshot):
    cur = conn.execute("INSERT INTO import_runs (source_id, retrieved_at, snapshot) VALUES (?,?,?)",
                       (source_id, datetime.now(timezone.utc).isoformat(), snapshot))
    conn.commit(); return cur.lastrowid


def _finish(conn, run_id, n):
    conn.execute("UPDATE import_runs SET record_count = ? WHERE import_run_id = ?", (n, run_id))
    conn.commit()


def main():
    reset_database()
    conn = get_connection(); init_schema(conn); seed_states(conn)

    # 1. Unfallatlas accidents (all years)
    ua = _source(conn, "Unfallatlas",
                 "https://www.opengeodata.nrw.de/produkte/transport_verkehr/unfallatlas/")
    files = discover_files()
    if not files:
        print("  ! No accident files found under data/raw/unfallatlas/")
    for f in files:
        run_id = _run(conn, ua, f.name)
        n = load_file(conn, f, run_id); _finish(conn, run_id, n)
        print(f"  loaded {n:>8,} accidents from {f.name}")

    # 2. Registered cars
    if CARS_FILE.exists():
        src = _source(conn, "GENESIS 46251 (registered cars)",
                      "https://www.regionalstatistik.de/genesis/online")
        run_id = _run(conn, src, CARS_FILE.name)
        n = load_registered_cars(conn, CARS_FILE, year=CARS_YEAR, import_run_id=run_id)
        _finish(conn, run_id, n)
        print(f"  loaded {n:>8,} car rows (year {CARS_YEAR}) from {CARS_FILE.name}")

    # 3. Accidents per 10k
    if PER10K_FILE.exists():
        src = _source(conn, "Regionalstatistik (accidents per 10k)",
                      "https://www.regionalstatistik.de/genesis/online")
        run_id = _run(conn, src, PER10K_FILE.name)
        n = load_accidents_per_10k(conn, PER10K_FILE, year=PER10K_YEAR, import_run_id=run_id)
        _finish(conn, run_id, n)
        print(f"  loaded {n:>8,} per-10k rows from {PER10K_FILE.name}")

    # 4. District geometries
    if DISTRICTS_GEOJSON.exists():
        src = _source(conn, "Regionalatlas (district geometries)",
                      "https://regionalatlas.statistikportal.de/")
        run_id = _run(conn, src, DISTRICTS_GEOJSON.name)
        n = load_geometries(conn, DISTRICTS_GEOJSON, import_run_id=run_id)
        _finish(conn, run_id, n)
        print(f"  loaded {n:>8,} district geometries from {DISTRICTS_GEOJSON.name}")

    _summary(conn); conn.close()


def _summary(conn: sqlite3.Connection):
    print("\n  --- database summary ---")
    for label, q in [
        ("accidents", "SELECT COUNT(*) FROM accidents"),
        ("years", "SELECT GROUP_CONCAT(DISTINCT year) FROM accidents"),
        ("regions", "SELECT COUNT(*) FROM regions"),
        ("  districts w/ geometry", "SELECT COUNT(*) FROM regions WHERE level='district' AND geometry IS NOT NULL"),
        ("indicator_values", "SELECT COUNT(*) FROM indicator_values"),
    ]:
        print(f"  {label:<24}: {conn.execute(q).fetchone()[0]}")


if __name__ == "__main__":
    main()
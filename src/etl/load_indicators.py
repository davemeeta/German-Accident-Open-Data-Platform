"""
Load regional indicators: registered passenger cars and the per-10k rate.

Two source layouts:

  registered cars (GENESIS 46251-01-03-4)
  ----------------------------------------
  Multi-header CSV (8 header rows), semicolon-delimited, latin-1 encoded.
  Column layout (0-indexed):
      0 = reference date  e.g. 01.01.2025
      1 = AGS             DG=Germany, 2-digit=state, 5-digit=district
      2 = name
      3 = all vehicles total
      4 = Personenkraftwagen insgesamt  <- passenger cars (what we want)
  Year is derived from the date column:
      01.01.2024 -> year 2023
      01.01.2025 -> year 2024
  Only 5-digit district rows are loaded; DG and state rows are skipped.
  File: data/raw/regional-stats/registered_cars_2024_2021.csv

  per-10k (Regionalstatistik)
  ---------------------------
  Simple flat table: schluessel;regionaleinheit;wert
  File: data/raw/regional-stats/accident_per_10000_per_city.csv
"""
from pathlib import Path
import sqlite3

import pandas as pd

from etl.load_regions import get_or_create_region


def _get_indicator_id(cur, code, name, unit, source):
    cur.execute("INSERT OR IGNORE INTO indicators (code, name, unit, source_system) "
                "VALUES (?,?,?,?)", (code, name, unit, source))
    return cur.execute(
        "SELECT indicator_id FROM indicators WHERE code = ?", (code,)).fetchone()[0]


def load_registered_cars(conn: sqlite3.Connection, path: Path, year: int,
                         import_run_id: int | None = None) -> int:
    """
    Load GENESIS 46251-01-03-4 multi-header CSV.
    Derives the year from col 0 (01.01.2025 -> 2024).
    Reads Personenkraftwagen insgesamt from col 4.
    Returns total rows written (summed across all years in the file).
    """
    cur = conn.cursor()
    ind_id = _get_indicator_id(cur, "CARS", "Registered passenger cars (Pkw)",
                               "vehicles", "GENESIS 46251")
    written = 0

    for line in Path(path).read_text(encoding="latin-1").splitlines():
        parts = line.split(";")
        if len(parts) < 5:
            continue

        # --- derive year from date column ---
        date_part = parts[0].strip()
        if not (date_part and date_part[0].isdigit() and "." in date_part):
            continue          # skip header rows
        try:
            ref_year = int(date_part.split(".")[-1])
            derived_year = ref_year - 1   # 01.01.2025 = end-of-2024 fleet
        except ValueError:
            continue

        # --- only 5-digit district rows ---
        ags = parts[1].strip()
        if not ags.isdigit() or len(ags) != 5:
            continue

        name  = parts[2].strip()
        raw   = parts[4].strip()          # Personenkraftwagen insgesamt
        if not raw.isdigit():
            continue

        region_id = get_or_create_region(conn, ags)
        if region_id is None:
            continue

        if name:
            cur.execute(
                "UPDATE regions SET name = ? "
                "WHERE region_id = ? AND (name IS NULL OR name = '')",
                (name, region_id))

        cur.execute(
            "INSERT OR REPLACE INTO indicator_values "
            "(region_id, indicator_id, year, value, import_run_id) VALUES (?,?,?,?,?)",
            (region_id, ind_id, derived_year, float(raw), import_run_id))
        written += 1

    conn.commit()
    return written


def load_accidents_per_10k(conn: sqlite3.Connection, path: Path, year: int,
                           import_run_id: int | None = None) -> int:
    """Regionalstatistik flat table: schluessel;regionaleinheit;wert."""
    raw_lines = Path(path).read_text(encoding="utf-8-sig").splitlines()
    header_idx = next(
        i for i, ln in enumerate(raw_lines) if ln.lower().startswith("schluessel;"))
    df = pd.read_csv(path, sep=";", dtype=str, encoding="utf-8-sig",
                     skiprows=header_idx, keep_default_na=False)
    df.columns = [c.strip().lower() for c in df.columns]

    cur = conn.cursor()
    ind_id = _get_indicator_id(cur, "ACC_PER_10K",
                               "Road accidents per 10,000 inhabitants",
                               "accidents/10k", "Regionalstatistik")
    written = 0
    for _, row in df.iterrows():
        ags = str(row.get("schluessel", "")).strip()
        if not ags:
            continue
        region_id = get_or_create_region(conn, ags)
        if region_id is None:
            continue
        name = str(row.get("regionaleinheit", "")).strip()
        if name:
            cur.execute(
                "UPDATE regions SET name = ? "
                "WHERE region_id = ? AND (name IS NULL OR name = '')",
                (name, region_id))
        val = str(row.get("wert", "")).replace(",", ".").strip()
        try:
            cur.execute(
                "INSERT OR REPLACE INTO indicator_values "
                "(region_id, indicator_id, year, value, import_run_id) VALUES (?,?,?,?,?)",
                (region_id, ind_id, year, float(val), import_run_id))
            written += 1
        except ValueError:
            pass
    conn.commit()
    return written
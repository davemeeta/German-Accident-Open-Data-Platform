"""
Load regional indicators: registered passenger cars and the per-10k rate.

Two different source layouts, so two parsers:
  * registered cars (GENESIS 46251-01-03-4): a multi-header table where the AGS
    is in column 2 and 'Personenkraftwagen / insgesamt' is column 5 (0-based 4),
    latin-1 encoded, counts as plain integers.
  * per-10k (Regionalstatistik): a simple schluessel;regionaleinheit;wert table.
"""
from pathlib import Path
import sqlite3

import pandas as pd

from etl.load_regions import get_or_create_region


def _get_indicator_id(cur, code, name, unit, source):
    cur.execute("INSERT OR IGNORE INTO indicators (code, name, unit, source_system) "
                "VALUES (?,?,?,?)", (code, name, unit, source))
    return cur.execute("SELECT indicator_id FROM indicators WHERE code = ?", (code,)).fetchone()[0]


def load_registered_cars(conn: sqlite3.Connection, path: Path, year: int,
                         import_run_id: int | None = None) -> int:
    """GENESIS 46251-01-03-4: AGS in col 1, passenger-car total in col 4. Returns rows written."""
    cur = conn.cursor()
    ind_id = _get_indicator_id(cur, "CARS", "Registered passenger cars (Pkw)",
                               "vehicles", "GENESIS 46251")
    written = 0
    for line in Path(path).read_text(encoding="latin-1").splitlines():
        parts = line.split(";")
        if len(parts) < 5:
            continue
        ags = parts[1].strip()
        if not ags.isdigit() or len(ags) != 5:   # keep only 5-digit district rows
            continue
        name = parts[2].strip()
        raw = parts[4].replace(".", "").replace(",", "").strip()  # integer count
        if not raw.isdigit():
            continue
        region_id = get_or_create_region(conn, ags)
        if region_id is None:
            continue
        if name:
            cur.execute("UPDATE regions SET name = ? WHERE region_id = ? AND (name IS NULL OR name='')",
                        (name, region_id))
        cur.execute("INSERT OR REPLACE INTO indicator_values "
                    "(region_id, indicator_id, year, value, import_run_id) VALUES (?,?,?,?,?)",
                    (region_id, ind_id, year, float(raw), import_run_id))
        written += 1
    conn.commit()
    return written


def load_accidents_per_10k(conn: sqlite3.Connection, path: Path, year: int,
                           import_run_id: int | None = None) -> int:
    """Regionalstatistik 'accidents per 10,000 inhabitants': schluessel;regionaleinheit;wert."""
    raw = Path(path).read_text(encoding="utf-8-sig").splitlines()
    header_idx = next(i for i, ln in enumerate(raw) if ln.lower().startswith("schluessel;"))
    df = pd.read_csv(path, sep=";", dtype=str, encoding="utf-8-sig",
                     skiprows=header_idx, keep_default_na=False)
    df.columns = [c.strip().lower() for c in df.columns]

    cur = conn.cursor()
    ind_id = _get_indicator_id(cur, "ACC_PER_10K", "Road accidents per 10,000 inhabitants",
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
            cur.execute("UPDATE regions SET name = ? WHERE region_id = ? AND (name IS NULL OR name='')",
                        (name, region_id))
        val = str(row.get("wert", "")).replace(",", ".").strip()
        try:
            cur.execute("INSERT OR REPLACE INTO indicator_values "
                        "(region_id, indicator_id, year, value, import_run_id) VALUES (?,?,?,?,?)",
                        (region_id, ind_id, year, float(val), import_run_id))
            written += 1
        except ValueError:
            pass
    conn.commit()
    return written
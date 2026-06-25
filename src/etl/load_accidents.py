"""
Load Unfallatlas accident files into the canonical schema.

Auto-discovers every Unfallorte*.{csv,txt} under data/raw/unfallatlas/ (any
nesting depth) and harmonises the year-to-year drift:
  * BOM / no BOM, UTF-8 / cp1252 encoding, CRLF line endings
  * ID column named UIDENTSTLAE / OBJECTID / OBJECTID_1 / OID_ / FID
  * light = ULICHTVERH or LICHT; road = IstStrassenzustand / STRZUSTAND / IstStrasse
  * is_other = IstSonstige or IstSonstig; is_goods absent in 2017 -> 0
  * coordinates with ',' or '.' decimals
Everything is read as text first so zero-padded region keys survive.
"""
from pathlib import Path
import sqlite3

import pandas as pd

from etl.config import UNFALLATLAS_DIR, UNFALLATLAS_COLUMN_MAP
from etl.load_regions import get_or_create_region

INT_FIELDS = ["year", "month", "hour", "weekday", "category", "kind", "type",
              "light", "road_condition"]
FLAG_FIELDS = ["is_bicycle", "is_car", "is_pedestrian", "is_motorcycle", "is_goods", "is_other"]


def discover_files(base: Path = UNFALLATLAS_DIR) -> list[Path]:
    """Every accident file under the unfallatlas tree, regardless of nesting."""
    files = [p for ext in ("*.csv", "*.txt")
             for p in base.rglob(ext) if p.name.lower().startswith("unfallorte")]
    return sorted(files)


def read_accident_csv(path: Path) -> pd.DataFrame:
    for enc in ("utf-8-sig", "cp1252", "latin1"):
        try:
            return pd.read_csv(path, sep=";", dtype=str, encoding=enc,
                               keep_default_na=False, na_values=[""])
        except UnicodeDecodeError:
            continue
    raise UnicodeDecodeError(f"Could not decode {path}")


def resolve_columns(df: pd.DataFrame, path: Path) -> dict[str, str]:
    lower = {c.lower().strip().lstrip("\ufeff"): c for c in df.columns}
    resolved = {}
    for field, candidates in UNFALLATLAS_COLUMN_MAP.items():
        for cand in candidates:
            if cand.lower() in lower:
                resolved[field] = lower[cand.lower()]
                break
    missing = [f for f in ("uland", "ukreis", "ugemeinde", "year") if f not in resolved]
    if missing:
        raise ValueError(f"{path.name}: missing required columns {missing}. "
                         f"Header: {list(df.columns)}")
    return resolved


def _build_ags(df, col) -> pd.Series:
    land = df[col["uland"]].fillna("").str.zfill(2)
    regbez = df[col["uregbez"]].fillna("0").str.zfill(1) if "uregbez" in col else "0"
    kreis = df[col["ukreis"]].fillna("").str.zfill(2)
    gem = df[col["ugemeinde"]].fillna("").str.zfill(3) if "ugemeinde" in col else "000"
    return land + regbez + kreis + gem


def _to_float(series: pd.Series) -> pd.Series:
    return pd.to_numeric(series.str.replace(",", ".", regex=False), errors="coerce")


def load_file(conn: sqlite3.Connection, path: Path, import_run_id: int | None = None) -> int:
    df = read_accident_csv(path)
    col = resolve_columns(df, path)
    ags = _build_ags(df, col)

    region_map = {a: get_or_create_region(conn, a) for a in ags.unique()}

    out = pd.DataFrame({"municipality_ags": ags})
    out["region_id"] = ags.map(region_map)
    out["source_uid"] = df[col["source_uid"]] if "source_uid" in col else None
    for f in INT_FIELDS:
        out[f] = pd.to_numeric(df[col[f]], errors="coerce") if f in col else None
    for f in FLAG_FIELDS:
        out[f] = (pd.to_numeric(df[col[f]], errors="coerce").fillna(0).astype(int)
                  if f in col else 0)
    out["lon"] = _to_float(df[col["lon"]]) if "lon" in col else None
    out["lat"] = _to_float(df[col["lat"]]) if "lat" in col else None
    out["import_run_id"] = import_run_id

    cols = (["source_uid", "region_id", "municipality_ags"] + INT_FIELDS + FLAG_FIELDS
            + ["lon", "lat", "import_run_id"])
    rows = [tuple(None if pd.isna(v) else v for v in rec)
            for rec in out[cols].itertuples(index=False, name=None)]
    placeholders = ",".join(["?"] * len(cols))
    conn.executemany(f"INSERT INTO accidents ({','.join(cols)}) VALUES ({placeholders})", rows)
    conn.commit()
    return len(rows)
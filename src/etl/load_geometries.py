import json
from pathlib import Path
import sqlite3
from etl.load_regions import get_or_create_region

_AGS_KEYS = ("AGS","RS","ARS","ags","rs","ars","id","krs_code","RS_0","SCH","GEN_KRS")

def _unwrap(v):
    if isinstance(v, list):
        return v[0] if v else None
    return v

def _find_ags(props, forced=None):
    for k in ([forced] if forced else _AGS_KEYS):
        if k and k in props and props[k] is not None:
            v = _unwrap(props[k])
            if v is None: continue
            s = str(v).strip()
            if s.isdigit():
                return s[:5] if len(s) >= 5 else s.zfill(5)
    if not forced:
        for v in props.values():
            v = _unwrap(v)
            if v is None: continue
            s = str(v).strip()
            if s.isdigit() and len(s) >= 5:
                return s[:5]
    return None

def load_geometries(conn, path, ags_property=None, import_run_id=None):
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    features = data["features"] if isinstance(data, dict) else data
    cur = conn.cursor()
    written = 0
    for f in features:
        props = f.get("properties", {}) or {}
        ags = _find_ags(props, ags_property)
        if not ags or "geometry" not in f: continue
        region_id = get_or_create_region(conn, ags)
        if region_id is None: continue
        cur.execute("UPDATE regions SET geometry = ? WHERE region_id = ?",
                    (json.dumps(f["geometry"]), region_id))
        name = (_unwrap(props.get("krs_name_short")) or _unwrap(props.get("krs_name"))
                or _unwrap(props.get("name")) or props.get("GEN") or props.get("BEZ"))
        if name:
            cur.execute("UPDATE regions SET name = ? WHERE region_id = ? AND (name IS NULL OR name='')",
                        (str(name), region_id))
        written += 1
    conn.commit()
    return written

"""
Region handling.

The 16 states + country are seeded from fixed official reference data.
Districts and municipalities are created on demand from the AGS codes found in
the accident data, with correct parent links (AGS is hierarchical):

    state = ags[:2]      district = ags[:5]      municipality = ags[:8]

Names for districts come later from the boundary GeoJSON / per-10k file.
"""
import sqlite3

from etl.config import STATE_NAMES


def seed_states(conn: sqlite3.Connection) -> None:
    """Insert the country (DG) and the 16 federal states. Idempotent."""
    cur = conn.cursor()
    cur.execute("INSERT OR IGNORE INTO regions (ags, name, level, parent_region_id) "
                "VALUES ('DG', 'Deutschland', 'country', NULL)")
    country_id = cur.execute("SELECT region_id FROM regions WHERE ags='DG'").fetchone()[0]
    for ags, name in STATE_NAMES.items():
        cur.execute("INSERT OR IGNORE INTO regions (ags, name, level, parent_region_id) "
                    "VALUES (?, ?, 'state', ?)", (ags, name, country_id))
    conn.commit()


def get_or_create_region(conn: sqlite3.Connection, ags: str) -> int | None:
    """
    Return region_id for an AGS, creating the municipality/district ancestors as
    needed. Accepts 5-digit (district) or 8-digit (municipality) keys.
    """
    if not ags or len(ags) < 5:
        return None
    cur = conn.cursor()
    state_ags, district_ags = ags[:2], ags[:5]
    mun_ags = ags[:8] if len(ags) >= 8 else None

    state_id = _lookup(cur, state_ags) or _insert(
        cur, state_ags, STATE_NAMES.get(state_ags, f"Land {state_ags}"), "state", _lookup(cur, "DG"))
    district_id = _lookup(cur, district_ags) or _insert(cur, district_ags, None, "district", state_id)
    if mun_ags is None:
        return district_id
    return _lookup(cur, mun_ags) or _insert(cur, mun_ags, None, "municipality", district_id)


def _lookup(cur, ags):
    r = cur.execute("SELECT region_id FROM regions WHERE ags = ?", (ags,)).fetchone()
    return r[0] if r else None


def _insert(cur, ags, name, level, parent_id):
    cur.execute("INSERT INTO regions (ags, name, level, parent_region_id) VALUES (?,?,?,?)",
                (ags, name, level, parent_id))
    return cur.lastrowid
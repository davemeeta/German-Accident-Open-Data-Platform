import difflib
import sqlite3
from typing import Optional

from mcp.server.fastmcp import FastMCP

from mcp_server.config import DB_PATH
from mcp_server.enums import Level

_UMLAUT_FOLD = str.maketrans({
    "ä": "ae", "ö": "oe", "ü": "ue", "ß": "ss",
    "Ä": "Ae", "Ö": "Oe", "Ü": "Ue",
})


def _fold(s: str) -> str:
    """ASCII-fold German umlauts/eszett (ü->ue, ö->oe, ä->ae, ß->ss) and lowercase,
    so a query typed without umlauts ("Muenchen") still matches a DB name that has
    them ("München"), and vice versa.
    """
    return s.translate(_UMLAUT_FOLD).lower()


def _fetch_named_regions(conn: sqlite3.Connection, level: Optional[str]) -> list[dict]:
    query = "SELECT ags, name, level FROM regions WHERE name IS NOT NULL"
    params: list = []
    if level:
        query += " AND level = ?"
        params.append(level)
    return [dict(r) for r in conn.execute(query, params).fetchall()]


def _search_regions(name: str, level: Optional[str], limit: int) -> tuple[list[dict], str]:
    """Read-only lookup against the `regions` table. This is the one tool in this
    server that does not go through the FastAPI backend: no HTTP endpoint exists
    for name -> AGS resolution, and this is reference/dimension data (identifiers
    and names), never accident metrics, so it sits outside the grounding
    constraint's concern (there is nothing here for an LLM to mis-narrate as a
    statistic). Opened with mode=ro so a write is impossible even by accident.

    Tries three stages, falling back only if the previous one found nothing:
    1. exact case-insensitive substring match (SQL LIKE)
    2. umlaut-folded substring match ("Muenchen" -> "München")
    3. fuzzy nearest-name suggestion (difflib) - for typos like "Bayren"

    Returns (matches, match_type) where match_type is "exact", "umlaut_folded",
    or "fuzzy_suggestion" - the caller should tell the LLM which one it got, since
    a fuzzy suggestion is a guess about what the user meant, not a confirmed match.
    """
    uri = f"file:{DB_PATH}?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        clauses = ["name IS NOT NULL", "name LIKE ?"]
        params: list = [f"%{name}%"]
        if level:
            clauses.append("level = ?")
            params.append(level)
        query = "SELECT ags, name, level FROM regions WHERE " + " AND ".join(clauses) + " ORDER BY level, name LIMIT ?"
        rows = [dict(r) for r in conn.execute(query, params + [limit]).fetchall()]
        if rows:
            return rows, "exact"

        all_rows = _fetch_named_regions(conn, level)

        folded_query = _fold(name)
        folded_matches = [r for r in all_rows if folded_query in _fold(r["name"])]
        if folded_matches:
            return folded_matches[:limit], "umlaut_folded"

        close_names = difflib.get_close_matches(name, [r["name"] for r in all_rows], n=limit, cutoff=0.6)
        if close_names:
            by_name = {r["name"]: r for r in all_rows}
            return [by_name[n] for n in close_names], "fuzzy_suggestion"

        return [], "none"
    finally:
        conn.close()


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def resolve_region(name: str, level: Optional[Level] = None, limit: int = 10) -> dict:
        """Look up the numeric AGS region code for a German place name, for use as
        the region_ags parameter of the other tools (state-level results can also
        feed the `state` enum by abbreviation if the name matches a state).
        Case-insensitive substring match against official region names, with two
        fallbacks if that finds nothing: umlaut-folded matching (so "Muenchen"
        still finds "München"), then fuzzy nearest-name suggestions for typos.

        IMPORTANT known data gap: municipality-level names are NOT populated in
        this database (only state and most district names are). A search for a
        small town/municipality will legitimately return no matches even though
        the AGS code exists in the accidents data - that is a real data-coverage
        limitation, not a bug. Cities that are their own urban district
        ("kreisfreie Stadt", e.g. Munich, Hamburg, Cologne) DO resolve, since
        those are district-level. If this returns no matches, say so explicitly
        rather than guessing an AGS code.

        name: place name or partial name, e.g. "Bayern", "München", "Cologne".
        level: optionally restrict to "state" or "district" (there is no usable
            "municipality" data to filter to - see above).

        Returns: {matches: [{ags, name, level}, ...], match_type} - empty list if
            nothing found even with fuzzy matching. match_type is "exact",
            "umlaut_folded", or "fuzzy_suggestion" - treat "fuzzy_suggestion"
            results as unconfirmed guesses about what the user meant, not a
            resolved answer: confirm with the user before using one, don't just
            pick the top suggestion. Multiple exact matches are also common (e.g.
            "München, kreisfreie Stadt" AND "München, Landkreis" both exist) - if
            ambiguous, ask the user which one they mean rather than picking one.
        """
        level_value = level.value if level else None
        matches, match_type = _search_regions(name, level_value, limit)
        return {"matches": matches, "match_type": match_type}

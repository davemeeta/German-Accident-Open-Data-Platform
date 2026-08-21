from typing import Optional

from mcp.server.fastmcp import FastMCP

from mcp_server.api_client import api_get
from mcp_server.enums import Category, CATEGORY_TO_INT, Level, Order, State, VehicleType, vehicle_types_to_flags


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_accident_count(
        state: Optional[State] = None,
        region_ags: Optional[str] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        category: Optional[Category] = None,
        vehicle_types: Optional[list[VehicleType]] = None,
    ) -> dict:
        """Total accident count matching filters. Use for single-number questions
        like "how many accidents in Bavaria in 2022" or "how many fatal accidents
        involving bicycles in March".

        state: one of the 16 German state abbreviations (e.g. "BY" for Bavaria).
            Full state/district/municipality NAMES are not accepted here - call
            resolve_region first to turn a name into an AGS code, then pass it as
            region_ags (also use region_ags, not state, for a state-level AGS code).
        region_ags: numeric AGS code (state/district/municipality) from resolve_region.
        category: severity filter - fatal, serious, or light. Omit for all severities.
        vehicle_types: restrict to accidents involving these road user types (each
            filter is independent and combines with AND, so ["pedestrian","bicycle"]
            means accidents involving BOTH a pedestrian and a bicycle, not either).

        Returns: {query: <filters actually applied>, accident_count: int, provenance: [...]}
        """
        flags = vehicle_types_to_flags(vehicle_types)
        params = {
            "state": state.value if state else None,
            "region": region_ags,
            "year": year,
            "month": month,
            "category": CATEGORY_TO_INT[category] if category else None,
            **flags,
        }
        data, _ = await api_get("/aggregates/accidents", params)
        return data

    @mcp.tool()
    async def get_accidents_by_region(
        level: Level = Level.state,
        year: Optional[int] = None,
        category: Optional[Category] = None,
        state: Optional[State] = None,
        region_ags: Optional[str] = None,
        vehicle_types: Optional[list[VehicleType]] = None,
        order: Order = Order.desc,
        limit: int = 20,
    ) -> dict:
        """Ranked list of accident counts grouped by state, district, or municipality.
        Use for "which states/districts have the most accidents" or "rank districts
        in Bavaria by accident count" style questions.

        level: the region granularity to group by (state / district / municipality).
        state / region_ags: optionally restrict to one state or one AGS subtree
            (e.g. region_ags of a state to rank its districts). Names must be
            resolved to AGS via resolve_region first.
        order: "desc" for most accidents first, "asc" for fewest first.
        limit: max rows returned (1-1000).

        Returns: {items: [{ags, name, level, year, accident_count}, ...]} as a raw list.
        """
        flags = vehicle_types_to_flags(vehicle_types)
        params = {
            "level": level.value,
            "year": year,
            "category": CATEGORY_TO_INT[category] if category else None,
            "state": state.value if state else None,
            "region": region_ags,
            "order": order.value,
            "limit": limit,
            **flags,
        }
        data, _ = await api_get("/aggregates/accidents/by-region", params)
        return {"items": data}

    @mcp.tool()
    async def get_accident_hotspots(
        precision: int = 3,
        min_count: int = 3,
        year: Optional[int] = None,
        state: Optional[State] = None,
        region_ags: Optional[str] = None,
        category: Optional[Category] = None,
        vehicle_types: Optional[list[VehicleType]] = None,
        weighted: bool = True,
        limit: int = 20,
    ) -> dict:
        """Geographic clusters of accidents ranked by severity or raw count. Use for
        "where are the most dangerous spots" style questions - this is spatial
        clustering of coordinates, not a per-district ranking (use
        get_accidents_by_region for that). Also answers "how many distinct
        hotspots are there" questions directly via the returned hotspot_count -
        that field is the count of clusters matching the filters, already
        computed by the tool, not something to count yourself from the list.

        precision: lat/lon rounding decimals for the grid (2=coarse ~1.1km cells,
            4=fine ~11m cells). Higher precision = smaller, more numerous clusters.
        min_count: drop clusters with fewer than this many accidents.
        weighted: if true, rank by a severity score (fatal x10 + serious x3 + light x1)
            instead of raw accident count.

        Returns: {ranked_by, severity_weights, hotspot_count, hotspots: [{lat, lon,
            district, total, fatal, serious, light, severity_score}, ...], provenance}
        """
        flags = vehicle_types_to_flags(vehicle_types)
        params = {
            "precision": precision,
            "min_count": min_count,
            "year": year,
            "state": state.value if state else None,
            "region": region_ags,
            "category": CATEGORY_TO_INT[category] if category else None,
            "weighted": weighted,
            "limit": limit,
            **flags,
        }
        data, _ = await api_get("/aggregates/hotspots", params)
        return data

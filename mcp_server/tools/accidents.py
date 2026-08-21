from typing import Optional

from mcp.server.fastmcp import FastMCP

from mcp_server.api_client import api_get
from mcp_server.enums import Category, CATEGORY_TO_INT, State, VehicleType, vehicle_types_to_flags


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def list_accidents(
        state: Optional[State] = None,
        region_ags: Optional[str] = None,
        year: Optional[int] = None,
        month: Optional[int] = None,
        weekday: Optional[int] = None,
        hour: Optional[int] = None,
        category: Optional[Category] = None,
        vehicle_types: Optional[list[VehicleType]] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> dict:
        """Paginated list of individual accident records with full detail (time,
        location, category, involved road users). Use only when the question needs
        specific example records or fields not covered by the aggregate tools (e.g.
        "show me some fatal accidents on a Sunday night in Berlin") - NOT for
        counting or ranking, use get_accident_count / get_accidents_by_region for
        those (this endpoint's "total" field is accurate but scanning items to
        count them yourself is wasteful and error-prone).

        weekday: 1-7 (backend's own numbering - do not assume 1=Monday without
            checking a returned record's weekday against a known date).
        hour: 0-23.
        limit: max records returned per call (1-1000). offset: pagination cursor.

        Returns: {total, limit, offset, items: [...raw accident records...], provenance}
        """
        flags = vehicle_types_to_flags(vehicle_types)
        params = {
            "state": state.value if state else None,
            "region": region_ags,
            "year": year,
            "month": month,
            "weekday": weekday,
            "hour": hour,
            "category": CATEGORY_TO_INT[category] if category else None,
            "limit": limit,
            "offset": offset,
            **flags,
        }
        data, _ = await api_get("/accidents", params)
        return data

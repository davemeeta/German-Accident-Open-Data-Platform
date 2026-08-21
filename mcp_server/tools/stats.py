from typing import Optional

from mcp.server.fastmcp import FastMCP

from mcp_server.api_client import api_get
from mcp_server.enums import Category, CATEGORY_TO_INT, State


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_accident_trend(
        state: Optional[State] = None,
        category: Optional[Category] = None,
    ) -> dict:
        """Year-by-year accident count time series. Use for "how has X changed over
        time" or "trend of fatal accidents in Bavaria" style questions, and as the
        basis for year-over-year comparisons.

        state: one of the 16 German state abbreviations. Omit for all of Germany.
            Does NOT accept district/municipality AGS or names - this endpoint
            only breaks down by state or nationwide.
        category: severity filter - fatal, serious, or light. Omit for all severities.

        Returns: {state, series: [{year, accident_count}, ...], provenance}
        """
        params = {
            "state": state.value if state else None,
            "category": CATEGORY_TO_INT[category] if category else None,
        }
        data, _ = await api_get("/stats/trend", params)
        return data

    @mcp.tool()
    async def get_first_data_year(state: Optional[State] = None) -> dict:
        """Earliest year for which accident data exists. Use for "since when do you
        have data" or "how far back does the data go" questions, and before
        interpreting a low count in an early year as a real trend rather than a
        data-coverage artifact.

        state: one of the 16 German state abbreviations. Omit for the overall
            dataset coverage.

        Returns: {state, first_year} or {scope: "overall", first_year}
        """
        data, _ = await api_get("/stats/first-year", {"state": state.value if state else None})
        return data

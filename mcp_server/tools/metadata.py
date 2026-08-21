from mcp.server.fastmcp import FastMCP

from mcp_server.api_client import api_get


def register(mcp: FastMCP) -> None:

    @mcp.tool()
    async def get_data_sources() -> dict:
        """List of upstream data sources backing this dataset, with license info.
        Use for "where does this data come from" / "what license is this data under"
        questions.

        Returns: {sources: [{source, license, license_url}, ...]}
        """
        data, _ = await api_get("/metadata/sources")
        return {"sources": data}

    @mcp.tool()
    async def get_import_runs() -> dict:
        """History of ETL import runs (when each data source was last loaded, and
        how many records). Use for "how fresh is this data" / "when was this last
        updated" questions.

        Returns: {runs: [{import_run_id, source, retrieved_at, snapshot, record_count}, ...]}
        """
        data, _ = await api_get("/import-runs")
        return {"runs": data}

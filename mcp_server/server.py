from mcp.server.fastmcp import FastMCP

from mcp_server.tools import accidents, aggregates, metadata, regions, stats


def create_server() -> FastMCP:
    mcp = FastMCP("unfallatlas-risk-lens")
    aggregates.register(mcp)
    stats.register(mcp)
    accidents.register(mcp)
    metadata.register(mcp)
    regions.register(mcp)
    return mcp


mcp = create_server()

if __name__ == "__main__":
    mcp.run()

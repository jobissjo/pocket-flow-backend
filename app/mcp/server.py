import asyncio
import logging
import sys
from typing import Optional

from pymongo import AsyncMongoClient

from app.core.config import settings
from app.core.database import init_db
from app.mcp.registry import tool_registry

# Import all tools to ensure they are registered in tool_registry
import app.mcp.tools  # noqa: F401

logger = logging.getLogger("pocketflow.mcp")

# Compatible with both MCP SDK v2 (MCPServer) and v1 (FastMCP)
try:
    from mcp.server.mcpserver import MCPServer
except ImportError:
    from mcp.server.fastmcp import FastMCP as MCPServer


def create_mcp_server() -> MCPServer:
    """Creates and configures the PocketFlow MCP Server with all domain tools."""
    server = MCPServer(
        name="PocketFlow",
    )

    # Register each tool from our modular registry
    for tool_meta in tool_registry.list_tools():
        server.tool(
            name=tool_meta.name,
            description=tool_meta.description,
        )(tool_meta.func)

    return server


mcp_server = create_mcp_server()


async def run_server(transport: str = "stdio"):
    """
    Initializes database connection and runs the MCP server.
    Used when launched via CLI or desktop client configuration.
    """
    logger.info("Connecting to MongoDB for PocketFlow MCP Server...")
    client: AsyncMongoClient = AsyncMongoClient(settings.MONGODB_URL)
    await init_db(client)
    logger.info("MongoDB initialized. Starting MCP Server...")

    try:
        if transport == "stdio":
            await mcp_server.run_stdio_async()
        elif transport == "sse":
            await mcp_server.run_sse_async()
        else:
            mcp_server.run(transport=transport)
    finally:
        client.close()


def main():
    """CLI entry point for running MCP server: python -m app.mcp.server [stdio|sse]"""
    transport = sys.argv[1] if len(sys.argv) > 1 else "stdio"
    asyncio.run(run_server(transport=transport))


if __name__ == "__main__":
    main()

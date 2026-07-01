"""Vissim MCP Server — Main Entry Point.

Bridges Claude (MCP Client) to PTV Vissim traffic simulation software.
Supports two backends:

    --backend mock   : Built-in demo mode, no license needed (default)
    --backend com    : Real Vissim via Windows COM (requires license + pywin32)

Usage:
    # Start with mock backend (default):
    python -m vissim_mcp.server

    # Start with COM backend:
    python -m vissim_mcp.server --backend com

    # As MCP server for Claude Desktop (stdio):
    python -m vissim_mcp.server --backend mock --transport stdio

    # With debug logging:
    python -m vissim_mcp.server --backend mock --debug

Claude Desktop config (claude_desktop_config.json):
    {
      "mcpServers": {
        "vissim": {
          "command": "python",
          "args": ["-m", "vissim_mcp.server", "--backend", "mock"],
          "cwd": "/path/to/vissim-mcp/src"
        }
      }
    }
"""

import argparse
import logging
import sys
from functools import partial

from mcp.server.fastmcp import FastMCP

from .backend.base import VissimBackend
from .tools.project import register_project_tools
from .tools.network import register_network_tools
from .tools.simulation import register_simulation_tools
from .tools.evaluation import register_evaluation_tools
from .tools.visualization import register_visualization_tools
from .tools.ai_tools import register_ai_tools

logger = logging.getLogger("vissim-mcp")

# ── Backend singleton ──────────────────────────────────────────
_backend: VissimBackend | None = None


def get_backend() -> VissimBackend:
    """Get or lazily connect the backend singleton."""
    global _backend
    if _backend is None:
        raise RuntimeError(
            "Backend not initialized. The 'vissim_connect' tool must be "
            "called first before any other Vissim operations."
        )
    return _backend


def create_server(backend_type: str = "mock") -> FastMCP:
    """Create and configure the MCP server with all tools registered.

    Args:
        backend_type: 'mock' (default, works everywhere) or 'com' (needs Vissim).

    Returns:
        Configured FastMCP server instance.
    """
    server = FastMCP(
        "PTV Vissim",
        json_response=True,
        instructions="""
        PTV Vissim MCP Server — traffic simulation control via MCP.

        This server connects Claude to PTV Vissim for microscopic traffic
        simulation. You can load networks, run simulations, query road
        elements, extract evaluation data (travel times, delays, queues),
        and modify network attributes.

        TWO MODES:
        - Mock mode (default): Built-in demo network with a 4-intersection
          urban corridor. Works everywhere, no license needed.
        - COM mode: Real PTV Vissim via Windows COM automation. Requires a
          licensed Vissim installation and Windows.

        WORKFLOW:
        1. Call vissim_connect() to start the engine
        2. Call vissim_load_net("path") to load a network
        3. Query network: vissim_get_links(), vissim_get_nodes(), etc.
        4. Run simulation: vissim_run_single_step() or vissim_run_continuous()
        5. Extract data: vissim_get_travel_times(), vissim_get_network_performance()
        6. Save and disconnect when done
        """,
    )

    # Initialize backend
    global _backend
    if backend_type == "mock":
        from .backend.mock_backend import MockBackend
        _backend = MockBackend()
        logger.info("Initialized Mock Backend (demo mode)")
    elif backend_type == "com":
        from .backend.com_backend import COMBackend
        _backend = COMBackend()
        logger.info("Initialized COM Backend (requires Vissim license)")
    else:
        raise ValueError(f"Unknown backend type: {backend_type}. Use 'mock' or 'com'.")

    # Register all tool groups
    _get = partial(get_backend)
    register_project_tools(server, _get)
    register_network_tools(server, _get)
    register_simulation_tools(server, _get)
    register_evaluation_tools(server, _get)
    register_visualization_tools(server, _get)
    register_ai_tools(server, _get)

    # ── Resources ──────────────────────────────────────────

    @server.resource("vissim://project/info")
    def project_info_resource() -> str:
        """Current project information as a readable resource."""
        import json
        backend = _backend
        if not backend.is_connected():
            return json.dumps({"connected": False, "message": "Not connected"})
        return json.dumps(backend.get_project_info(), indent=2)

    @server.resource("vissim://network/links")
    def links_resource() -> str:
        """All network links as JSON."""
        import json
        backend = _backend
        if not backend.is_connected():
            return json.dumps({"error": "Not connected"})
        return json.dumps(backend.get_links(limit=200), indent=2)

    @server.resource("vissim://simulation/status")
    def sim_status_resource() -> str:
        """Current simulation status as JSON."""
        import json
        backend = _backend
        if not backend.is_connected():
            return json.dumps({"error": "Not connected"})
        return json.dumps(backend.get_simulation_state(), indent=2)

    @server.resource("vissim://evaluation/network-performance")
    def np_resource() -> str:
        """Network performance data as JSON."""
        import json
        backend = _backend
        if not backend.is_connected():
            return json.dumps({"error": "Not connected"})
        return json.dumps(backend.get_network_performance(), indent=2)

    logger.info(f"Registered {len(server._mcp_tools) if hasattr(server, '_mcp_tools') else 'N'} tools")
    return server


def main():
    """CLI entry point for the Vissim MCP Server."""
    parser = argparse.ArgumentParser(
        description="PTV Vissim MCP Server — Bridge Claude to traffic simulation",
    )
    parser.add_argument(
        "--backend", choices=["mock", "com"], default="mock",
        help="Backend to use: 'mock' (default, no license needed) or 'com' (needs Vissim)",
    )
    parser.add_argument(
        "--transport", choices=["stdio", "http"], default="stdio",
        help="MCP transport: 'stdio' for Claude Desktop, 'http' for remote access",
    )
    parser.add_argument(
        "--host", default="127.0.0.1",
        help="Host for HTTP transport (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--port", type=int, default=8765,
        help="Port for HTTP transport (default: 8765)",
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args()

    # Configure logging
    level = logging.DEBUG if args.debug else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    logger.info(f"Starting Vissim MCP Server (backend={args.backend}, transport={args.transport})")

    server = create_server(args.backend)

    if args.transport == "http":
        import uvicorn
        app = server.streamable_http_app()
        logger.info(f"HTTP server at http://{args.host}:{args.port}")
        uvicorn.run(app, host=args.host, port=args.port)
    else:
        # stdio — standard for Claude Desktop
        logger.info("Starting stdio transport (for Claude Desktop)")
        server.run(transport="stdio")


if __name__ == "__main__":
    main()

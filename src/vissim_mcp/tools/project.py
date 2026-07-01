"""Project management tools: connect, load, save, get info."""

from typing import Optional
import json


def register_project_tools(mcp, get_backend):
    """Register all project management MCP tools."""

    @mcp.tool()
    def vissim_connect(visible: bool = True) -> dict:
        """Connect to PTV Vissim (or Mock Vissim in demo mode).

        On first call, this starts the Vissim engine. If Vissim is already
        running, it attaches to the existing instance.

        Args:
            visible: Whether to show the Vissim window (default True).
                     Set False for headless/background operation.
        """
        backend = get_backend()
        return backend.connect(visible=visible)

    @mcp.tool()
    def vissim_disconnect() -> dict:
        """Disconnect from Vissim. The simulation engine keeps running."""
        backend = get_backend()
        return backend.disconnect()

    @mcp.tool()
    def vissim_load_net(path: str) -> dict:
        """Load a Vissim network file (.inpx).

        In mock mode, this loads the built-in demo network (a 4-intersection
        urban corridor). In COM mode, loads a real Vissim network file.

        Args:
            path: Path to .inpx network file.
        """
        backend = get_backend()
        return backend.load_net(path)

    @mcp.tool()
    def vissim_load_layout(path: str) -> dict:
        """Load a Vissim layout file (.layx).

        The layout contains the graphical arrangement of the network view.

        Args:
            path: Path to .layx layout file.
        """
        backend = get_backend()
        return backend.load_layout(path)

    @mcp.tool()
    def vissim_save_net(path: Optional[str] = None) -> dict:
        """Save the current network. Saves to the current path if no path given.

        Args:
            path: Optional save path. If omitted, saves to the currently loaded path.
        """
        backend = get_backend()
        return backend.save_net(path)

    @mcp.tool()
    def vissim_get_project_info() -> dict:
        """Get summary information about the currently loaded Vissim project.

        Returns: network element counts, simulation state, and backend info.
        """
        backend = get_backend()
        return backend.get_project_info()
    

    @mcp.tool()
    async def ai_execute(query: str) -> str:
        backend = get_backend()
        result = backend.vissim_ai_execute(query=query)
        return json.dumps(result, indent=2)


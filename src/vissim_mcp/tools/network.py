"""Network query and editing tools: links, nodes, signals, inputs, routes."""

from typing import Any


def register_network_tools(mcp, get_backend):
    """Register all network-related MCP tools."""

    @mcp.tool()
    def vissim_get_links(limit: int = 50, offset: int = 0) -> list[dict]:
        """Get all road links (segments) in the Vissim network.

        Each link has: id, name, length, number of lanes, speed limit.

        Args:
            limit: Maximum number of links to return (default 50).
            offset: Pagination offset (0-based).
        """
        backend = get_backend()
        return backend.get_links(limit=limit, offset=offset)

    @mcp.tool()
    def vissim_get_nodes(limit: int = 50, offset: int = 0) -> list[dict]:
        """Get all nodes (intersections) in the Vissim network.

        Each node has: id, name, coordinates (x, y), type.

        Args:
            limit: Maximum number of nodes to return (default 50).
            offset: Pagination offset (0-based).
        """
        backend = get_backend()
        return backend.get_nodes(limit=limit, offset=offset)

    @mcp.tool()
    def vissim_get_signal_controllers() -> list[dict]:
        """Get all signal controllers (traffic lights) in the network.

        Each controller has: id, name, cycle time, number of signal groups, type.
        """
        backend = get_backend()
        return backend.get_signal_controllers()

    @mcp.tool()
    def vissim_get_vehicle_inputs() -> list[dict]:
        """Get all vehicle inputs (traffic demand entry points).

        Each input has: id, name, link ID, volume (veh/h), composition.
        """
        backend = get_backend()
        return backend.get_vehicle_inputs()

    @mcp.tool()
    def vissim_get_vehicle_routes() -> list[dict]:
        """Get all vehicle routing decisions.

        Each route has: id, name, input ID, destination, relative flow ratio.
        """
        backend = get_backend()
        return backend.get_vehicle_routes()

    @mcp.tool()
    def vissim_get_att_value(object_type: str, object_id: int, attribute: str) -> str:
        """Get an attribute value from any Vissim network object.

        This is the universal "getter" — works on links, nodes, signal
        controllers, vehicle inputs, and vehicle routes.

        Args:
            object_type: Type of object ('link', 'node', 'signalcontroller',
                         'vehicleinput', 'vehicleroute').
            object_id: Numeric ID of the object.
            attribute: Attribute name (e.g., 'Length', 'NumLanes', 'Volume(1)').
        """
        backend = get_backend()
        value = backend.get_att_value(object_type, object_id, attribute)
        return str(value)

    @mcp.tool()
    def vissim_set_att_value(object_type: str, object_id: int,
                              attribute: str, value: str) -> dict:
        """Set an attribute value on any Vissim network object.

        Args:
            object_type: Type of object ('link', 'node', 'signalcontroller', etc.).
            object_id: Numeric ID of the object.
            attribute: Attribute name (e.g., 'Volume(1)' for vehicle input volume).
            value: New value (numeric values are parsed automatically).
        """
        backend = get_backend()
        # Auto-convert numeric strings
        parsed = value
        try:
            if '.' in value:
                parsed = float(value)
            else:
                parsed = int(value)
        except ValueError:
            pass
        return backend.set_att_value(object_type, object_id, attribute, parsed)

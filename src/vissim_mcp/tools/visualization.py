"""Visualization tools: screenshots, view control."""


def register_visualization_tools(mcp, get_backend):
    """Register all visualization MCP tools."""

    @mcp.tool()
    def vissim_screenshot(width: int = 800, height: int = 600) -> str:
        """Capture a screenshot of the current Vissim network view.

        In mock mode, generates an SVG diagram of the demo network.
        In COM mode, captures the Vissim window.

        Args:
            width: Screenshot width in pixels (default 800).
            height: Screenshot height in pixels (default 600).
        """
        backend = get_backend()
        image_bytes = backend.get_screenshot(width, height)

        import base64
        b64 = base64.b64encode(image_bytes).decode('utf-8')
        # Detect if SVG or PNG
        if image_bytes.startswith(b'<?xml') or image_bytes.startswith(b'<svg'):
            mime = "image/svg+xml"
        else:
            mime = "image/png"
        return f"data:{mime};base64,{b64}"

    @mcp.tool()
    def vissim_zoom_to(target_type: str, target_id: int) -> dict:
        """Zoom the network view to a specific element.

        Args:
            target_type: Type of element: 'link', 'node', or 'signal'.
            target_id: Numeric ID of the target element.
        """
        backend = get_backend()
        return backend.zoom_to(target_type, target_id)

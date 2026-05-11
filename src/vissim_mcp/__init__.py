"""Vissim MCP — Model Context Protocol server for PTV Vissim traffic simulation.

Bridge Claude AI to Vissim via COM automation, with a built-in mock backend
for development and demonstration without a Vissim license.

Architecture:
    Claude (MCP Client)
        │  MCP Protocol (stdio)
        ▼
    Vissim MCP Server (FastMCP)
        │
        ▼
    Backend Interface (Abstract)
        ├── COM Backend  → PTV Vissim (pywin32, needs license)
        └── Mock Backend → Simulated Vissim (zero deps, always works)
"""

__version__ = "0.1.0"

# Vissim MCP

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Tests](https://img.shields.io/badge/tests-passing-brightgreen.svg)](./tests/)

**Model Context Protocol server for PTV Vissim traffic simulation.**

Bridge Claude AI (or any MCP-compatible LLM) to PTV Vissim for microscopic traffic simulation — load networks, run simulations, query road elements, extract evaluation data, and modify signal timings, all through natural language.



---

## Architecture

```
Claude / LLM Client
       │  MCP Protocol (stdio or HTTP)
       ▼
┌──────────────────────┐
│  Vissim MCP Server   │   FastMCP Python
│  ┌────────────────┐  │
│  │  35+ Tools     │  │   
│  │  4 Resources   │  │
│  └───────┬────────┘  │
│          │            │
│  ┌───────▼────────┐  │
│  │ Backend ABC    │  │   Strategy Pattern
│  └───┬───────┬────┘  │
│      │       │        │
│  ┌───▼──┐ ┌──▼────┐  │
│  │ Mock │ │  COM  │  │
│  │ (demo│ │(real) │  │
│  └──────┘ └───────┘  │
└──────────────────────┘
```

### Dual Backend Design

| Feature | Mock Backend | COM Backend |
|---------|-------------|-------------|
| **Requires Vissim** | No | Yes (license) |
| **Platform** | Any (Linux/macOS/Win) | Windows only |
| **Use case** | Dev, CI/CD, Demos | Production |
| **Data** | Built-in demo network | Real Vissim data |

The Mock Backend includes a realistic **4-intersection urban corridor** with:
- 8 road links (3 arterial + 5 collector)
- 4 nodes (3 signalized + 1 priority)
- 3 signal controllers (fixed + actuated)
- 4 vehicle inputs, 5 routing decisions

---

## Quick Start

### 1. Install

```bash
git clone https://github.com/XIEXIANG924/vissim-mcp.git
cd vissim-mcp
pip install -e ".[dev]"
```

### 2. Run tests (no Vissim needed)

```bash
pytest tests/ -v
```

### 3. Start the server (mock mode)

```bash
python -m vissim_mcp.server --backend mock
```

### 4. Connect with Claude Desktop

Add to `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "vissim": {
      "command": "python",
      "args": ["-m", "vissim_mcp.server", "--backend", "mock"],
      "cwd": "/path/to/vissim-mcp/src"
    }
  }
}
```

Then in Claude, try:

> "Connect to Vissim and tell me about the loaded network"

---

## Available Tools

### Project Management
| Tool | Description |
|------|-------------|
| `vissim_connect` | Connect to Vissim engine |
| `vissim_disconnect` | Disconnect |
| `vissim_load_net` | Load .inpx network file |
| `vissim_load_layout` | Load .layx layout file |
| `vissim_save_net` | Save current network |
| `vissim_get_project_info` | Project summary |

### Network Query
| Tool | Description |
|------|-------------|
| `vissim_get_links` | List all road links |
| `vissim_get_nodes` | List all nodes (intersections) |
| `vissim_get_signal_controllers` | List signal controllers |
| `vissim_get_vehicle_inputs` | List vehicle inputs |
| `vissim_get_vehicle_routes` | List routing decisions |
| `vissim_get_att_value` | Get any object attribute |
| `vissim_set_att_value` | Set any object attribute |

### Simulation Control
| Tool | Description |
|------|-------------|
| `vissim_run_single_step` | Run N simulation steps |
| `vissim_run_continuous` | Start continuous simulation |
| `vissim_stop` | Stop simulation |
| `vissim_get_simulation_state` | Current simulation status |
| `vissim_set_simulation_period` | Set start/end time |

### Evaluation & Data
| Tool | Description |
|------|-------------|
| `vissim_get_travel_times` | Vehicle travel time measurements |
| `vissim_get_delays` | Delay per vehicle |
| `vissim_get_queue_lengths` | Queue length at detectors |
| `vissim_get_network_performance` | Overall network statistics |
| `vissim_get_data_collection` | Data collection point results |

### Visualization
| Tool | Description |
|------|-------------|
| `vissim_screenshot` | Capture network view |
| `vissim_zoom_to` | Zoom to specific element |

---

## Example Conversation with Claude

```
User: Load the demo network and show me the road layout.

Claude: [calls vissim_connect → vissim_load_net("demo")
         → vissim_get_links() → vissim_screenshot()]
         
         Here's the demo network — a 4-intersection urban corridor
         along Main Street. 8 links total, 3 lanes on the arterial,
         2 lanes on collectors. Speed limit is 60 km/h on Main St.
         [SVG screenshot of the network]

User: Run the simulation for 30 minutes and give me performance stats.

Claude: [calls vissim_run_single_step(steps=1800)
         → vissim_get_network_performance()]
         
         After 30 minutes of simulation:
         - 245 vehicles processed
         - Average speed: 38.2 km/h
         - Average delay: 22.5 s/veh
         - Total distance traveled: 13,750 km

User: The delay at 1st Ave seems high. Increase its green time to 45 seconds.

Claude: [calls vissim_set_att_value("signalcontroller", 1, "CycleTime", 90)
         starts optimizing signal timing...]
```

---

## COM Backend Setup (Real Vissim)

If you have a licensed PTV Vissim installation on Windows:

```bash
# Install COM dependencies
pip install -e ".[com]"

# Start with COM backend
python -m vissim_mcp.server --backend com
```

Requirements:
- Windows OS
- PTV Vissim full license (COM is disabled in Demo/Student editions)
- Python 3.10+ 64-bit (must match Vissim architecture)
- pywin32 (`pip install pywin32`)

### Remote VS Code Access (Private Network)

The HTTP transport requires a bearer token. On the licensed Windows host, set
`VISSIM_API_TOKEN` in the server process environment, then start the server on
loopback:

```powershell
$env:VISSIM_API_TOKEN = "<long-random-token-from-your-approved-secret-store>"
vissim-mcp --backend com --transport http --host 127.0.0.1 --port 8765
```

Place a TLS reverse proxy or approved identity-aware gateway on the Windows host
and forward its `/mcp` route to `http://127.0.0.1:8765/mcp`. Restrict the proxy
and Windows Firewall to your LAN/VPN. Do not expose port 8765 directly or
forward it from the internet. Anyone with the bearer token can currently use
all MCP tools, including tools that modify or save a network; share it only with
trusted operators and rotate it when access should be revoked.
The remote HTTP server intentionally omits the AI code-generation and
code-execution tools because code execution would run with the Windows host's
permissions. For local stdio use of those tools, install the optional `ai`
extra; do not re-enable arbitrary code execution on a network-facing server.

On the client PC, add the remote server to VS Code's `mcp.json` and replace the
URL with the private HTTPS address configured on the proxy:

```json
{
  "servers": {
    "vissim": {
      "type": "http",
      "url": "https://vissim-host.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${input:vissim-token}"
      }
    }
  },
  "inputs": [
    {
      "type": "promptString",
      "id": "vissim-token",
      "description": "Vissim MCP bearer token",
      "password": true
    }
  ]
}
```

Reload the MCP server in VS Code and confirm it connects before using any
write-capable tools. The Vissim process and MCP server must remain running in
the Windows user session that can access the licensed Vissim installation.

---

## Project Structure

```
vissim-mcp/
├── README.md
├── pyproject.toml
├── LICENSE
├── src/vissim_mcp/
│   ├── __init__.py
│   ├── server.py              # MCP server entry point
│   ├── backend/
│   │   ├── __init__.py
│   │   ├── base.py            # Abstract backend interface
│   │   ├── mock_backend.py    # Demo backend (no Vissim needed)
│   │   └── com_backend.py     # Real Vissim COM backend
│   └── tools/
│       ├── __init__.py
│       ├── project.py         # Project management tools
│       ├── network.py         # Network query/edit tools
│       ├── simulation.py      # Simulation control tools
│       ├── evaluation.py      # Data extraction tools
│       └── visualization.py   # Screenshot/zoom tools
├── tests/
│   ├── __init__.py
│   └── test_mock_backend.py   # Comprehensive tests (run anywhere)
└── docs/
    └── ARCHITECTURE.md
```

---

## Why This Project?

For students and developers interested in:

- **MCP Protocol**: The hottest AI integration protocol of 2025-2026
- **Traffic Engineering**: Real-world domain knowledge meets software
- **Software Architecture**: Strategy pattern, dependency injection, abstract interfaces
- **Windows COM**: Low-level OS interop understanding
- **Open Source**: Clean, documented, tested — portfolio-ready

This project is designed to be resume-worthy: it demonstrates architecture design, testing methodology, domain modeling, and API design — all in a focused, single-purpose codebase.

---

## Roadmap

- [x] Mock backend with demo network
- [x] COM backend skeleton
- [x] 20+ MCP tools
- [x] Comprehensive test suite
- [ ] SUMO TraCI backend (free, open-source traffic simulator)
- [ ] Docker container with SUMO
- [ ] GitHub Actions CI/CD
- [ ] PyPI publication
- [ ] GIF demo of Claude controlling the simulation

---

## License

MIT — free to use, modify, and distribute.

## Acknowledgments

- [QGIS MCP](https://github.com/jjsantos01/qgis_mcp) by jjsantos01 — architectural inspiration
- [PTV Vissim](https://www.ptvgroup.com/en/products/ptv-vissim) — the traffic simulation engine
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk) — the protocol implementation

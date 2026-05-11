"""Mock backend simulating PTV Vissim behavior without requiring a license.

Provides a realistic demo traffic network (a 4-intersection urban corridor)
and simulates simulation steps, data extraction, and network editing.
Designed for:
1. Development and testing without Vissim
2. CI/CD pipelines on any platform (Linux/macOS/Windows)
3. Live demos — show Claude controlling a "traffic simulator"
"""

import time
import random
import math
from typing import Any, Optional

from .base import (
    VissimBackend,
    LinkInfo,
    NodeInfo,
    SignalControllerInfo,
    VehicleInputInfo,
    VehicleRouteInfo,
    SimulationState,
    EvaluationResult,
)


# ── Demo Network: 4-intersection urban corridor ──────────────

DEMO_LINKS = [
    LinkInfo(id=1, name="Main St West", number=1, length=300.0, num_lanes=3,
             speed_limit=60.0, link_type="arterial"),
    LinkInfo(id=2, name="Main St Central", number=2, length=250.0, num_lanes=3,
             speed_limit=60.0, link_type="arterial"),
    LinkInfo(id=3, name="Main St East", number=3, length=280.0, num_lanes=3,
             speed_limit=60.0, link_type="arterial"),
    LinkInfo(id=4, name="1st Ave North", number=4, length=200.0, num_lanes=2,
             speed_limit=40.0, link_type="collector"),
    LinkInfo(id=5, name="1st Ave South", number=5, length=200.0, num_lanes=2,
             speed_limit=40.0, link_type="collector"),
    LinkInfo(id=6, name="2nd Ave North", number=6, length=200.0, num_lanes=2,
             speed_limit=40.0, link_type="collector"),
    LinkInfo(id=7, name="2nd Ave South", number=7, length=200.0, num_lanes=2,
             speed_limit=40.0, link_type="collector"),
    LinkInfo(id=8, name="3rd Ave North", number=8, length=220.0, num_lanes=2,
             speed_limit=40.0, link_type="collector"),
]

DEMO_NODES = [
    NodeInfo(id=1, name="Main St / 1st Ave", number=1, x=0.0, y=0.0, node_type="signalized"),
    NodeInfo(id=2, name="Main St / 2nd Ave", number=2, x=250.0, y=0.0, node_type="signalized"),
    NodeInfo(id=3, name="Main St / 3rd Ave", number=3, x=530.0, y=0.0, node_type="signalized"),
    NodeInfo(id=4, name="Main St / 4th Ave", number=4, x=810.0, y=0.0, node_type="priority"),
]

DEMO_SIGNALS = [
    SignalControllerInfo(id=1, name="SC-1st Ave", number=1, cycle_time=90.0,
                         num_groups=4, signal_type="fixed"),
    SignalControllerInfo(id=2, name="SC-2nd Ave", number=2, cycle_time=90.0,
                         num_groups=4, signal_type="fixed"),
    SignalControllerInfo(id=3, name="SC-3rd Ave", number=3, cycle_time=120.0,
                         num_groups=4, signal_type="actuated"),
]

DEMO_VEHICLE_INPUTS = [
    VehicleInputInfo(id=1, name="Main St WB Inflow", link_id=3, volume=800.0,
                     composition_name="Urban Mixed"),
    VehicleInputInfo(id=2, name="Main St EB Inflow", link_id=1, volume=750.0,
                     composition_name="Urban Mixed"),
    VehicleInputInfo(id=3, name="1st Ave NB Inflow", link_id=5, volume=400.0,
                     composition_name="Urban Mixed"),
    VehicleInputInfo(id=4, name="2nd Ave SB Inflow", link_id=6, volume=350.0,
                     composition_name="Urban Mixed"),
]

DEMO_ROUTES = [
    VehicleRouteInfo(id=1, name="WB Through", input_id=1, destination_link_id=1,
                     relative_flow=0.6),
    VehicleRouteInfo(id=2, name="WB to 2nd Ave", input_id=1, destination_link_id=7,
                     relative_flow=0.2),
    VehicleRouteInfo(id=3, name="WB to 3rd Ave", input_id=1, destination_link_id=8,
                     relative_flow=0.2),
    VehicleRouteInfo(id=4, name="EB Through", input_id=2, destination_link_id=3,
                     relative_flow=0.7),
    VehicleRouteInfo(id=5, name="EB to 1st Ave", input_id=2, destination_link_id=5,
                     relative_flow=0.3),
]


class MockBackend(VissimBackend):
    """Mock Vissim backend with built-in demo network.

    Simulates a realistic 4-intersection urban corridor with:
    - 8 links (3 arterial, 5 collector)
    - 4 nodes (3 signalized, 1 priority)
    - 3 signal controllers
    - 4 vehicle inputs, 5 routing decisions

    Simulation steps advance time and update mock evaluation data
    using simple mathematical models (not real traffic simulation).
    """

    def __init__(self):
        self._connected = False
        self._project_loaded = False
        self._project_path: Optional[str] = None
        self._state = SimulationState()

        # Mutable copies of demo data (so edits persist during session)
        self._links: list[LinkInfo] = []
        self._nodes: list[NodeInfo] = []
        self._signals: list[SignalControllerInfo] = []
        self._inputs: list[VehicleInputInfo] = []
        self._routes: list[VehicleRouteInfo] = []

        # Evaluation state
        self._step_count = 0
        self._random = random.Random(42)  # seeded for reproducibility

    # ── Lifecycle ──────────────────────────────────────────────

    def connect(self, visible: bool = True) -> dict:
        if self._connected:
            return {"status": "already_connected", "message": "Already connected to Mock Vissim"}
        self._connected = True
        time.sleep(0.05)  # simulate COM connection delay
        return {
            "status": "connected",
            "backend": "mock",
            "version": "2026.0-mock",
            "visible": visible,
            "message": "Connected to Mock Vissim (demo mode — no license required)",
        }

    def disconnect(self) -> dict:
        self._connected = False
        self._project_loaded = False
        return {"status": "disconnected", "message": "Disconnected from Mock Vissim"}

    def is_connected(self) -> bool:
        return self._connected

    # ── Project Management ─────────────────────────────────────

    def load_net(self, path: str) -> dict:
        self._ensure_connected()
        # In mock mode, the demo network is always loaded
        self._links = [LinkInfo(**vars(l)) for l in DEMO_LINKS]
        self._nodes = [NodeInfo(**vars(n)) for n in DEMO_NODES]
        self._signals = [SignalControllerInfo(**vars(s)) for s in DEMO_SIGNALS]
        self._inputs = [VehicleInputInfo(**vars(i)) for i in DEMO_VEHICLE_INPUTS]
        self._routes = [VehicleRouteInfo(**vars(r)) for r in DEMO_ROUTES]
        self._project_loaded = True
        self._project_path = path
        self._state = SimulationState()
        self._step_count = 0

        return {
            "status": "loaded",
            "path": path,
            "links": len(self._links),
            "nodes": len(self._nodes),
            "signals": len(self._signals),
            "inputs": len(self._inputs),
            "routes": len(self._routes),
            "message": f"Loaded demo network from {path}",
        }

    def load_layout(self, path: str) -> dict:
        self._ensure_connected()
        return {"status": "loaded", "path": path, "message": f"Layout loaded: {path}"}

    def save_net(self, path: Optional[str] = None) -> dict:
        self._ensure_connected()
        save_path = path or self._project_path or "demo_network.inpx"
        return {"status": "saved", "path": save_path, "message": f"Saved to {save_path} (mock)"}

    def get_project_info(self) -> dict:
        self._ensure_connected()
        if not self._project_loaded:
            return {"loaded": False, "message": "No project loaded"}
        return {
            "loaded": True,
            "path": self._project_path or "(demo network)",
            "backend": "mock",
            "num_links": len(self._links),
            "num_nodes": len(self._nodes),
            "num_signals": len(self._signals),
            "num_vehicle_inputs": len(self._inputs),
            "num_vehicle_routes": len(self._routes),
            "simulation_state": self._state.to_dict(),
        }

    # ── Network Query ──────────────────────────────────────────

    def get_links(self, limit: int = 50, offset: int = 0) -> list[dict]:
        self._ensure_connected()
        return [l.to_dict() for l in self._links[offset:offset + limit]]

    def get_nodes(self, limit: int = 50, offset: int = 0) -> list[dict]:
        self._ensure_connected()
        return [n.to_dict() for n in self._nodes[offset:offset + limit]]

    def get_signal_controllers(self) -> list[dict]:
        self._ensure_connected()
        return [s.to_dict() for s in self._signals]

    def get_vehicle_inputs(self) -> list[dict]:
        self._ensure_connected()
        return [i.to_dict() for i in self._inputs]

    def get_vehicle_routes(self) -> list[dict]:
        self._ensure_connected()
        return [r.to_dict() for r in self._routes]

    def get_att_value(self, object_type: str, object_id: int, attribute: str) -> Any:
        self._ensure_connected()
        collection = self._get_collection(object_type)
        for obj in collection:
            if hasattr(obj, 'id') and obj.id == object_id:
                if hasattr(obj, attribute):
                    return getattr(obj, attribute)
                if isinstance(obj, dict) and attribute in obj:
                    return obj[attribute]
        raise ValueError(f"Object {object_type}#{object_id} not found or "
                         f"attribute '{attribute}' does not exist")

    # ── Simulation Control ─────────────────────────────────────

    def run_single_step(self, steps: int = 1) -> dict:
        self._ensure_connected()
        if self._state.simulation_second >= self._state.period_end:
            return {"status": "finished", "message": "Simulation period ended"}

        for _ in range(steps):
            if self._state.simulation_second >= self._state.period_end:
                break
            self._state.simulation_second += 1
            self._state.simulation_time += 1.0 / self._state.speed
            self._step_count += 1

        return {
            "status": "running" if not self._state.is_running else "stepping",
            "steps_executed": min(steps, self._state.period_end - max(0,
                                 self._state.simulation_second - steps)),
            "simulation_second": self._state.simulation_second,
            "simulation_time": round(self._state.simulation_time, 2),
        }

    def run_continuous(self) -> dict:
        self._ensure_connected()
        self._state.is_running = True
        return {"status": "started", "message": "Continuous simulation started"}

    def stop_simulation(self) -> dict:
        self._ensure_connected()
        was_running = self._state.is_running
        self._state.is_running = False
        return {
            "status": "stopped",
            "simulation_second": self._state.simulation_second,
            "message": "Simulation stopped" if was_running else "Simulation was not running",
        }

    def get_simulation_state(self) -> dict:
        self._ensure_connected()
        return self._state.to_dict()

    def set_simulation_period(self, start: int, end: int) -> dict:
        self._ensure_connected()
        self._state.period_start = start
        self._state.period_end = end
        return {
            "status": "set",
            "period_start_s": start,
            "period_end_s": end,
            "message": f"Simulation period set to [{start}, {end}]",
        }

    # ── Evaluation / Data Extraction ────────────────────────────

    def get_travel_times(self, measurement_id: int,
                         from_time: Optional[int] = None,
                         to_time: Optional[int] = None) -> list[dict]:
        self._ensure_connected()
        t = self._state.simulation_second
        return [
            EvaluationResult(
                name=f"TT_{measurement_id}",
                value=45.0 + 10 * math.sin(t / 300) + self._random.gauss(0, 3),
                unit="s",
                time_interval=(from_time or 0, to_time or t),
                details={"measurement_id": measurement_id, "num_vehicles": 120},
            ).to_dict()
        ]

    def get_delays(self, measurement_id: int,
                   from_time: Optional[int] = None,
                   to_time: Optional[int] = None) -> list[dict]:
        self._ensure_connected()
        t = self._state.simulation_second
        return [
            EvaluationResult(
                name=f"Delay_{measurement_id}",
                value=15.0 + 8 * math.sin(t / 360) + self._random.gauss(0, 2),
                unit="s/veh",
                time_interval=(from_time or 0, to_time or t),
                details={"measurement_id": measurement_id, "num_vehicles": 200},
            ).to_dict()
        ]

    def get_queue_lengths(self, counter_id: int,
                          from_time: Optional[int] = None,
                          to_time: Optional[int] = None) -> list[dict]:
        self._ensure_connected()
        t = self._state.simulation_second
        return [
            EvaluationResult(
                name=f"Queue_{counter_id}",
                value=max(0, 35.0 + 20 * math.sin(t / 180) + self._random.gauss(0, 5)),
                unit="m",
                time_interval=(from_time or 0, to_time or t),
                details={"counter_id": counter_id, "max_queue_m": 85.0, "avg_stops": 0.8},
            ).to_dict()
        ]

    def get_network_performance(self) -> list[dict]:
        self._ensure_connected()
        t = self._state.simulation_second
        return [
            EvaluationResult(
                name="Total Vehicles",
                value=float(200 + int(50 * math.sin(t / 600))),
                unit="veh",
                details={"active": True, "arrived": 180, "en_route": 20},
            ).to_dict(),
            EvaluationResult(
                name="Average Speed",
                value=38.0 + 5 * math.cos(t / 400) + self._random.gauss(0, 1),
                unit="km/h",
                details={"min_speed": 12.0, "max_speed": 58.0},
            ).to_dict(),
            EvaluationResult(
                name="Total Delay",
                value=450.0 + 100 * math.sin(t / 500) + self._random.gauss(0, 10),
                unit="s",
                details={"avg_delay_per_veh": 22.5, "stops_per_veh": 1.2},
            ).to_dict(),
            EvaluationResult(
                name="Total Distance",
                value=12500.0 + self._step_count * 15.0,
                unit="km",
                details={"avg_distance_per_veh": 2.8},
            ).to_dict(),
        ]

    def get_data_collection(self, collection_id: int) -> list[dict]:
        self._ensure_connected()
        t = self._state.simulation_second
        return [
            EvaluationResult(
                name=f"DC_{collection_id}",
                value=float(50 + int(20 * math.sin(t / 200 + collection_id))),
                unit="veh/h",
                details={"collection_id": collection_id, "interval_s": 300},
            ).to_dict()
        ]

    # ── Network Editing ────────────────────────────────────────

    def set_att_value(self, object_type: str, object_id: int,
                      attribute: str, value: Any) -> dict:
        self._ensure_connected()
        collection = self._get_collection(object_type)
        for obj in collection:
            if hasattr(obj, 'id') and obj.id == object_id:
                if hasattr(obj, attribute):
                    old = getattr(obj, attribute)
                    setattr(obj, attribute, value)
                    return {"status": "updated", "object": f"{object_type}#{object_id}",
                            "attribute": attribute, "old_value": old, "new_value": value}
        raise ValueError(f"Object {object_type}#{object_id} not found")

    # ── Visualization ──────────────────────────────────────────

    def get_screenshot(self, width: int = 800, height: int = 600) -> bytes:
        """Generate a simple SVG-based 'screenshot' of the network.
        In a real COM backend, this would capture Vissim's render window.
        """
        svg = f'''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="-100 -100 1000 300" width="{width}" height="{height}">
  <rect width="100%" height="100%" fill="#1a1a2e"/>
  <!-- Main St (horizontal arterial) -->
  <line x1="-80" y1="0" x2="900" y2="0" stroke="#e94560" stroke-width="8"/>
  <!-- Cross streets -->
  <line x1="0" y1="-80" x2="0" y2="80" stroke="#0f3460" stroke-width="5"/>
  <line x1="250" y1="-80" x2="250" y2="80" stroke="#0f3460" stroke-width="5"/>
  <line x1="530" y1="-80" x2="530" y2="80" stroke="#0f3460" stroke-width="5"/>
  <!-- Nodes (intersections) -->
  <circle cx="0" cy="0" r="10" fill="#e94560"/>
  <circle cx="250" cy="0" r="10" fill="#e94560"/>
  <circle cx="530" cy="0" r="10" fill="#e94560"/>
  <circle cx="810" cy="0" r="8" fill="#ffc107"/>
  <!-- Labels -->
  <text x="0" y="-15" text-anchor="middle" fill="white" font-size="10" font-family="monospace">1st Ave</text>
  <text x="250" y="-15" text-anchor="middle" fill="white" font-size="10" font-family="monospace">2nd Ave</text>
  <text x="530" y="-15" text-anchor="middle" fill="white" font-size="10" font-family="monospace">3rd Ave</text>
  <text x="400" y="25" text-anchor="middle" fill="white" font-size="12" font-family="monospace">Main St (Arterial)</text>
  <!-- Mock Vissim watermark -->
  <text x="800" y="280" text-anchor="end" fill="#555" font-size="8" font-family="monospace">Vissim MCP (Mock)</text>
</svg>'''
        return svg.encode('utf-8')

    def zoom_to(self, target_type: str, target_id: int) -> dict:
        self._ensure_connected()
        collection = self._get_collection(target_type)
        target = None
        for obj in collection:
            if hasattr(obj, 'id') and obj.id == target_id:
                target = obj
                break
        if target is None:
            raise ValueError(f"{target_type}#{target_id} not found")

        return {
            "status": "zoomed",
            "target_type": target_type,
            "target_id": target_id,
            "message": f"Zoomed to {target_type} #{target_id}: {getattr(target, 'name', '')}",
        }

    # ── Internal Helpers ───────────────────────────────────────

    def _ensure_connected(self):
        if not self._connected:
            raise RuntimeError("Not connected to Vissim. Call connect() first.")

    def _get_collection(self, object_type: str) -> list:
        type_map = {
            "link": self._links,
            "links": self._links,
            "node": self._nodes,
            "nodes": self._nodes,
            "signal": self._signals,
            "signalcontroller": self._signals,
            "vehicleinput": self._inputs,
            "vehicleinputs": self._inputs,
            "vehicleroute": self._routes,
            "vehicleroutes": self._routes,
        }
        key = object_type.lower().replace(" ", "").replace("_", "")
        if key not in type_map:
            raise ValueError(f"Unknown object type: {object_type}. "
                             f"Valid: {list(type_map.keys())}")
        return type_map[key]

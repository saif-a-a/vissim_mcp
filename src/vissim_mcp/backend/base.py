"""Abstract base class for Vissim backends.

Defines the contract that all backends must fulfill. This enables:
1. Mock Backend: for development and CI/CD without a Vissim license
2. COM Backend: for real Vissim automation (requires license + Windows)
3. Future backends: e.g., SUMO TraCI for free traffic simulation

Design note: Methods return plain Python dicts/lists — the MCP layer
is responsible for formatting these into MCP-compatible responses.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class LinkInfo:
    """Represents a Vissim link (road segment)."""
    id: int
    name: str = ""
    number: int = 0
    length: float = 0.0
    num_lanes: int = 1
    speed_limit: float = 50.0  # km/h
    link_type: str = "urban"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "number": self.number,
            "length_m": self.length,
            "num_lanes": self.num_lanes,
            "speed_limit_kmh": self.speed_limit,
            "link_type": self.link_type,
        }


@dataclass
class NodeInfo:
    """Represents a Vissim node (intersection)."""
    id: int
    name: str = ""
    number: int = 0
    x: float = 0.0
    y: float = 0.0
    node_type: str = "priority"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "number": self.number,
            "x": self.x,
            "y": self.y,
            "node_type": self.node_type,
        }


@dataclass
class SignalControllerInfo:
    """Represents a signal controller (traffic light)."""
    id: int
    name: str = ""
    number: int = 0
    cycle_time: float = 90.0  # seconds
    num_groups: int = 0
    signal_type: str = "fixed"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "number": self.number,
            "cycle_time_s": self.cycle_time,
            "num_groups": self.num_groups,
            "signal_type": self.signal_type,
        }


@dataclass
class VehicleInputInfo:
    """Represents a vehicle input (traffic demand entry point)."""
    id: int
    name: str = ""
    link_id: int = 0
    volume: float = 0.0  # vehicles per hour
    composition_name: str = "Default"

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "link_id": self.link_id,
            "volume_veh_h": self.volume,
            "composition_name": self.composition_name,
        }


@dataclass
class VehicleRouteInfo:
    """Represents a vehicle routing decision."""
    id: int
    name: str = ""
    input_id: int = 0
    destination_link_id: int = 0
    relative_flow: float = 1.0

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "input_id": self.input_id,
            "destination_link_id": self.destination_link_id,
            "relative_flow": self.relative_flow,
        }


@dataclass
class SimulationState:
    """Current simulation state."""
    is_running: bool = False
    simulation_time: float = 0.0  # simulation seconds
    simulation_second: int = 0
    period_start: int = 0
    period_end: int = 3600
    speed: int = 1

    def to_dict(self) -> dict:
        return {
            "is_running": self.is_running,
            "simulation_time_s": self.simulation_time,
            "simulation_second": self.simulation_second,
            "period_start_s": self.period_start,
            "period_end_s": self.period_end,
            "speed": self.speed,
        }


@dataclass
class EvaluationResult:
    """Generic evaluation result container."""
    name: str
    value: float
    unit: str = ""
    time_interval: Optional[tuple[int, int]] = None
    details: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {
            "name": self.name,
            "value": self.value,
            "unit": self.unit,
        }
        if self.time_interval:
            d["from_time_s"] = self.time_interval[0]
            d["to_time_s"] = self.time_interval[1]
        d.update(self.details)
        return d


class VissimBackend(ABC):
    """Abstract interface for all Vissim-compatible backends.

    Every method returns plain Python types (dict, list, str, int, float).
    The MCP server layer transforms these into MCP Tool responses.
    """

    # ── Lifecycle ──────────────────────────────────────────────

    @abstractmethod
    def connect(self, visible: bool = True) -> dict:
        """Connect to the simulation engine. Returns status info."""

    @abstractmethod
    def disconnect(self) -> dict:
        """Disconnect from the simulation engine."""

    @abstractmethod
    def is_connected(self) -> bool:
        """Check if the backend is currently connected."""

    # ── Project Management ─────────────────────────────────────

    @abstractmethod
    def load_net(self, path: str) -> dict:
        """Load a Vissim network file (.inpx)."""

    @abstractmethod
    def load_layout(self, path: str) -> dict:
        """Load a Vissim layout file (.layx)."""

    @abstractmethod
    def save_net(self, path: Optional[str] = None) -> dict:
        """Save the current network."""

    @abstractmethod
    def get_project_info(self) -> dict:
        """Get summary info about the loaded project."""

    # ── Network Query ──────────────────────────────────────────

    @abstractmethod
    def get_links(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get all links in the network."""

    @abstractmethod
    def get_nodes(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get all nodes in the network."""

    @abstractmethod
    def get_signal_controllers(self) -> list[dict]:
        """Get all signal controllers."""

    @abstractmethod
    def get_vehicle_inputs(self) -> list[dict]:
        """Get all vehicle inputs."""

    @abstractmethod
    def get_vehicle_routes(self) -> list[dict]:
        """Get all vehicle routing decisions."""

    @abstractmethod
    def get_att_value(self, object_type: str, object_id: int, attribute: str) -> Any:
        """Get a single attribute value from a Vissim object."""

    # ── Simulation Control ─────────────────────────────────────

    @abstractmethod
    def run_single_step(self, steps: int = 1) -> dict:
        """Advance simulation by N steps."""

    @abstractmethod
    def run_continuous(self) -> dict:
        """Start continuous simulation."""

    @abstractmethod
    def stop_simulation(self) -> dict:
        """Stop the running simulation."""

    @abstractmethod
    def get_simulation_state(self) -> dict:
        """Get current simulation state."""

    @abstractmethod
    def set_simulation_period(self, start: int, end: int) -> dict:
        """Set simulation period (in simulation seconds)."""

    # ── Evaluation / Data Extraction ────────────────────────────

    @abstractmethod
    def get_travel_times(self, measurement_id: int,
                         from_time: Optional[int] = None,
                         to_time: Optional[int] = None) -> list[dict]:
        """Get vehicle travel time measurements."""

    @abstractmethod
    def get_delays(self, measurement_id: int,
                   from_time: Optional[int] = None,
                   to_time: Optional[int] = None) -> list[dict]:
        """Get delay measurements."""

    @abstractmethod
    def get_queue_lengths(self, counter_id: int,
                          from_time: Optional[int] = None,
                          to_time: Optional[int] = None) -> list[dict]:
        """Get queue length counter results."""

    @abstractmethod
    def get_network_performance(self) -> list[dict]:
        """Get vehicle network performance statistics."""

    @abstractmethod
    def get_data_collection(self, collection_id: int) -> list[dict]:
        """Get data collection point measurements."""

    # ── Network Editing (optional helper) ──────────────────────

    @abstractmethod
    def set_att_value(self, object_type: str, object_id: int,
                      attribute: str, value: Any) -> dict:
        """Set an attribute value on a Vissim object."""

    # ── Visualization ──────────────────────────────────────────

    @abstractmethod
    def get_screenshot(self, width: int = 800, height: int = 600) -> bytes:
        """Capture a screenshot of the current network view. Returns PNG bytes."""

    @abstractmethod
    def zoom_to(self, target_type: str, target_id: int) -> dict:
        """Zoom the network view to a specific element.

        target_type: 'link', 'node', 'signal'
        """

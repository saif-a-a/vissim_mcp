"""Real PTV Vissim backend via Windows COM automation.

Requires:
- Windows OS
- PTV Vissim with COM license (full version, NOT demo/student)
- pywin32: pip install pywin32
- Python 3.9+ 64-bit (must match Vissim architecture)

COM Object Hierarchy:
    Vissim.Vissim (ProgID)
    ├── .Net          → INetwork
    ├── .Simulation   → ISimulation
    ├── .Evaluation   → IEvaluation
    └── .Graphics     → IGraphics
"""

from typing import Any, Optional

from .base import VissimBackend
import json
import textwrap
import anthropic



class COMBackend(VissimBackend):
    """Real Vissim backend using Windows COM automation.

    This backend requires a licensed PTV Vissim installation on Windows.
    Without a license, use MockBackend instead.
    """

    def __init__(self):
        self._vissim = None
        self._connected = False

    # ── Lifecycle ──────────────────────────────────────────────

    def connect(self, visible: bool = True) -> dict:
        if self._connected:
            return {"status": "already_connected", "message": "Already connected to Vissim"}

        try:
            import pythoncom
            pythoncom.CoInitialize()
        except ImportError:
            pass  # may already be initialized

        try:
            import win32com.client
        except ImportError:
            raise ImportError(
                "pywin32 is required for COM backend. "
                "Install with: pip install pywin32"
            )

        try:
            # Try to attach to running instance first
            self._vissim = win32com.client.GetActiveObject("Vissim.Vissim")
        except Exception:
            # Start a new instance
            self._vissim = win32com.client.Dispatch("Vissim.Vissim")

        # Try to set visibility (may not be supported on all instances)
        try:
            self._vissim.Visible = visible
        except Exception:
            pass  # Visible property may not be settable on running instances
        
        self._connected = True

        return {
            "status": "connected",
            "backend": "com",
            "version": self._safe_get("Vissim", "Version"),
            "visible": visible,
            "message": "Connected to PTV Vissim via COM",
        }

    def disconnect(self) -> dict:
        self._vissim = None
        self._connected = False
        return {"status": "disconnected", "message": "Disconnected from Vissim"}

    def is_connected(self) -> bool:
        return self._connected and self._vissim is not None

    # ── Project Management ─────────────────────────────────────

    def load_net(self, path: str) -> dict:
        self._ensure_connected()
        self._vissim.LoadNet(path)
        return {"status": "loaded", "path": path, "message": f"Loaded: {path}"}

    def load_layout(self, path: str) -> dict:
        self._ensure_connected()
        self._vissim.LoadLayout(path)
        return {"status": "loaded", "path": path, "message": f"Layout loaded: {path}"}

    def save_net(self, path: Optional[str] = None) -> dict:
        self._ensure_connected()
        if path:
            self._vissim.SaveNetAs(path)
        else:
            self._vissim.SaveNet()
        return {"status": "saved", "path": path or "(current)", "message": "Saved"}

    def get_project_info(self) -> dict:
        self._ensure_connected()
        net = self._vissim.Net
        
        # Safely get counts for each collection
        try:
            num_links = net.Links.Count
        except Exception:
            num_links = 0
        
        try:
            num_nodes = net.Nodes.Count
        except Exception:
            num_nodes = 0
        
        try:
            num_signals = net.SignalControllers.Count
        except Exception:
            num_signals = 0
        
        try:
            num_vehicle_inputs = net.VehicleInputs.Count
        except Exception:
            num_vehicle_inputs = 0
        
        try:
            num_vehicle_routes = net.VehicleRoutes.Count
        except Exception:
            num_vehicle_routes = 0
        
        return {
            "loaded": True,
            "backend": "com",
            "version": self._safe_get(self._vissim, "Version", "unknown"),
            "num_links": num_links,
            "num_nodes": num_nodes,
            "num_signals": num_signals,
            "num_vehicle_inputs": num_vehicle_inputs,
            "num_vehicle_routes": num_vehicle_routes,
            "simulation_state": self.get_simulation_state(),
        }

    # ── Network Query ──────────────────────────────────────────

    def get_links(self, limit: int = 50, offset: int = 0) -> list[dict]:
        self._ensure_connected()
        try:
            links = self._vissim.Net.Links
        except Exception as e:
            return [{"error": f"Failed to access links: {e}"}]
        
        result = []
        try:
            count = links.Count
        except Exception:
            count = 0
        
        for i in range(offset + 1, min(offset + limit + 1, count + 1)):
            try:
                # Try using parentheses first
                try:
                    link = links(i)
                except Exception:
                    link = links.Item(i)
                result.append({
                    "id": i,
                    "name": self._safe_get(link, "Name", f"Link_{i}"),
                    "number": i,
                    "length_m": self._safe_get(link, "AttValue('Length')", 0.0),
                    "num_lanes": self._safe_get(link, "AttValue('NumLanes')", 1),
                })
            except Exception as e:
                result.append({"error": f"Failed to access link {i}: {e}"})
        return result

    def get_nodes(self, limit: int = 50, offset: int = 0) -> list[dict]:
        self._ensure_connected()
        try:
            nodes = self._vissim.Net.Nodes
        except Exception as e:
            return [{"error": f"Failed to access nodes: {e}"}]
        
        result = []
        try:
            count = nodes.Count
        except Exception:
            count = 0
        
        for i in range(offset + 1, min(offset + limit + 1, count + 1)):
            try:
                # Try using parentheses first
                try:
                    node = nodes(i)
                except Exception:
                    node = nodes.Item(i)
                result.append({
                    "id": i,
                    "name": self._safe_get(node, "Name", f"Node_{i}"),
                    "number": i,
                })
            except Exception as e:
                result.append({"error": f"Failed to access node {i}: {e}"})
        return result

    def get_signal_controllers(self) -> list[dict]:
        self._ensure_connected()
        try:
            scs = self._vissim.Net.SignalControllers
        except Exception as e:
            return [{"error": f"Failed to access signal controllers: {e}"}]
        
        result = []
        try:
            count = scs.Count
        except Exception:
            count = 0
        
        for i in range(1, count + 1):
            try:
                # Try using parentheses first
                try:
                    sc = scs(i)
                except Exception:
                    sc = scs.Item(i)
                result.append({
                    "id": i,
                    "name": self._safe_get(sc, "Name", f"SC_{i}"),
                    "number": i,
                    "cycle_time_s": self._safe_get(sc, "AttValue('CycleTime')", 0.0),
                    "num_groups": self._safe_get(sc.SignalGroups, "Count", 0),
                })
            except Exception as e:
                result.append({"error": f"Failed to access signal controller {i}: {e}"})
        return result

    def get_vehicle_inputs(self) -> list[dict]:
        self._ensure_connected()
        try:
            inputs = self._vissim.Net.VehicleInputs
        except Exception as e:
            return [{"error": f"Failed to access vehicle inputs: {e}"}]
        
        result = []
        try:
            count = inputs.Count
        except Exception:
            count = 0
        
        for i in range(1, count + 1):
            try:
                # Try using parentheses instead of Item()
                vi = inputs(i)
                result.append({
                    "id": i,
                    "name": self._safe_get(vi, "Name", f"VI_{i}"),
                    "link_id": self._safe_get(vi, "AttValue('Link')", 0),
                    "volume_veh_h": self._safe_get(vi, "AttValue('Volume(1)')", 0.0),
                })
            except Exception as e:
                # If parentheses don't work, try Item()
                try:
                    vi = inputs.Item(i)
                    result.append({
                        "id": i,
                        "name": self._safe_get(vi, "Name", f"VI_{i}"),
                        "link_id": self._safe_get(vi, "AttValue('Link')", 0),
                        "volume_veh_h": self._safe_get(vi, "AttValue('Volume(1)')", 0.0),
                    })
                except Exception as e2:
                    result.append({"error": f"Failed to access vehicle input {i}: {e} / {e2}"})
        return result

    def get_vehicle_routes(self) -> list[dict]:
        self._ensure_connected()
        try:
            routes = self._vissim.Net.VehicleRoutes
        except Exception as e:
            return [{"error": f"Failed to access vehicle routes: {e}"}]
        
        result = []
        try:
            count = routes.Count
        except Exception:
            count = 0
        
        for i in range(1, count + 1):
            try:
                # Try using parentheses first
                try:
                    vr = routes(i)
                except Exception:
                    vr = routes.Item(i)
                result.append({
                    "id": i,
                    "name": self._safe_get(vr, "Name", f"VR_{i}"),
                    "input_id": 0,
                    "relative_flow": self._safe_get(vr, "AttValue('RelFlow(1)')", 1.0),
                })
            except Exception as e:
                result.append({"error": f"Failed to access vehicle route {i}: {e}"})
        return result

    def get_att_value(self, object_type: str, object_id: int, attribute: str) -> Any:
        self._ensure_connected()
        obj = self._resolve_object(object_type, object_id)
        return obj.AttValue(attribute)

    # ── Simulation Control ─────────────────────────────────────

    def run_single_step(self, steps: int = 1) -> dict:
        self._ensure_connected()
        sim = self._vissim.Simulation
        for _ in range(steps):
            sim.RunSingleStep()
        return {
            "status": "stepped",
            "steps_executed": steps,
            "simulation_second": sim.SimulationSecond,
            "simulation_time": round(sim.SimulationTime, 2),
        }

    def run_continuous(self) -> dict:
        self._ensure_connected()
        self._vissim.Simulation.RunContinuous()
        return {"status": "started", "message": "Continuous simulation started"}

    def stop_simulation(self) -> dict:
        self._ensure_connected()
        self._vissim.Simulation.Stop()
        return {"status": "stopped", "message": "Simulation stopped"}

    def get_simulation_state(self) -> dict:
        self._ensure_connected()
        try:
            sim = self._vissim.Simulation
            is_running = self._safe_get(sim, "IsSimulationRunning", False)
            sim_time = self._safe_get(sim, "SimulationTime", 0.0)
            sim_second = self._safe_get(sim, "SimulationSecond", 0)
            speed = self._safe_get(sim, "Speed", 1)
            return {
                "is_running": is_running,
                "simulation_time_s": sim_time,
                "simulation_second": sim_second,
                "speed": speed,
            }
        except Exception as e:
            return {
                "is_running": False,
                "simulation_time_s": 0.0,
                "simulation_second": 0,
                "speed": 1,
                "error": str(e),
            }

    def set_simulation_period(self, start: int, end: int) -> dict:
        self._ensure_connected()
        try:
            sim = self._vissim.Simulation
            sim.PeriodStartTime = start
            sim.PeriodEndTime = end
            return {"status": "set", "period_start_s": start, "period_end_s": end}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # ── Evaluation / Data Extraction ────────────────────────────

    def get_travel_times(self, measurement_id: int,
                         from_time: Optional[int] = None,
                         to_time: Optional[int] = None) -> list[dict]:
        self._ensure_connected()
        tt = self._vissim.Evaluation.VehicleTravelTimes.Item(measurement_id)
        # COM: GetResult(AttName, from, to) returns data
        if from_time is not None and to_time is not None:
            result = tt.GetResult("TravTime", "Mean", from_time, to_time)
        else:
            result = tt.GetResult("TravTime", "Mean", "", "")
        return [{"name": f"TT_{measurement_id}", "value": result, "unit": "s"}]

    def get_delays(self, measurement_id: int,
                   from_time: Optional[int] = None,
                   to_time: Optional[int] = None) -> list[dict]:
        self._ensure_connected()
        delay = self._vissim.Evaluation.Delay.Item(measurement_id)
        if from_time is not None and to_time is not None:
            result = delay.GetResult("Delay", "Mean", from_time, to_time)
        else:
            result = delay.GetResult("Delay", "Mean", "", "")
        return [{"name": f"Delay_{measurement_id}", "value": result, "unit": "s/veh"}]

    def get_queue_lengths(self, counter_id: int,
                          from_time: Optional[int] = None,
                          to_time: Optional[int] = None) -> list[dict]:
        self._ensure_connected()
        qc = self._vissim.Evaluation.QueueCounters.Item(counter_id)
        if from_time is not None and to_time is not None:
            result = qc.GetResult("QueueLen", "Mean", from_time, to_time)
        else:
            result = qc.GetResult("QueueLen", "Mean", "", "")
        return [{"name": f"Queue_{counter_id}", "value": result, "unit": "m"}]

    def get_network_performance(self) -> list[dict]:
        self._ensure_connected()
        vnp = self._vissim.Evaluation.VehicleNetworkPerformance
        return [
            {"name": "Total Vehicles", "value": vnp.TotalVehicles, "unit": "veh"},
            {"name": "Average Speed", "value": vnp.AverageSpeed, "unit": "km/h"},
            {"name": "Total Delay", "value": vnp.TotalDelay, "unit": "s"},
            {"name": "Total Distance", "value": vnp.TotalDistance, "unit": "km"},
        ]

    def get_data_collection(self, collection_id: int) -> list[dict]:
        self._ensure_connected()
        dc = self._vissim.Evaluation.DataCollections.Item(collection_id)
        result = dc.GetResult("Volume", "Sum", "", "")
        return [{"name": f"DC_{collection_id}", "value": result, "unit": "veh/h"}]

    # ── Network Editing ────────────────────────────────────────

    def set_att_value(self, object_type: str, object_id: int,
                      attribute: str, value: Any) -> dict:
        self._ensure_connected()
        obj = self._resolve_object(object_type, object_id)
        old = self._safe_get(obj, f"AttValue('{attribute}')", None)
        obj.SetAttValue(attribute, value)
        return {"status": "updated", "object": f"{object_type}#{object_id}",
                "attribute": attribute, "old_value": old, "new_value": value}

    # ── Visualization ──────────────────────────────────────────

    def get_screenshot(self, width: int = 800, height: int = 600) -> bytes:
        self._ensure_connected()
        # Vissim COM doesn't have a direct Screenshot() method.
        # In practice, you'd use the Graphics.NetworkWindow or
        # a pyautogui/PIL approach to capture the Vissim window.
        import io
        try:
            from PIL import Image
            import pyautogui
        except ImportError:
            raise ImportError("Pillow and pyautogui required for screenshots. "
                              "Install: pip install Pillow pyautogui")

        window = pyautogui.getWindowsWithTitle("Vissim")[0]
        screenshot = pyautogui.screenshot(region=(
            window.left, window.top, window.width, window.height
        ))
        buf = io.BytesIO()
        screenshot.save(buf, format="PNG")
        return buf.getvalue()

    def zoom_to(self, target_type: str, target_id: int) -> dict:
        self._ensure_connected()
        obj = self._resolve_object(target_type, target_id)
        nw = self._vissim.Graphics.CurrentNetworkWindow
        nw.SetAttValue("CenterX", obj.AttValue("X") if hasattr(obj, 'AttValue') else 0)
        nw.SetAttValue("CenterY", obj.AttValue("Y") if hasattr(obj, 'AttValue') else 0)
        return {
            "status": "zoomed",
            "target": f"{target_type}#{target_id}",
            "message": f"Zoomed to {target_type} #{target_id}",
        }

    # ── Internal Helpers ───────────────────────────────────────

    def _ensure_connected(self):
        if not self._connected or self._vissim is None:
            raise RuntimeError("Not connected to Vissim. Call connect() first.")

    def _safe_get(self, obj, attr_or_call, default=None):
        """Safely get a value from a COM object, returning default on failure."""
        try:
            if callable(attr_or_call):
                return attr_or_call()
            return getattr(obj, attr_or_call)
        except Exception:
            return default

    def _resolve_object(self, object_type: str, object_id: int):
        """Resolve a Vissim COM object by type and 1-based index."""
        net = self._vissim.Net
        type_map = {
            "link": net.Links,
            "node": net.Nodes,
            "signalcontroller": net.SignalControllers,
            "signalgroup": net.SignalControllers,
            "vehicleinput": net.VehicleInputs,
            "vehicleroute": net.VehicleRoutes,
            "datacollection": self._vissim.Evaluation.DataCollections,
        }
        key = object_type.lower().replace("_", "").replace(" ", "")
        collection = type_map.get(key)
        if not collection:
            raise ValueError(f"Unknown object type: {object_type}")
        return collection.Item(object_id)
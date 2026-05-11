"""Tests for the Mock Backend — runs without Vissim on any platform."""

import pytest
from vissim_mcp.backend.mock_backend import MockBackend
from vissim_mcp.backend.base import VissimBackend


@pytest.fixture
def backend():
    """Create a connected mock backend with demo network loaded."""
    b = MockBackend()
    b.connect()
    b.load_net("demo.inpx")
    return b


class TestMockBackendLifecycle:
    """Test connection and project lifecycle."""

    def test_connect_disconnect(self):
        b = MockBackend()
        assert not b.is_connected()

        result = b.connect()
        assert result["status"] == "connected"
        assert result["backend"] == "mock"
        assert b.is_connected()

        result = b.disconnect()
        assert result["status"] == "disconnected"
        assert not b.is_connected()

    def test_connect_twice_is_idempotent(self, backend):
        result = backend.connect()
        assert result["status"] == "already_connected"

    def test_load_net_populates_data(self, backend):
        info = backend.get_project_info()
        assert info["loaded"]
        assert info["num_links"] == 8
        assert info["num_nodes"] == 4
        assert info["num_signals"] == 3
        assert info["num_vehicle_inputs"] == 4
        assert info["num_vehicle_routes"] == 5

    def test_save_net(self, backend):
        result = backend.save_net("output.inpx")
        assert result["status"] == "saved"


class TestNetworkQuery:
    """Test querying the demo network."""

    def test_get_links(self, backend):
        links = backend.get_links()
        assert len(links) == 8
        assert links[0]["name"] == "Main St West"
        assert links[0]["num_lanes"] == 3
        assert links[0]["link_type"] == "arterial"

    def test_get_links_pagination(self, backend):
        page1 = backend.get_links(limit=3, offset=0)
        page2 = backend.get_links(limit=3, offset=3)
        assert len(page1) == 3
        assert len(page2) == 3
        assert page1[0]["id"] != page2[0]["id"]

    def test_get_nodes(self, backend):
        nodes = backend.get_nodes()
        assert len(nodes) == 4
        assert nodes[0]["node_type"] == "signalized"
        assert nodes[3]["node_type"] == "priority"

    def test_get_signal_controllers(self, backend):
        signals = backend.get_signal_controllers()
        assert len(signals) == 3
        assert signals[0]["cycle_time_s"] == 90.0
        assert signals[2]["signal_type"] == "actuated"

    def test_get_vehicle_inputs(self, backend):
        inputs = backend.get_vehicle_inputs()
        assert len(inputs) == 4
        assert inputs[0]["volume_veh_h"] == 800.0

    def test_get_vehicle_routes(self, backend):
        routes = backend.get_vehicle_routes()
        assert len(routes) == 5
        assert routes[0]["relative_flow"] == 0.6

    def test_get_att_value(self, backend):
        length = backend.get_att_value("link", 1, "length")
        assert length == 300.0

        speed = backend.get_att_value("link", 4, "speed_limit")
        assert speed == 40.0

    def test_get_att_value_invalid(self, backend):
        with pytest.raises(ValueError):
            backend.get_att_value("link", 999, "length")


class TestSimulationControl:
    """Test simulation stepping and control."""

    def test_run_single_step(self, backend):
        state = backend.get_simulation_state()
        assert state["simulation_second"] == 0

        result = backend.run_single_step(steps=10)
        assert result["steps_executed"] == 10
        assert result["simulation_second"] == 10

        state = backend.get_simulation_state()
        assert state["simulation_second"] == 10

    def test_run_continuous_and_stop(self, backend):
        result = backend.run_continuous()
        assert result["status"] == "started"

        state = backend.get_simulation_state()
        assert state["is_running"]

        result = backend.stop_simulation()
        assert result["status"] == "stopped"

    def test_set_simulation_period(self, backend):
        result = backend.set_simulation_period(0, 7200)
        assert result["period_start_s"] == 0
        assert result["period_end_s"] == 7200

        state = backend.get_simulation_state()
        assert state["period_end_s"] == 7200

    def test_simulation_stops_at_period_end(self, backend):
        backend.set_simulation_period(0, 5)
        result = backend.run_single_step(steps=100)
        assert result["simulation_second"] <= 5
        # Running again should indicate finished
        result2 = backend.run_single_step(steps=1)
        assert result2["status"] == "finished"


class TestEvaluation:
    """Test evaluation data extraction."""

    def test_get_travel_times(self, backend):
        backend.run_single_step(steps=60)
        results = backend.get_travel_times(1)
        assert len(results) == 1
        assert results[0]["unit"] == "s"
        assert results[0]["value"] > 0

    def test_get_delays(self, backend):
        backend.run_single_step(steps=60)
        results = backend.get_delays(1)
        assert len(results) == 1
        assert results[0]["unit"] == "s/veh"

    def test_get_queue_lengths(self, backend):
        results = backend.get_queue_lengths(1)
        assert len(results) == 1
        assert results[0]["unit"] == "m"
        assert results[0]["value"] >= 0

    def test_get_network_performance(self, backend):
        backend.run_single_step(steps=100)
        results = backend.get_network_performance()
        assert len(results) == 4

        names = {r["name"] for r in results}
        assert "Total Vehicles" in names
        assert "Average Speed" in names
        assert "Total Delay" in names
        assert "Total Distance" in names

    def test_get_data_collection(self, backend):
        results = backend.get_data_collection(1)
        assert len(results) == 1
        assert results[0]["unit"] == "veh/h"

    def test_evaluation_changes_over_time(self, backend):
        """Run simulation and verify results change."""
        r1 = backend.get_network_performance()
        backend.run_single_step(steps=500)
        r2 = backend.get_network_performance()
        # Total distance should increase
        d1 = next(r for r in r1 if r["name"] == "Total Distance")["value"]
        d2 = next(r for r in r2 if r["name"] == "Total Distance")["value"]
        assert d2 > d1


class TestNetworkEditing:
    """Test attribute modification."""

    def test_set_att_value(self, backend):
        result = backend.set_att_value("link", 1, "speed_limit", 70.0)
        assert result["status"] == "updated"
        assert result["old_value"] == 60.0
        assert result["new_value"] == 70.0

        # Verify the change persisted
        new_val = backend.get_att_value("link", 1, "speed_limit")
        assert new_val == 70.0


class TestVisualization:
    """Test screenshot and zoom."""

    def test_get_screenshot(self, backend):
        img = backend.get_screenshot(width=400, height=300)
        assert isinstance(img, bytes)
        assert len(img) > 0
        # Should be SVG (mock backend)
        assert img.startswith(b'<?xml') or img.startswith(b'<svg')

    def test_zoom_to_link(self, backend):
        result = backend.zoom_to("link", 3)
        assert result["status"] == "zoomed"
        assert result["target_id"] == 3

    def test_zoom_to_invalid(self, backend):
        with pytest.raises(ValueError):
            backend.zoom_to("link", 999)


class TestBackendInterface:
    """Verify MockBackend fulfills the abstract interface."""

    def test_is_subclass(self):
        assert issubclass(MockBackend, VissimBackend)

    def test_all_abstract_methods_implemented(self):
        """Ensure no abstract methods are left unimplemented."""
        b = MockBackend()
        b.connect()
        b.load_net("test.inpx")

        # Call every method to verify none are abstract
        methods_to_test = [
            ("connect", [True]),
            ("disconnect", []),
            ("is_connected", []),
            ("load_net", ["test.inpx"]),
            ("load_layout", ["test.layx"]),
            ("save_net", []),
            ("get_project_info", []),
            ("get_links", []),
            ("get_nodes", []),
            ("get_signal_controllers", []),
            ("get_vehicle_inputs", []),
            ("get_vehicle_routes", []),
            ("get_att_value", ["link", 1, "length"]),
            ("run_single_step", [1]),
            ("run_continuous", []),
            ("stop_simulation", []),
            ("get_simulation_state", []),
            ("set_simulation_period", [0, 3600]),
            ("get_travel_times", [1]),
            ("get_delays", [1]),
            ("get_queue_lengths", [1]),
            ("get_network_performance", []),
            ("get_data_collection", [1]),
            ("set_att_value", ["link", 1, "speed_limit", 50.0]),
            ("get_screenshot", []),
            ("zoom_to", ["link", 1]),
        ]

        for method_name, args in methods_to_test:
            method = getattr(b, method_name)
            result = method(*args)
            assert result is not None, f"Method {method_name} returned None"

"""Simulation control tools: run, stop, step, configure."""


def register_simulation_tools(mcp, get_backend):
    """Register all simulation control MCP tools."""

    @mcp.tool()
    def vissim_run_single_step(steps: int = 1) -> dict:
        """Advance the simulation by a number of single steps.

        Useful for debugging or when you need precise control over
        simulation progression.

        Args:
            steps: Number of simulation steps to run (default 1).
        """
        backend = get_backend()
        return backend.run_single_step(steps=steps)

    @mcp.tool()
    def vissim_run_continuous() -> dict:
        """Start continuous simulation. Stops at the end of the simulation period."""
        backend = get_backend()
        return backend.run_continuous()

    @mcp.tool()
    def vissim_stop() -> dict:
        """Stop the currently running simulation."""
        backend = get_backend()
        return backend.stop_simulation()

    @mcp.tool()
    def vissim_get_simulation_state() -> dict:
        """Get the current simulation state: time, running status, speed."""
        backend = get_backend()
        return backend.get_simulation_state()

    @mcp.tool()
    def vissim_set_simulation_period(start: int, end: int) -> dict:
        """Set the simulation period (start and end time in simulation seconds).

        Args:
            start: Start time in simulation seconds (e.g., 0).
            end: End time in simulation seconds (e.g., 3600 for 1 hour).
        """
        backend = get_backend()
        return backend.set_simulation_period(start, end)

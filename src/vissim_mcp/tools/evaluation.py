"""Evaluation and data extraction tools: travel times, delays, queues, etc."""

from typing import Optional


def register_evaluation_tools(mcp, get_backend):
    """Register all evaluation/data extraction MCP tools."""

    @mcp.tool()
    def vissim_get_travel_times(measurement_id: int,
                                 from_time: Optional[int] = None,
                                 to_time: Optional[int] = None) -> list[dict]:
        """Get vehicle travel time measurement results.

        Args:
            measurement_id: Travel time measurement ID (1-based index).
            from_time: Start time filter (simulation seconds). None = from start.
            to_time: End time filter (simulation seconds). None = to current.
        """
        backend = get_backend()
        return backend.get_travel_times(measurement_id, from_time, to_time)

    @mcp.tool()
    def vissim_get_delays(measurement_id: int,
                           from_time: Optional[int] = None,
                           to_time: Optional[int] = None) -> list[dict]:
        """Get vehicle delay measurement results (seconds per vehicle).

        Args:
            measurement_id: Delay measurement ID.
            from_time: Start time filter. None = from start.
            to_time: End time filter. None = to current.
        """
        backend = get_backend()
        return backend.get_delays(measurement_id, from_time, to_time)

    @mcp.tool()
    def vissim_get_queue_lengths(counter_id: int,
                                  from_time: Optional[int] = None,
                                  to_time: Optional[int] = None) -> list[dict]:
        """Get queue length counter results (meters).

        Args:
            counter_id: Queue counter ID.
            from_time: Start time filter. None = from start.
            to_time: End time filter. None = to current.
        """
        backend = get_backend()
        return backend.get_queue_lengths(counter_id, from_time, to_time)

    @mcp.tool()
    def vissim_get_network_performance() -> list[dict]:
        """Get overall vehicle network performance statistics.

        Returns: total vehicles, average speed, total delay, total distance.
        """
        backend = get_backend()
        return backend.get_network_performance()

    @mcp.tool()
    def vissim_get_data_collection(collection_id: int) -> list[dict]:
        """Get data collection point measurement results.

        Args:
            collection_id: Data collection point ID.
        """
        backend = get_backend()
        return backend.get_data_collection(collection_id)

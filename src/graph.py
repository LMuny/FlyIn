"""Graph of the hubs and how they connect."""

from src.models import Connection, Hub, ZoneType
from collections import deque as dq


class Graph:
    """Map of the hubs, with the neighbors of each hub.

    Attributes:
        neighbors: For each hub name, its neighboring hubs and the
            connection that leads to each of them.
        hubs: Hubs of the map, stored by name.
    """

    def __init__(self,
                 hubs: dict[str, Hub],
                 connections: list[Connection]
                 ) -> None:
        """Build the list of neighbors of every hub.

        Args:
            hubs: Hubs of the map, stored by name.
            connections: Connections of the map. Each one is added in
                both directions.
        """
        self.neighbors: dict[str, list[tuple[Hub, Connection]]] = {}
        self.hubs = hubs

        for hub in hubs:
            self.neighbors[hub] = []

        for link in connections:
            self.neighbors[link.hub_a.name].append((link.hub_b, link))
            self.neighbors[link.hub_b.name].append((link.hub_a, link))

    def get_link(self, a: str, b: str) -> Connection | None:
        """Find the connection between two hubs.

        Args:
            a: Name of the first hub.
            b: Name of the second hub.

        Returns:
            The connection between the two hubs, or None if they are not
            connected.
        """
        for neighbor, link in self.neighbors[a]:
            if neighbor.name == b:
                return link
        return None

    def has_path(self, start: Hub, end: Hub) -> bool:
        """Check if the end can be reached from the start.

        Uses a breadth-first search that never enters blocked zones.

        Args:
            start: Hub where the search begins.
            end: Hub to reach.

        Returns:
            True if a path exists, False otherwise.
        """
        queue = dq([start])
        vzted = {start.name}

        while queue:
            hub: Hub = queue.popleft()
            if hub.name == end.name:
                return True
            for neighbor, _ in self.neighbors[hub.name]:
                if neighbor.zone == ZoneType.BLOCKED or neighbor.name in vzted:
                    continue
                vzted.add(neighbor.name)
                queue.append(neighbor)
        return False

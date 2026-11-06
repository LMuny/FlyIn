""" Graph of the hubs and how they connect."""

from src.models import Connection, Hub, ZoneType
from collections import deque as dq


class Graph:
    """..."""
    def __init__(self,
                 hubs: dict[str, Hub],
                 connections: list[Connection]
                 ) -> None:
        self.neighbors: dict[str, list[tuple[Hub, Connection]]] = {}

        for hub in hubs:
            self.neighbors[hub] = []

        for link in connections:
            self.neighbors[link.hub_a.name].append((link.hub_b, link))
            self.neighbors[link.hub_b.name].append((link.hub_a, link))

    def has_path(self, start: Hub, end: Hub) -> bool:
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

"""Returns the best routes found"""

from heapq import heappop, heappush

from src.models import Hub, ZoneType
from src.graph import Graph


class Scheduler:
    def __init__(self, graph: Graph) -> None:
        self.graph = graph
        self.hub_bookings: dict[tuple[str, int], int] = {}
        self.link_bookings: dict[tuple[str, int], int] = {}

    def best_route(self, start: Hub, end: Hub) -> tuple[list[str], int]:
        heap = [(0, 0, start.name, [start.name])]
        vzted: set[str] = set()

        while heap:
            turns, priority, name, path = heappop(heap)
            if name in vzted:
                continue
            vzted.add(name)
            if name == end.name:
                return (path, turns)
            for neighbor, _ in self.graph.neighbors[name]:
                if neighbor.zone == ZoneType.BLOCKED or neighbor.name in vzted:
                    continue
                new_turns = turns + neighbor.zone.cost
                new_priority = priority
                if neighbor.zone == ZoneType.PRIORITY:
                    new_priority -= 1
                new_path = path + [neighbor.name]
                heappush(
                    heap,
                    (
                        new_turns,
                        new_priority,
                        neighbor.name,
                        new_path
                    )
                )

        return ([], 0)

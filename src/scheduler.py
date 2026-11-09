"""Scheduler that plans the route of every drone, turn by turn."""

from heapq import heappop, heappush

from src.models import Hub, Connection, ZoneType
from src.graph import Graph


class Scheduler:
    """Plans the drones one by one, booking the space each one uses.

    A route is a list with one position per turn: index 0 is the start,
    and each next index is where the drone is on that turn. A position is
    a hub name, or a connection name while flying to a restricted zone.

    Attributes:
        graph: Graph of the map.
        hub_bookings: Number of drones booked per (hub name, turn).
        link_bookings: Number of drones booked per (connection name, turn).
    """

    def __init__(self, graph: Graph) -> None:
        """Set up a scheduler with no bookings.

        Args:
            graph: Graph of the map to plan on.
        """
        self.graph = graph
        self.hub_bookings: dict[tuple[str, int], int] = {}
        self.link_bookings: dict[tuple[str, int], int] = {}

    def _link_name(self, link: Connection) -> str:
        """Get the name of a connection, e.g. "hub_a-hub_b".

        Args:
            link: The connection.

        Returns:
            The names of its two hubs, joined by a dash.
        """
        return f"{link.hub_a.name}-{link.hub_b.name}"

    def _hub_has_room(self, hub: Hub, turn: int) -> bool:
        """Check if one more drone can be in a hub on a given turn.

        Args:
            hub: The hub to check.
            turn: The turn to check.

        Returns:
            True if the hub is unlimited or below max_drones on that turn.
        """
        if hub.unlimited:
            return True
        count = self.hub_bookings.get((hub.name, turn), 0)
        return count < hub.max_drones

    def _link_has_room(self, link: Connection, turn: int) -> bool:
        """Check if one more drone can cross a connection on a given turn.

        Args:
            link: The connection to check.
            turn: The turn to check.

        Returns:
            True if the connection is below max_link_capacity on that turn.
        """
        name = self._link_name(link)
        count = self.link_bookings.get((name, turn), 0)
        return count < link.max_link_capacity

    def _book(self, path: list[str]) -> None:
        """Book every hub and connection a route uses, turn by turn.

        A hub is booked on every turn the drone is in it, including while
        waiting. A connection is booked on the turn the drone crosses it.
        A connection to a restricted zone is booked only on the turn the
        drone is on it, and is free again on the turn it arrives.

        Args:
            path: The route to book, with one position per turn.
        """
        for turn, pos in enumerate(path):
            if turn == 0:
                continue
            prev = path[turn - 1]

            if pos in self.graph.hubs:
                key = (pos, turn)
                self.hub_bookings[key] = self.hub_bookings.get(key, 0) + 1

                if prev in self.graph.hubs and prev != pos:
                    link = self.graph.get_link(prev, pos)
                    if link is not None:
                        link_key = (self._link_name(link), turn)
                        self.link_bookings[link_key] = (
                            self.link_bookings.get(link_key, 0) + 1)
            else:
                link_key = (pos, turn)
                self.link_bookings[link_key] = (
                    self.link_bookings.get(link_key, 0) + 1)

    def best_route(self, start: Hub, end: Hub) -> tuple[list[str], int]:
        """Find the fastest route for one drone, given the current bookings.

        Uses Dijkstra's algorithm on (hub, turn) states. At each turn the
        drone can wait or move to a neighbor that has room. On equal turns,
        the route through more priority zones is preferred.

        Args:
            start: Hub where the drone starts.
            end: Hub the drone must reach.

        Returns:
            The route with one position per turn, and its number of turns.
            ([], 0) if no route exists.
        """
        heap = [(0, 0, start.name, [start.name])]
        visited: set[tuple[str, int]] = set()

        while heap:
            turns, priority, name, path = heappop(heap)
            if (name, turns) in visited:
                continue
            else:
                visited.add((name, turns))
            if name == end.name:
                return (path, turns)
            current = self.graph.hubs[name]
            if self._hub_has_room(current, turns + 1):
                heappush(heap, (turns + 1, priority, name, path + [name]))

            for neighbor, link in self.graph.neighbors[name]:
                arrival = turns + neighbor.zone.cost
                if neighbor.zone == ZoneType.BLOCKED:
                    continue
                if (not self._link_has_room(link, turns + 1)
                        or not self._hub_has_room(neighbor, arrival)):
                    continue
                new_priority = priority
                if neighbor.zone == ZoneType.PRIORITY:
                    new_priority -= 1
                if neighbor.zone == ZoneType.RESTRICTED:
                    link_name = self._link_name(link)
                    new_path = path + [link_name, neighbor.name]
                else:
                    new_path = path + [neighbor.name]

                heappush(heap, (
                    arrival, new_priority, neighbor.name, new_path
                    ))

        return ([], 0)

    def plan_all(
            self,
            start: Hub,
            end: Hub,
            nb_drones: int
            ) -> list[list[str]]:
        """Plan the route of every drone, one after the other.

        Each route is booked before the next drone is planned, so later
        drones avoid the space already taken or wait for it.

        Args:
            start: Hub where all the drones start.
            end: Hub all the drones must reach.
            nb_drones: Number of drones to plan.

        Returns:
            The route of each drone, in drone order.
        """
        routes: list[list[str]] = []
        for _ in range(nb_drones):
            path, _turns = self.best_route(start, end)
            self._book(path)
            routes.append(path)
        return routes

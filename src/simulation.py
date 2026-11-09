"""Simulation that turns the planned routes into turn-by-turn output."""


class Simulation:
    """Turns the planned routes into the output lines, one per turn.

    Attributes:
        routes: The route of each drone, in drone order. Each route has
            one position per turn, starting with the start hub at index 0.
    """

    def __init__(self, routes: list[list[str]]) -> None:
        """Store the routes to simulate.

        Args:
            routes: The route of each drone, as returned by the scheduler.
        """
        self.routes = routes

    def turn_count(self) -> int:
        """Get the number of turns needed to deliver every drone.

        Returns:
            The length of the longest route, without its starting position.
        """
        return max(len(route) - 1 for route in self.routes)

    def turn_lines(self) -> list[str]:
        """Build the output line of every turn.

        Each line lists the drones that move on that turn, as
        "D<ID>-<zone>", or "D<ID>-<connection>" while flying to a
        restricted zone. Drones that wait or are already delivered are
        left out.

        Returns:
            One line per turn, from turn 1 to the last turn.
        """
        result: list[str] = []

        for turn in range(1, self.turn_count() + 1):
            moves: list[str] = []
            for drone_id, route in enumerate(self.routes, start=1):
                if turn < len(route) and route[turn] != route[turn - 1]:
                    moves.append(f"D{drone_id}-{route[turn]}")
            result.append(" ".join(moves))
        return result

"""Entry point of the program: reads a map file given on the command line."""

from sys import argv, exit

from src.parser import MapParser
from src.graph import Graph
from src.scheduler import Scheduler
from src.simulation import Simulation

DEBUG: bool = False


def main() -> None:
    """Plan the drones on the map given as an argument and print each turn.

    Raises:
        SystemExit: If the arguments or the map file are invalid, or if
            the end can't be reached from the start.
    """
    if len(argv) != 2:
        print("usage: 'uv run python3 -m src <map_file_path>'")
        exit(1)

    parser = MapParser(argv[1])
    parser.parse()
    if parser.start_hub is None or parser.end_hub is None:
        exit(1)
    graph = Graph(parser.hubs, parser.connections)
    if not graph.has_path(parser.start_hub, parser.end_hub):
        print("[ERROR]: no path from start to end")
        exit(1)

    if DEBUG:
        print("\n--------------[Element Count]-------------\n")
        print(f"Drones      : {parser.nb_drones}")
        print(f"Hubs        : {len(parser.hubs)}")
        print(f"Connections : {len(parser.connections)}")

        print(f"Start       : {parser.start_hub.name}")
        print(f"End         : {parser.end_hub.name}")
        print("\n-------------[Hub Links List]-------------\n")
        for name, links in graph.neighbors.items():
            print(name, [hub.name for hub, _ in links])
        print("\n---------------[Scheduler]----------------\n")
        scheduler = Scheduler(graph)
        routes = scheduler.plan_all(
            parser.start_hub,
            parser.end_hub,
            parser.nb_drones)
        simulation = Simulation(routes)
        for line in simulation.turn_lines():
            print(line)
        print("\n------------------[END]-------------------\n")

    else:
        scheduler = Scheduler(graph)
        routes = scheduler.plan_all(
            parser.start_hub,
            parser.end_hub,
            parser.nb_drones)
        simulation = Simulation(routes)
        for line in simulation.turn_lines():
            print(line)


if __name__ == "__main__":
    main()

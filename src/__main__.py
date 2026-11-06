"""Entry point of the program: reads a map file given on the command line."""

from sys import argv, exit
from src.parser import MapParser
from src.graph import Graph
from src.scheduler import Scheduler


def main() -> None:
    """Parse the map file given as an argument and print what it contains.

    Raises:
        SystemExit: If the arguments or the map file are invalid.
    """
    if len(argv) != 2:
        print("usage: 'uv run python3 -m src <map_file_path>'")
        exit(1)

    parser = MapParser(argv[1])
    parser.parse()
    print("\n--------------[Element Count]-------------\n")
    print(f"Drones      : {parser.nb_drones}")
    print(f"Hubs        : {len(parser.hubs)}")
    print(f"Connections : {len(parser.connections)}")
    if parser.start_hub is None or parser.end_hub is None:
        exit(1)
    print(f"Start       : {parser.start_hub.name}")
    print(f"End         : {parser.end_hub.name}")
    print("\n-------------[Hub Links List]-------------\n")
    graph = Graph(parser.hubs, parser.connections)
    if not graph.has_path(parser.start_hub, parser.end_hub):
        print("[ERROR]: no path from start to end")
        exit(1)
    else:
        print("[PATH FOUND]\n")
    for name, links in graph.neighbors.items():
        print(name, [hub.name for hub, _ in links])
    print("\n---------------[Scheduler]----------------\n")
    scheduler = Scheduler(graph)
    print(scheduler.best_route(parser.start_hub, parser.end_hub))
    print("\n------------------[END]-------------------\n")


if __name__ == "__main__":
    main()

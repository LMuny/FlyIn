"""Entry point of the program: reads a map file given on the command line."""

from sys import argv, exit, stdin, stdout

from src.parser import MapParser
from src.graph import Graph
from src.scheduler import Scheduler
from src.simulation import Simulation
from src.display import Display
from src.radar import Radar

DEBUG: bool = False


def main() -> None:
    """Plan the drones on the map given as an argument and print each turn.

    With the --visual option, the turns are then replayed on a radar.

    Raises:
        SystemExit: If the arguments or the map file are invalid, or if
            the end can't be reached from the start.
    """
    args = argv[1:]
    visual = "--visual" in args
    if visual:
        args.remove("--visual")
    if len(args) != 1:
        print("usage: 'uv run python3 -m src <map_file_path> [--visual]'")
        exit(1)

    parser = MapParser(args[0])
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
        print("\n---------------[DISPLAY]------------------\n")
        display = Display(parser.hubs)
        for line in simulation.turn_lines():
            if stdout.isatty():
                print(display.color_line(line))
            else:
                print(line)
        print("\n------------------[END]-------------------\n")

    else:
        scheduler = Scheduler(graph)
        routes = scheduler.plan_all(
            parser.start_hub,
            parser.end_hub,
            parser.nb_drones)
        simulation = Simulation(routes)
        display = Display(parser.hubs)
        for line in simulation.turn_lines():
            if stdout.isatty():
                print(display.color_line(line))
            else:
                print(line)

    if visual:
        if stdin.isatty():
            input("\nPress Enter to start the radar...")
        title = args[0].rsplit('/', 1)[-1].removesuffix('.txt')
        Radar(parser.hubs, parser.connections, routes, title).play()


if __name__ == "__main__":
    main()

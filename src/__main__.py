"""Entry point of the program: reads a map file given on the command line."""

import sys
from src.parser import MapParser


def main() -> None:
    """Parse the map file given as an argument and print what it contains.

    Raises:
        SystemExit: If the arguments or the map file are invalid.
    """
    if len(sys.argv) != 2:
        print("usage: 'uv run python3 -m src <map_file_path>'")
        sys.exit(1)

    parser = MapParser(sys.argv[1])
    parser.parse()
    print(f"Drones      : {parser.nb_drones}")
    print(f"Hubs        : {len(parser.hubs)}")
    print(f"Connections : {len(parser.connections)}")
    if parser.start_hub is None or parser.end_hub is None:
        sys.exit(1)
    print(f"Start       : {parser.start_hub.name}")
    print(f"End         : {parser.end_hub.name}")


if __name__ == "__main__":
    main()

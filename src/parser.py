"""Parser that reads a map file and builds its hubs and connections."""

import sys
from pydantic import ValidationError
from src.models import Hub, Connection


class MapParser:
    """Reads a map file and stores what it defines.

    Any parsing error prints a message and stops the program.

    Attributes:
        filepath: Path of the map file.
        nb_drones: Number of drones defined by the map.
        hubs: Hubs of the map, stored by name.
        connections: Connections of the map.
        connection_keys: Sorted name pairs, used to find duplicates.
        start_hub: Hub where the drones start, or None until it is parsed.
        end_hub: Hub the drones must reach, or None until it is parsed.
    """

    def __init__(self, filepath: str) -> None:
        """Set up an empty parser.

        Args:
            filepath: Path of the map file to read.
        """
        self.filepath = filepath
        self.nb_drones: int = 0
        self.hubs: dict[str, Hub] = {}
        self.connections: list[Connection] = []
        self.connection_keys: set[tuple[str, str]] = set()
        self.start_hub: Hub | None = None
        self.end_hub: Hub | None = None

    def _print_error(self, message: str, line_no: int | None = None) -> None:
        """Print an error message in the terminal.

        Args:
            message: Cause of the error.
            line_no: Line of the map file, or None if no line applies.
        """
        RED = '\033[1;38;5;88m'
        RESET = '\033[0m'
        if line_no is not None:
            message = f"line {line_no}: {message}"
        print(f"{RED}[ERROR]{RESET}: {message}")

    def _load_txt(self) -> str:
        """Read the whole map file.

        Returns:
            The content of the file.

        Raises:
            SystemExit: If the file can't be read.
        """
        try:
            with open(self.filepath, 'r') as f:
                return f.read()
        except OSError:
            self._print_error("Incorrect file path")
            sys.exit(1)

    def _extract_lines(self) -> list[tuple[int, str]]:
        """Get the lines to parse, without comments and blank lines.

        Returns:
            A list of (line number, stripped line) pairs.
        """
        clean_lines: list[tuple[int, str]] = []
        raw_text = self._load_txt()
        all_lines = raw_text.splitlines()
        for line_no, line in enumerate(all_lines, start=1):
            line = line.strip()
            if line.startswith('#') or line == "":
                continue
            clean_lines.append((line_no, line))
        return clean_lines

    def _parse_nb_drones(self, line_no: int, line: str) -> None:
        """Parse the nb_drones line and store its value.

        Args:
            line_no: Line number, used in error messages.
            line: The full line, e.g. "nb_drones: 5".

        Raises:
            SystemExit: If the line isn't a positive nb_drones value.
        """
        name, _sep, value = line.partition(':')
        if name.strip() != "nb_drones":
            self._print_error("First line should be 'nb_drones'", line_no)
            sys.exit(1)
        try:
            nb_drones = int(value)
        except ValueError:
            self._print_error("nb_drones must be an integer", line_no)
            sys.exit(1)
        if nb_drones <= 0:
            self._print_error(
                "nb_drones value should be greater than 0", line_no)
            sys.exit(1)
        self.nb_drones = nb_drones

    def _parse_hub(self, line_no: int, prefix: str, rest: str) -> None:
        """Parse a hub line and store the new hub.

        Args:
            line_no: Line number, used in error messages.
            prefix: Type of the line: "start_hub", "end_hub" or "hub".
            rest: Text after the prefix, e.g. " roof1 3 4 [zone=restricted]".

        Raises:
            SystemExit: If the line is invalid, or defines a second start or
                end hub.
        """
        split_rest = rest.split(maxsplit=3)
        if len(split_rest) < 3:
            self._print_error("expected <name> <x> <y> [metadata]", line_no)
            sys.exit(1)

        unlimited = prefix != "hub"
        metadata: dict[str, str] = {}
        if len(split_rest) == 4:
            ignored = {"max_drones"} if unlimited else set()
            metadata = self._parse_metadata(
                line_no,
                split_rest[3],
                {"zone", "color", "max_drones"},
                ignored
            )

        name = split_rest[0]
        if "-" in name:
            self._print_error("name must not contain '-'", line_no)
            sys.exit(1)
        if name in self.hubs:
            self._print_error(f"duplicate hub name '{name}'", line_no)
            sys.exit(1)
        try:
            x = int(split_rest[1])
            y = int(split_rest[2])
        except ValueError:
            self._print_error("x and y must be integers", line_no)
            sys.exit(1)

        try:
            new_hub = Hub.model_validate({
                "name": name,
                "x": x,
                "y": y,
                "unlimited": unlimited,
                **metadata,
            })
        except ValidationError as e:
            self._print_error(f"invalid hub: {e.errors()[0]['msg']}", line_no)
            sys.exit(1)
        if prefix == "start_hub":
            if self.start_hub:
                self._print_error("must not have two starting hub", line_no)
                sys.exit(1)
            self.start_hub = new_hub
        elif prefix == "end_hub":
            if self.end_hub:
                self._print_error("must not have two end hub", line_no)
                sys.exit(1)
            self.end_hub = new_hub
        self.hubs[new_hub.name] = new_hub

    def _parse_connection(self, line_no: int, rest: str) -> None:
        """Parse a connection line and store the new connection.

        Args:
            line_no: Line number, used in error messages.
            rest: Text after the prefix, e.g. " a-b [max_link_capacity=2]".

        Raises:
            SystemExit: If the line is invalid, links an unknown hub, links
                a hub to itself, or repeats a connection in either direction.
        """
        split_rest = rest.split(maxsplit=1)
        if len(split_rest) < 1:
            self._print_error("expected <hub_a-hub-b> [metadata]", line_no)
            sys.exit(1)
        nodes = split_rest[0].split("-", maxsplit=1)
        if len(nodes) < 2:
            self._print_error("expected <hub_a-hub-b>", line_no)
            sys.exit(1)
        for name in nodes:
            if name not in self.hubs:
                self._print_error(f"hub: {name}, doesn't exist...", line_no)
                sys.exit(1)
        key = (min(nodes), max(nodes))
        if key in self.connection_keys:
            self._print_error(
                f"duplicate connection '{nodes[0]}-{nodes[1]}'", line_no)
            sys.exit(1)
        self.connection_keys.add(key)
        if nodes[0] == nodes[1]:
            self._print_error(
                f"hub '{nodes[0]}' can't connect to itself", line_no)
            sys.exit(1)
        metadata: dict[str, str] = {}
        if len(split_rest) == 2:
            metadata = self._parse_metadata(
                line_no, split_rest[1], {"max_link_capacity"}, set())
        try:
            new_connection = Connection.model_validate({
                "hub_a": self.hubs[nodes[0]],
                "hub_b": self.hubs[nodes[1]],
                **metadata,
            })
        except ValidationError as e:
            self._print_error(
                f"invalid connection: {e.errors()[0]['msg']}", line_no)
            sys.exit(1)
        self.connections.append(new_connection)

    def _parse_metadata(self, line_no: int, text: str, allowed: set[str],
                        ignored: set[str]) -> dict[str, str]:
        """Parse a metadata block into a dict.

        Args:
            line_no: Line number, used in error messages.
            text: The block with its brackets, e.g. "[zone=normal color=red]".
            allowed: Tags accepted on this type of line.
            ignored: Tags to skip, whatever their value is.

        Returns:
            The tags and their values as strings, without the ignored tags.

        Raises:
            SystemExit: If the block, a tag or a value is invalid.
        """
        if not (text.startswith("[") and text.endswith("]")):
            self._print_error("metadata must be inside [...]", line_no)
            sys.exit(1)
        tags = text[1:-1].split()
        metadata: dict[str, str] = {}
        for tag in tags:
            key, _sep, v = tag.partition('=')
            if not key or not v:
                self._print_error(f"'{tag}' should be key=value", line_no)
                sys.exit(1)
            if key in ignored:
                continue
            if key not in allowed:
                self._print_error(f"unallowed metadata tag '{key}'", line_no)
                sys.exit(1)
            if key in metadata:
                self._print_error(f"tag '{key}' is given twice", line_no)
                sys.exit(1)

            if key in ("max_drones", "max_link_capacity"):
                try:
                    value = int(v)
                except ValueError:
                    self._print_error(
                        f"the value of {key} must be an integer", line_no)
                    sys.exit(1)
                if value <= 0:
                    self._print_error(
                        f"the value of {key} must be positive", line_no)
                    sys.exit(1)

            if key == "zone":
                zone_type = [
                    'restricted',
                    'priority',
                    'blocked',
                    'normal'
                ]
                if v not in zone_type:
                    self._print_error(
                        f"the value of {key} must be an allowed type", line_no)
                    sys.exit(1)

            metadata[key] = v
        return metadata

    def parse(self) -> None:
        """Parse the whole map file and store its content.

        Raises:
            SystemExit: If the file is empty, a line is invalid, or the start
                or end hub is missing.
        """
        lines = self._extract_lines()
        if not lines:
            self._print_error("file is empty")
            sys.exit(1)

        self._parse_nb_drones(*lines[0])

        for line_no, line in lines[1:]:
            prefix, _sep, rest = line.partition(':')
            prefix = prefix.strip()
            if prefix in ("start_hub", "end_hub", "hub"):
                self._parse_hub(line_no, prefix, rest)
            elif prefix == "connection":
                self._parse_connection(line_no, rest)
            else:
                self._print_error(f"unknown line type '{prefix}'", line_no)
                sys.exit(1)
        if not self.end_hub or not self.start_hub:
            self._print_error("start_hub and / or end_hub missing")
            sys.exit(1)

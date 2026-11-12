"""Animated terminal radar that replays the simulation on the map."""

import re
import time

from src.display import COLORS, Display
from src.models import Connection, Hub, ZoneType

RESET = COLORS['reset']
BOLD = '\033[1m'
REVERSE = '\033[7m'
TITLE_COLOR = '\033[1;38;5;255m'
FRAME_COLOR = '\033[38;5;31m'
DOT_COLOR = '\033[38;5;237m'
LINK_COLOR = '\033[38;5;242m'
TEXT_COLOR = '\033[38;5;250m'
LEGEND_COLOR = '\033[38;5;244m'
PULSE_HEAD = '\033[1;38;5;226m'
PULSE_TAIL = '\033[38;5;136m'
FLYING_COLOR = '\033[1;38;5;226m'
BAR_ON = '\033[38;5;41m'
BAR_OFF = '\033[38;5;238m'

SPACE_X = 4
SPACE_Y = 2
MARGIN_X = 2
MARGIN_Y = 1
MIN_INNER = 70
BAR_WIDTH = 30
SUBSTEPS = 8
SWEEP = '◜◝◞◟'
ANSI = re.compile(r'\033\[[0-9;?]*[A-Za-z]')

SYMBOLS: dict[ZoneType, str] = {
    ZoneType.NORMAL: '●',
    ZoneType.PRIORITY: '◆',
    ZoneType.RESTRICTED: '▲',
    ZoneType.BLOCKED: '✕',
}

Cell = tuple[int, int]

GLYPHS: dict[frozenset[str], tuple[str, str]] = {
    frozenset('LR'): ('─', '━'),
    frozenset('UD'): ('│', '┃'),
    frozenset('RD'): ('╭', '┏'),
    frozenset('LD'): ('╮', '┓'),
    frozenset('RU'): ('╰', '┗'),
    frozenset('LU'): ('╯', '┛'),
    frozenset('LRD'): ('┬', '┳'),
    frozenset('LRU'): ('┴', '┻'),
    frozenset('UDR'): ('├', '┣'),
    frozenset('UDL'): ('┤', '┫'),
    frozenset('LRUD'): ('┼', '╋'),
}


class Radar:
    """Draws the map in the terminal and replays the drones turn by turn.

    Each hub is drawn at its (x, y) position with a symbol for its zone
    type, in its map color, over a faint dot grid. When drones are in a
    hub, the symbol is replaced by their number on a colored block. A
    drone flying to a restricted zone is drawn as a star in the middle
    of its connection. Between two turns, a light pulse runs along each
    connection a drone is crossing.

    Attributes:
        hubs: Hubs of the map, stored by name.
        links: Connections of the map, stored by name ("hub_a-hub_b").
        pairs: Connection between two hubs, stored by both name orders.
        routes: The route of each drone, with one position per turn.
        title: Name shown in the top border, e.g. the map name.
        turn_count: Number of turns needed to deliver every drone.
        cells: Screen (row, column) of each hub, stored by name.
        link_chars: Plain line character of each connection cell.
        base: The map without drones, as a grid of characters.
        inner: Width of the panel, without its borders.
    """

    def __init__(self, hubs: dict[str, Hub], connections: list[Connection],
                 routes: list[list[str]], title: str = "") -> None:
        """Place the hubs on the screen and draw the empty map.

        Args:
            hubs: Hubs of the map, stored by name.
            connections: Connections of the map.
            routes: The route of each drone, as returned by the scheduler.
            title: Name shown in the top border, e.g. the map name.
        """
        self.hubs = hubs
        self.links = {f"{c.hub_a.name}-{c.hub_b.name}": c
                      for c in connections}
        self.pairs: dict[tuple[str, str], Connection] = {}
        for link in connections:
            self.pairs[(link.hub_a.name, link.hub_b.name)] = link
            self.pairs[(link.hub_b.name, link.hub_a.name)] = link
        self.routes = routes
        self.title = title
        self.turn_count = max(len(route) - 1 for route in routes)

        min_x = min(hub.x for hub in hubs.values())
        max_y = max(hub.y for hub in hubs.values())
        self.cells: dict[str, Cell] = {
            name: ((max_y - hub.y) * SPACE_Y + MARGIN_Y,
                   (hub.x - min_x) * SPACE_X + MARGIN_X)
            for name, hub in hubs.items()
        }
        self.hub_cells = set(self.cells.values())
        self.height = max(row for row, _ in self.cells.values()) + 1 \
            + MARGIN_Y
        self.width = max(col for _, col in self.cells.values()) + 1 \
            + MARGIN_X
        self.inner = max(self.width + 4, MIN_INNER)
        self.paths: dict[str, list[Cell]] = {}
        self._route_links()
        self.link_chars: dict[Cell, str] = {}
        self.base: list[list[str]] = [[' '] * self.width
                                      for _ in range(self.height)]
        self._draw_dots()
        self._draw_links()
        self._draw_hubs()

    def _draw_dots(self) -> None:
        """Draw a faint dot on every grid point, like a radar screen."""
        for row in range(MARGIN_Y, self.height, SPACE_Y):
            for col in range(MARGIN_X, self.width, SPACE_X):
                self.base[row][col] = f"{DOT_COLOR}·{RESET}"

    @staticmethod
    def _walk(corners: list[Cell]) -> list[Cell]:
        """Get the cells of a path made of straight segments.

        Args:
            corners: The start, each corner, and the end of the path.

        Returns:
            Each cell strictly between the start and the end, in order.
            Each cell touches the previous one by a side.
        """
        cells: list[Cell] = []
        row, col = corners[0]
        for target_row, target_col in corners[1:]:
            while (row, col) != (target_row, target_col):
                row += (target_row > row) - (target_row < row)
                col += (target_col > col) - (target_col < col)
                cells.append((row, col))
        return cells[:-1]

    def _candidates(self, link: Connection) -> list[list[Cell]]:
        """List the possible paths of a connection on the screen.

        A path is a straight line when the hubs are aligned. The other
        paths go horizontal-vertical-horizontal, or vertical-horizontal-
        vertical, through every nearby column or row. This includes L
        shapes and detours around a hub in the way.

        Args:
            link: The connection.

        Returns:
            The cells of each possible path, from hub_a to hub_b.
        """
        start = self.cells[link.hub_a.name]
        end = self.cells[link.hub_b.name]
        (r1, c1), (r2, c2) = start, end
        options: list[list[Cell]] = []
        if r1 == r2 or c1 == c2:
            options.append([start, end])
        for col in range(min(c1, c2) - SPACE_X, max(c1, c2) + SPACE_X + 1):
            if 0 <= col < self.width and r1 != r2:
                options.append([start, (r1, col), (r2, col), end])
        for row in range(min(r1, r2) - SPACE_Y, max(r1, r2) + SPACE_Y + 1):
            if 0 <= row < self.height and c1 != c2:
                options.append([start, (row, c1), (row, c2), end])
        return [self._walk(corners) for corners in options]

    @staticmethod
    def _bends(path: list[Cell]) -> int:
        """Count the turns of a path.

        Args:
            path: The cells of the path, in order.

        Returns:
            The number of times the path changes direction.
        """
        bends = 0
        for a, b, c in zip(path, path[1:], path[2:]):
            if (b[0] - a[0], b[1] - a[1]) != (c[0] - b[0], c[1] - b[1]):
                bends += 1
        return bends

    def _route_links(self) -> None:
        """Choose the path of every connection on the screen.

        Shorter connections are routed first. Each possible path gets a
        cost, and the cheapest one is chosen. From the most to the least
        important, the cost avoids:
            - crossing a hub, which would look like drones skipping it;
            - running right next to a hub that is not one of its ends,
              which would look like the line is connected to it;
            - sharing cells with the paths already chosen;
            - long paths and paths with many turns.
        """
        used: set[Cell] = set()

        def length(link: Connection) -> int:
            (r1, c1) = self.cells[link.hub_a.name]
            (r2, c2) = self.cells[link.hub_b.name]
            return abs(r2 - r1) + abs(c2 - c1)

        for name, link in sorted(self.links.items(),
                                 key=lambda item: length(item[1])):
            ends = {self.cells[link.hub_a.name], self.cells[link.hub_b.name]}
            others = self.hub_cells - ends

            def cost(path: list[Cell]) -> int:
                hubs_hit = sum(cell in others for cell in path)
                touching = sum(
                    (row + dr, col + dc) in others
                    for row, col in path
                    for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)))
                shared = sum(cell in used for cell in path)
                return (hubs_hit * 1000 + touching * 20 + shared * 2
                        + len(path) + self._bends(path) * 3)

            best = min(self._candidates(link), key=cost)
            self.paths[name] = best
            used.update(best)

    def _line_cells(self, link: Connection) -> list[Cell]:
        """Get the screen cells between the two hubs of a connection.

        Args:
            link: The connection.

        Returns:
            The (row, column) of each cell strictly between its hubs,
            from hub_a to hub_b, along the path chosen for it.
        """
        return list(self.paths[f"{link.hub_a.name}-{link.hub_b.name}"])

    def _midpoint(self, link: Connection) -> Cell:
        """Get the cell in the middle of a connection, avoiding hubs.

        Args:
            link: The connection.

        Returns:
            The cell closest to the middle of the path that is not a hub.
        """
        cells = self._line_cells(link)
        middle = len(cells) // 2
        free = [i for i, cell in enumerate(cells)
                if cell not in self.hub_cells]
        if not free:
            return cells[middle]
        return cells[min(free, key=lambda i: abs(i - middle))]

    def _cells_from(self, link: Connection, start: str) -> list[Cell]:
        """Get the cells of a connection, starting from one of its hubs.

        Args:
            link: The connection.
            start: Name of the hub to start from.

        Returns:
            The cells between the two hubs, ordered from start.
        """
        cells = self._line_cells(link)
        if start == link.hub_b.name:
            cells.reverse()
        return cells

    def _draw_links(self) -> None:
        """Draw every connection on the base grid, in gray.

        For each cell, the directions toward its neighbors on every line
        that crosses it are collected, then turned into one character:
        a straight line, a rounded corner, or a junction where several
        lines meet. A cell used only by connections with a capacity above
        1 is drawn with thick lines.
        """
        directions: dict[Cell, set[str]] = {}
        thin: set[Cell] = set()
        for link in self.links.values():
            points = ([self.cells[link.hub_a.name]]
                      + self._line_cells(link)
                      + [self.cells[link.hub_b.name]])
            for i in range(1, len(points) - 1):
                cell = points[i]
                found = directions.setdefault(cell, set())
                found.add(self._direction(cell, points[i - 1]))
                found.add(self._direction(cell, points[i + 1]))
                if link.max_link_capacity == 1:
                    thin.add(cell)

        for cell, found in directions.items():
            if cell in self.hub_cells:
                continue
            light, heavy = GLYPHS.get(frozenset(found), ('┼', '╋'))
            char = light if cell in thin else heavy
            row, col = cell
            self.link_chars[cell] = char
            self.base[row][col] = f"{LINK_COLOR}{char}{RESET}"

    @staticmethod
    def _direction(cell: Cell, other: Cell) -> str:
        """Get the side of a cell where a neighboring cell is.

        Args:
            cell: The cell.
            other: A cell that touches it by a side.

        Returns:
            "U", "D", "L" or "R" for up, down, left or right.
        """
        if other[0] < cell[0]:
            return 'U'
        if other[0] > cell[0]:
            return 'D'
        return 'L' if other[1] < cell[1] else 'R'

    def _paint(self, name: str, char: str) -> str:
        """Color a character with the map color of a hub.

        Args:
            name: Name of the hub.
            char: The character to color.

        Returns:
            The colored character, or the plain one if the hub has no
            known color.
        """
        color = self.hubs[name].color
        if color == 'rainbow':
            return Display.rainbow(char, 0)
        if color is not None and color in COLORS:
            return f"{COLORS[color]}{char}{RESET}"
        return char

    def _draw_hubs(self) -> None:
        """Draw the symbol of every hub on the base grid."""
        for name, hub in self.hubs.items():
            symbol = '◉' if hub.unlimited else SYMBOLS[hub.zone]
            row, col = self.cells[name]
            self.base[row][col] = self._paint(name, symbol)

    def _move_path(self, prev: str, pos: str) -> list[Cell]:
        """Get the cells a drone crosses between two turns.

        Args:
            prev: Position of the drone on the previous turn.
            pos: Position of the drone on this turn.

        Returns:
            The cells crossed, in order. A move onto a connection to a
            restricted zone covers its first half, and the arrival in the
            zone covers its second half. Empty if the drone waits.
        """
        if prev == pos:
            return []
        if prev in self.hubs and pos in self.hubs:
            return self._cells_from(self.pairs[(prev, pos)], prev)
        if pos in self.links:
            cells = self._cells_from(self.links[pos], prev)
            return cells[:len(cells) // 2 + 1]
        cells = self._cells_from(self.links[prev], pos)[::-1]
        return cells[len(cells) // 2:]

    def _pulses(self, turn: int, step: int) -> dict[Cell, str]:
        """Get the pulse cells of the moves made on a turn, at one step.

        Args:
            turn: The turn whose moves are animated.
            step: The animation step, from 0 to SUBSTEPS - 1.

        Returns:
            The colored character to draw on each pulse cell.
        """
        pulses: dict[Cell, str] = {}
        for route in self.routes:
            if turn >= len(route):
                continue
            path = self._move_path(route[turn - 1], route[turn])
            if not path:
                continue
            head = step * len(path) // SUBSTEPS
            for index, color in ((head - 1, PULSE_TAIL), (head, PULSE_HEAD)):
                if 0 <= index < len(path) \
                        and path[index] not in self.hub_cells:
                    cell = path[index]
                    char = self.link_chars.get(cell, '·')
                    pulses[cell] = f"{color}{char}{RESET}"
        return pulses

    def _visible_len(self, text: str) -> int:
        """Get the length of a text as shown, without its color codes.

        Args:
            text: The text, possibly with color codes.

        Returns:
            The number of characters shown on screen.
        """
        return len(ANSI.sub('', text))

    def _row(self, text: str = "") -> str:
        """Put a text between the side borders of the panel.

        Args:
            text: The text, possibly with color codes.

        Returns:
            The text, padded to the panel width, between two borders.
        """
        padding = ' ' * (self.inner - self._visible_len(text))
        return f"{FRAME_COLOR}│{RESET}{text}{padding}{FRAME_COLOR}│{RESET}"

    def _border(self, left: str, right: str, middle: str = "") -> str:
        """Build a horizontal border of the panel.

        Args:
            left: Left corner character.
            right: Right corner character.
            middle: Text shown on the left of the border, if any.

        Returns:
            The border line.
        """
        fill = '─' * (self.inner - 1 - self._visible_len(middle))
        return f"{FRAME_COLOR}{left}─{RESET}{middle}" \
               f"{FRAME_COLOR}{fill}{right}{RESET}"

    def _frame(self, turn: int, pulses: dict[Cell, str],
               tick: int) -> list[str]:
        """Build the screen lines of one turn.

        Args:
            turn: The turn whose drone positions are drawn, from 0.
            pulses: Pulse cells to draw on the connections.
            tick: Animation counter, used to turn the radar sweep icon.

        Returns:
            The lines to print: the whole panel.
        """
        grid = [row[:] for row in self.base]
        for (row, col), char in pulses.items():
            grid[row][col] = char

        counts: dict[str, int] = {}
        flying: list[str] = []
        delivered = 0
        for drone_id, route in enumerate(self.routes, start=1):
            pos = route[min(turn, len(route) - 1)]
            if pos in self.hubs:
                counts[pos] = counts.get(pos, 0) + 1
                if turn >= len(route) - 1:
                    delivered += 1
            else:
                row, col = self._midpoint(self.links[pos])
                grid[row][col] = f"{FLYING_COLOR}*{RESET}"
                flying.append(f"D{drone_id}→{route[turn + 1]}")

        start = ""
        for name, count in counts.items():
            row, col = self.cells[name]
            char = str(count) if count < 10 else '+'
            grid[row][col] = BOLD + REVERSE + self._paint(name, char)
            if self.hubs[name].unlimited and turn < self.turn_count:
                start = name

        total = len(self.routes)
        filled = delivered * BAR_WIDTH // total
        bar = (f"{BAR_ON}{'█' * filled}{BAR_OFF}"
               f"{'░' * (BAR_WIDTH - filled)}{RESET}")
        percent = delivered * 100 // total
        waiting = counts.get(start, 0) if start else 0
        in_flight = ', '.join(flying) if flying else '—'
        limit = self.inner - 14
        if len(in_flight) > limit:
            in_flight = in_flight[:limit - 1] + '…'

        title = f" {TITLE_COLOR}FLY-IN RADAR{RESET}"
        if self.title:
            title += f"{LEGEND_COLOR} · {self.title}{RESET}"
        title += f"   {TEXT_COLOR}Turn {turn:>2}/{self.turn_count}" \
                 f" {FRAME_COLOR}{SWEEP[tick % len(SWEEP)]}{RESET} "

        margin = ' ' * ((self.inner - self.width) // 2)
        lines = [self._border('╭', '╮', title)]
        lines += [self._row(margin + ''.join(row)) for row in grid]
        lines += [
            self._border('├', '┤'),
            self._row(f"  {TEXT_COLOR}Delivered{RESET}  {bar}  "
                      f"{BOLD}{delivered}/{total}{RESET} "
                      f"{LEGEND_COLOR}({percent}%){RESET}"),
            self._row(f"  {TEXT_COLOR}At start{RESET}   {waiting}"),
            self._row(f"  {TEXT_COLOR}In flight{RESET}  {in_flight}"),
            self._border('├', '┤'),
            self._row(f"  {LEGEND_COLOR}◉ start/end   ● normal   "
                      f"◆ priority   ▲ restricted   ✕ blocked{RESET}"),
            self._row(f"  {BOLD}{REVERSE}3{RESET}"
                      f"{LEGEND_COLOR} drones in a hub   {RESET}"
                      f"{FLYING_COLOR}*{RESET}"
                      f"{LEGEND_COLOR} flying to a restricted zone   "
                      f"{PULSE_HEAD}━{RESET}{LEGEND_COLOR} moving{RESET}"),
            f"{FRAME_COLOR}╰{'─' * self.inner}╯{RESET}",
        ]
        return lines

    def _draw(self, lines: list[str]) -> None:
        """Print a frame over the previous one.

        Args:
            lines: The lines of the frame.
        """
        print('\033[H' + '\n'.join(line + '\033[K' for line in lines),
              flush=True)

    def play(self, delay: float = 0.5) -> None:
        """Replay every turn in the terminal, from turn 0 to the last one.

        The screen is redrawn in place. Between two turns, a pulse runs
        along each connection a drone is crossing. Ctrl+C stops the
        replay cleanly.

        Args:
            delay: Seconds the pulses take to cross between two turns.
        """
        print('\033[2J\033[?25l', end='')
        tick = 0
        try:
            self._draw(self._frame(0, {}, tick))
            time.sleep(delay)
            for turn in range(1, self.turn_count + 1):
                for step in range(SUBSTEPS):
                    tick += 1
                    pulses = self._pulses(turn, step)
                    self._draw(self._frame(turn - 1, pulses, tick))
                    time.sleep(delay / SUBSTEPS)
                self._draw(self._frame(turn, {}, tick))
                time.sleep(delay / 2)
        except KeyboardInterrupt:
            pass
        finally:
            print('\033[?25h', end='', flush=True)

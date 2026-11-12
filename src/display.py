"""Colored terminal output of the simulation."""

from src.models import Hub


COLORS: dict[str, str] = {
    'orange': '\033[38;5;202m',
    'blue': '\033[38;5;21m',
    'red': '\033[38;5;160m',
    'green': '\033[38;5;34m',
    'purple': '\033[38;5;90m',
    'darkred': '\033[38;5;88m',
    'cyan': '\033[38;5;44m',
    'gold': '\033[38;5;214m',
    'brown': '\033[38;5;130m',
    'yellow': '\033[38;5;220m',
    'maroon': '\033[38;5;52m',
    'crimson': '\033[38;5;196m',
    'magenta': '\033[38;5;164m',
    'black': '\033[38;5;240m',
    'lime': '\033[38;5;148m',
    'violet': '\033[38;5;127m',
    'reset': '\033[0m'
}


class Display:
    """Colors the output lines with the colors of the zones.

    Each move takes the color of the zone the drone reaches, as set by
    the color metadata of the map. Moves onto a connection, toward a
    restricted zone, are shown in italics.

    Attributes:
        hubs: Hubs of the map, stored by name.
    """

    def __init__(self, hubs: dict[str, Hub]) -> None:
        """Store the hubs whose colors are used.

        Args:
            hubs: Hubs of the map, stored by name.
        """
        self.hubs = hubs

    @staticmethod
    def rainbow(txt: str, offset: int) -> str:
        """Color each character of a text with the next rainbow color.

        Args:
            txt: The text to color.
            offset: Index of the rainbow color used for the first
                character.

        Returns:
            The colored text, ending with a color reset.
        """
        rc: list[str] = [
            '\033[38;5;196m',
            '\033[38;5;202m',
            '\033[38;5;11m',
            '\033[38;5;34m',
            '\033[38;5;39m',
            '\033[38;5;21m',
            '\033[38;5;127m'
        ]
        if offset > len(rc):
            offset = offset % len(rc)
        result = ""
        i = 0 + offset
        for c in txt:
            if i >= len(rc):
                i = 0
            result += f'{rc[i]}{c}'
            i += 1
        result += COLORS['reset']
        return result

    def color_line(self, line: str) -> str:
        """Color every move of an output line.

        A move into a hub takes the color of that hub, or stays uncolored
        if the hub has no known color. A move onto a connection is shown
        in italics. The text itself is never changed.

        Args:
            line: An output line, e.g. "D1-roof1 D2-roof1-roof2".

        Returns:
            The same line with color codes around each move.
        """
        moves = line.split()
        colored: list[str] = []
        for move in moves:
            drone, _, place = move.partition('-')
            if place in self.hubs:
                color = self.hubs[place].color
                if color == "rainbow":
                    move = self.rainbow(move, 0)
                elif color in COLORS:
                    move = f"{COLORS[color]}{move}{COLORS['reset']}"
            else:
                move = f"\033[3m{move}{COLORS['reset']}"
            colored.append(move)
        return " ".join(colored)

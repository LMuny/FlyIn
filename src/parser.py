import sys


class MapParser:
    def __init__(self, filepath: str) -> None:
        self.filepath = filepath

    def _load_txt(self) -> str:
        try:
            with open(self.filepath, 'r') as f:
                return f.read()
        except OSError as e:
            print(f"[ERROR] Incorrect file path: {e}")
            sys.exit(1)

    def extract_lines(self) -> list[tuple[int, str]]:
        clean_lines: list[tuple[int, str]] = []
        raw_text = self._load_txt()
        all_lines = raw_text.splitlines()
        for line_no, line in enumerate(all_lines, start=1):
            line = line.strip()
            if line.startswith('#') or line == "":
                continue
            clean_lines.append((line_no, line))
        return clean_lines

    def parse_nb_drone(self) -> dict[str, int]:
        arg_list = self.extract_lines()
        result: dict = {}
        if arg_list[0][1].startswith("nb_drones"):
            name, nb = arg_list[0][1].split(':')
            name = name.strip()
            try:
                nb_drone = int(nb)
            except Exception as e:
                raise ValueError(e)
            result[name] = nb_drone
        else:
            print("[ERROR] First line should be 'nb_drone'")
            sys.exit(1)
        if result[name] <= 0:
            print("[ERROR] nb_drone should be greater than 0")
            sys.exit(1)
        return result



if __name__ == '__main__':
    parser = MapParser('maps/easy/01_linear_path.txt')
    result = parser.parse_nb_drone()
    print(result)

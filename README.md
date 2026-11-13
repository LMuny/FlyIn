*This activity has been created as part of the 42 curriculum by lmuny.*

# Fly-In

## Description

Fly-In is a drone routing simulator. A map describes a network of **hubs** (zones) linked by
two-way **connections**. A fleet of drones starts on the `start_hub` and must reach the
`end_hub` in as few turns as possible, without ever breaking the rules of the map:

- each hub holds at most `max_drones` drones at once (the start and end hubs are unlimited);
- each connection carries at most `max_link_capacity` drones on the same turn;
- zones have a type that changes how drones move into them:

| Zone type    | Effect                                                            |
|--------------|-------------------------------------------------------------------|
| `normal`     | Entering takes 1 turn                                             |
| `priority`   | Entering takes 1 turn, and these zones are preferred on equal cost |
| `restricted` | Entering takes 2 turns: the drone spends 1 turn on the connection |
| `blocked`    | Can never be entered                                              |

The program reads a map, plans a route for every drone, and prints the simulation one line per
turn. Each line lists the drones that move on that turn as `D<id>-<zone>`, or
`D<id>-<hub_a>-<hub_b>` when a drone is in flight on a connection toward a restricted zone.
Drones that wait or have already arrived are not printed.

The goal is to deliver every drone in as few turns as possible.

## Instructions

### Requirements

- Python **3.10+**
- [uv](https://docs.astral.sh/uv/) to manage the virtual environment and dependencies
- Runtime dependency: `pydantic` (installed by `uv`)

### Installation

```bash
make install        # same as: uv sync
```

### Running

```bash
make run MAP=maps/easy/01_linear_path.txt
# or directly
uv run python3 -m src maps/easy/01_linear_path.txt
```

### Other Makefile rules

| Rule               | Description                                          |
|--------------------|------------------------------------------------------|
| `make debug MAP=…` | Run the program under `pdb`                          |
| `make lint`        | Run `flake8` and `mypy` with the required flags      |
| `make lint-strict` | Run `flake8` and `mypy --strict`                     |
| `make clean`       | Remove `__pycache__` folders and the mypy cache      |

### Map file format

```text
# Comments start with '#', blank lines are ignored
nb_drones: 4

start_hub: start 0 0 [color=green]
hub: junction 1 0 [color=yellow max_drones=2]
hub: path_a 2 1 [color=blue]
hub: path_b 2 -1 [color=blue zone=restricted]
end_hub: goal 3 0 [color=red]

connection: start-junction [max_link_capacity=2]
connection: junction-path_a
```

- The first useful line must be `nb_drones: <positive int>`.
- Hubs: `<start_hub|end_hub|hub>: <name> <x> <y> [metadata]`, with the optional tags `zone`,
  `color` and `max_drones` (default 1). Names can't contain `-`.
- Connections: `connection: <hub_a>-<hub_b> [max_link_capacity=<n>]` (default 1).

Any invalid line (unknown tag, bad value, duplicate hub or connection, unknown hub, missing
start or end, etc.) stops the program with an `[ERROR]` message giving the line number. The
program also refuses a map where the end can't be reached from the start.

## Algorithm and implementation strategy

### Project layout

| File                | Role                                                                 |
|---------------------|----------------------------------------------------------------------|
| `src/models.py`     | Pydantic models `Hub`, `Connection` and the `ZoneType` enum (with its turn cost) |
| `src/parser.py`     | `MapParser`: reads and validates the map file line by line           |
| `src/graph.py`      | `Graph`: adjacency list of the hubs, plus a BFS reachability check   |
| `src/scheduler.py`  | `Scheduler`: plans every drone's route turn by turn                  |
| `src/simulation.py` | `Simulation`: turns the routes into the output lines                 |
| `src/display.py`    | `Display`: colors the output in the terminal                         |
| `src/__main__.py`   | Entry point that chains all of the above                             |

### 1. Parsing and validation

The parser strips comments and blank lines, keeps the line numbers for error messages, then
dispatches each line on its prefix (`hub`, `start_hub`, `end_hub`, `connection`). Values are
validated both by hand (clear error messages) and by Pydantic (`max_drones > 0`, typed fields).
Connections are stored with a sorted key `(min, max)` so that `a-b` and `b-a` are detected as
duplicates.

### 2. Graph

The `Graph` builds an adjacency list where each hub maps to a list of `(neighbor, connection)`
pairs, adding every connection in both directions. Before planning, a **breadth-first search**
that never enters blocked zones checks that the end is reachable at all.

### 3. Planning: prioritized planning with a time-expanded Dijkstra

Planning all drones at once is a hard multi-agent problem, so the scheduler uses
**prioritized planning**: drones are planned **one after the other**, and each route is
**booked** before the next drone is planned.

- **Reservation tables.** `hub_bookings[(hub, turn)]` and `link_bookings[(connection, turn)]`
  count how many drones already use a hub or a connection on a given turn. A hub is booked on
  every turn a drone is in it (waiting included); a connection is booked on the turn it is
  crossed.

- **Time-expanded search.** For each drone, `best_route` runs **Dijkstra's algorithm on
  `(hub, turn)` states** rather than on hubs alone. From a state, the drone can:
  - **wait** in its hub (if the hub still has room on the next turn);
  - **move** to a neighbor that isn't blocked, if the connection has room on the next turn and
    the neighbor has room on the arrival turn (`turn + 1`, or `turn + 2` for a restricted zone).

  Since time is part of the state, the search naturally finds when it is better to wait for a
  bottleneck to clear than to take a long detour, and it can't loop forever in cycles.

- **Cost and tie-breaking.** The heap is ordered by `(arrival turn, priority score)`. The turn
  count is minimized first; on equal turns, the route that goes through more `priority` zones
  wins (each one lowers the score by 1).

- **Restricted zones.** Moving into a restricted zone adds an extra position to the route: the
  connection name for the in-flight turn, then the zone on the next turn. That way the output
  shows `D1-loop_b-exit_point` on turn N and `D1-exit_point` on turn N+1.

Because every later drone sees the bookings of the earlier ones, the plan is **conflict-free by
construction**: no capacity check is needed during the simulation. The first drone gets the
shortest path, and the next ones either take another branch or wait just long enough, which
spreads the fleet over all the parallel paths of the map.

### 4. Simulation

A route is a list with one position per turn (index 0 = start). The simulation walks through
the turns from 1 to the length of the longest route and prints, for each drone, its new
position only when it differs from the previous one, so waiting and arrived drones are left out.

### Results on the provided maps

| Map                                  | Drones | Turns |
|--------------------------------------|:------:|:-----:|
| easy/01_linear_path                  | 2      | 4     |
| easy/02_simple_fork                  | 4      | 4     |
| easy/03_basic_capacity               | 4      | 4     |
| medium/01_dead_end_trap              | 5      | 8     |
| medium/02_circular_loop              | 6      | 10    |
| medium/03_priority_puzzle            | 5      | 6     |
| hard/01_maze_nightmare               | 8      | 13    |
| hard/02_capacity_hell                | 12     | 16    |
| hard/03_ultimate_challenge           | 15     | 26    |
| challenger/01_the_impossible_dream   | 25     | **43** (reference record: 45) |

## Visual representation

When the output goes to a terminal, every move is colored to make the simulation easy to
follow at a glance:

- **Zone colors.** Each move `D<id>-<zone>` is printed in the color set by the zone's `color`
  metadata in the map (a 256-color ANSI palette: `red`, `blue`, `green`, `gold`, `cyan`, …).
  You can see right away which part of the map each drone is in, and how the fleet spreads over
  the different branches.
- **Rainbow zones.** A zone with `color=rainbow` is printed with one color per character.
- **In-flight moves in italics.** A move onto a connection (`D<id>-<hub_a>-<hub_b>`, toward a
  restricted zone) is printed in *italics*, so the 2-turn moves stand out from the normal ones.
- **Colored errors.** Parsing errors start with a red `[ERROR]` tag and give the line number
  of the problem.
- **Clean output when piped.** Colors are only added when `stdout` is a terminal
  (`isatty()`). When the output is redirected to a file or another program, the lines are
  printed as plain text with the exact required format.

## Example

Input (`maps/easy/02_simple_fork.txt`):

```text
nb_drones: 4

start_hub: start 0 0 [color=green]
hub: junction 1 0 [color=yellow max_drones=2]
hub: path_a 2 1 [color=blue]
hub: path_b 2 -1 [color=blue]
end_hub: goal 3 0 [color=red]

connection: start-junction [max_link_capacity=2]
connection: junction-path_a
connection: junction-path_b
connection: path_a-goal
connection: path_b-goal
```

Output:

```text
D1-junction D2-junction
D1-path_a D2-path_b D3-junction D4-junction
D1-goal D2-goal D3-path_a D4-path_b
D3-goal D4-goal
```

Two drones enter the junction together (it holds 2), then split over the two branches so that
the next pair can follow right behind: 4 drones are delivered in 4 turns.

Example with a restricted zone (`maps/medium/02_circular_loop.txt`, first turns):

```text
D1-loop_a D2-loop_a
D1-loop_b D3-loop_a
D1-loop_b-exit_point D2-loop_b D4-loop_a
D1-exit_point D2-loop_b-exit_point D3-loop_b D5-loop_a
D1-goal D2-exit_point D3-loop_b-exit_point D4-loop_b D6-loop_a
...
```

`exit_point` is restricted and holds one drone: each drone spends one turn on the
`loop_b-exit_point` connection, then arrives on the next turn, and the drones go through one by
one in a steady pipeline.

## Resources

- [Dijkstra's algorithm (Wikipedia)](https://en.wikipedia.org/wiki/Dijkstra%27s_algorithm)
- [Breadth-first search (Wikipedia)](https://en.wikipedia.org/wiki/Breadth-first_search)
- [Multi-agent pathfinding (Wikipedia)](https://en.wikipedia.org/wiki/Multi-agent_pathfinding)
- D. Silver, *Cooperative Pathfinding* (AIIDE 2005), which introduces reservation tables and
  space-time search for cooperative A*
- [Python `heapq` documentation](https://docs.python.org/3/library/heapq.html)
- [Pydantic documentation](https://docs.pydantic.dev/)
- [ANSI escape codes (Wikipedia)](https://en.wikipedia.org/wiki/ANSI_escape_code)
- [uv documentation](https://docs.astral.sh/uv/)

### Use of AI

AI (Claude) was used as a tutor and reviewer throughout the project, not as a code generator:

- **Understanding the problem:** explaining concepts such as time-expanded graphs, reservation
  tables and prioritized planning, and discussing the tradeoffs between possible approaches.
- **Debugging and review:** pointing out bugs and edge cases in my own code (parser validation,
  booking of restricted connections) so I could fix them myself.
- **Documentation:** help with wording the docstrings and writing this README.

All the code was written and is understood by me; AI suggestions were only kept after I
could explain them.

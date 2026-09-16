# Double Queens Hint

Milestone 3: elementary, candidate-set, and local constraint hints with
structured, replayable proofs.

## Origin: the L6C5 incident

This project began with a real Double Queens game in which the green region
logically forced a queen at L6C5. An AI assistant named GPTou initially failed
to identify that deduction reliably. The queen was forced; the explanation
apparently needed more structure.

That incident established the project's main design goal: logical hints must
be deterministic, structured, explainable, replayable, and regression tested,
rather than produced by opaque solving behavior. The original position is
preserved as `known_game_001` in [tests/test_known_games.py](tests/test_known_games.py),
where placing a queen at L6C5 is an explicit regression test.

## Run

```sh
uv sync
uv run pytest
```

```python
from double_queens import Board, CellState, next_hint, render_hint, render_board

regions = [[f"region_{r}" for _ in range(8)] for r in range(8)]
state = [[CellState.UNKNOWN] * 8 for _ in range(8)]
state[0][0] = CellState.QUEEN
board = Board(regions, state)
hint = next_hint(board)
if hint is not None:
    log.info(render_hint(hint, level=1))
    log.info(render_hint(hint, level=4))
    board.apply(hint)
log.info("board_state", board=render_board(board))
```

## Running tests

Run these commands from the repository root, after `uv sync`:

```sh
# Run the complete test suite
uv run pytest

# Run every test in one file
uv run pytest tests/test_known_games.py

# Run one specific test function
uv run pytest tests/test_known_games.py::test_known_game_001_next_hint_l6c5

# Show board/deduction logs live (-s) and individual test names (-v)
uv run pytest -s -v tests/test_known_games.py::test_known_game_001_logical_replay
```

The `::` separator selects a function within a test file. Add `-s -v` to
any of these commands to inspect the debug output while tests run.

## Architecture and public APIs

- `board.py`: `Cell`, `CellState`, string `RegionId`, `GroupKind`, `Group`,
  `Board`, and `ContradictionError`. Board construction copies square input
  grids; `state` is a read-only tuple grid. Coordinates are zero-based;
  `str(Cell(...))` uses one-based `L…C…` notation.
- Board queries: `row`, `column`, `region`, `cells`, `groups`, `at`, `queens`,
  `unknown`, `excluded`, `neighbors`, `validate`, and `is_solved`.
- `deduction.py`: immutable `Action`, `CellFact`, `Premise`, `Deduction`, and
  `Rule`. Group evidence records quota, group membership, and every observed
  state. Adjacency evidence records the queen and unknown targets. These
  facts are the structured explanation; consequences are separate actions.
- `rules/`: forced remaining cells, queen adjacency, completed groups,
  common-neighbor exclusion, and advanced local constraint reasoning.
- `QueenConstraint(cells, queen_count, source=None)` normalizes cells into a
  frozen set and validates the exact count. `derive_constraints(board)` returns
  each row, column, and region's unknown cells and remaining queen quota, with
  a full `Premise` snapshot as its source.
  Common-neighbor deductions carry this constraint and `AdjacencyFact` pairs
  connecting each excluded target to every candidate. Target states and source
  facts participate in the existing stale-evidence checks.
- `engine.py`: `find_deductions`, `best_deduction`, and `next_hint`.
  Queries validate without mutation. Ranking uses difficulty, explicit rule
  priority (forced queens, adjacency, completed groups, common neighbors), evidence count,
  action count, then stable coordinate/source tie breakers.
  Discovery returns the M1/M2 tier whenever it has deductions; otherwise it
  evaluates M3 (difficulty 3). Structural proof tie breakers are deterministic.
- `Board.apply`: checks evidence freshness, rejects state conflicts, validates
  the resulting board, then commits atomically. It applies supplied actions
  without additional propagation. It is not a proof verifier for arbitrary
  caller-created deductions; use deductions returned by the engine.
- `hints/`: `render_hint` (levels 1–4), `render_deduction` (evidence and
  conclusions), and `render_board` (compact terminal grid and optional region legend).
  Colors are cosmetic. `DebugRenderContext` owns one randomized
  `RegionPalette` for a complete debug trace, so boards and human-readable
  hints share stable glyphs. Seeds and custom RNGs make tests deterministic.
- `solver.py`: `solve_logically` mutates the supplied board by repeatedly
  calling `engine.next_hint` and `board.apply`. `LogicalSolveResult` holds the
  board, immutable history, `SolveStatus`, `solved`, and `reason`.

## Validation and scope decisions

Construction rejects malformed input. Explicit `validate`, engine queries,
application, and solved checks reject locally contradictory states with
`ContradictionError`. This permits constructing invalid states for inspection.
Validation checks group overfill/underfill and immediate queen adjacency.
The number of regions must equal the board size because both total quotas
are twice their respective group counts. No fixed size or palette is assumed.

A board is solved when every quota is met and queens do not touch; remaining
unknown cells do not need cosmetic exclusion marks. Stale deductions raise
`ValueError`; application failures leave the board unchanged. Invalid boards
raise errors rather than being reported as a logical stall.

Local validation does not establish global solvability. Unsupported situations
return `LOGIC_STALLED`. There is no guessing, backtracking, screenshot ingestion,
exhaustive solver, or GUI.

The real-game fixture still places L6C5 at step 1. Milestone 1 stalled after
7 deductions; milestone 2 solves it in 32 deductions, including 3 common-neighbor
deductions. Its complete history is checked by replaying the public hint API.

The initially empty `known_game_002` stalled immediately with M2. M3 currently
solves it in 55 deductions, 16 requiring advanced evidence. All 20 queens are
placed; two unknown cells remain because solved status does not require cosmetic
exclusions. The test requires progress and deterministic replay, not a stored
solution or a particular human solving order.

## Local constraints and proof lifecycle

`derive_inclusions(constraints)` subtracts directly included candidate sets
and their counts. `analyze_local_placements(board, constraint, constraints=None)`
enumerates every placement of at most two queens inside that single residual
constraint. Its input must be a current, proven constraint, such as one returned
by `derive_constraints`; it does not certify arbitrary caller-invented facts.

Each placement is checked for queen adjacency and directly intersecting quotas.
An intersecting constraint is impossible if the placement overfills it or leaves
too few available cells after accounting for unselected source candidates and
immediately attacked cells. No Board is copied or mutated, and no hypothetical
placement calls the hint engine or solver. An empty valid-placement set raises
`ContradictionError`; it cannot justify conclusions by vacuous agreement.

`derive_subconstraint(analysis, cells)` returns a constraint when all recorded
placements agree on its cardinality, otherwise `None`.
`derive_local_constraints(board)` computes a single deterministic pass of
inclusions and placement-derived facts. Automatic subsets are singletons,
row/column/region intersections, adjacency components, and their complements.
It does not enumerate arbitrary subsets or repeatedly combine facts to closure.
Inclusion facts participate in immediate placement checks; placement-derived
facts are then consumed by the existing forced-cell, completed-group, and
common-neighbor rules. A separate `LOCAL_PLACEMENT_EXCLUSION` rule handles
external cells attacked in every placement by potentially different queens.

Constraints are ephemeral per-query facts, recomputed after each actual action.
`QueenConstraint.derivation` holds an immutable `InclusionProof` or
`PlacementSubsetProof`. `LocalPlacements` records accepted placements, checked
constraints, and `PlacementRejection` records with a `PlacementConflict` reason,
counts, available cells, or adjacency witnesses. `PlacementCoverage` records an
attacking queen for each placement when excluding an external cell.

Proof snapshots include the consulted groups and candidate neighborhoods.
They are flattened into ordinary `Premise` values for existing stale-evidence
and atomic-application checks. Renderers consume the saved proof, including after
the board changes, and do not reconstruct it by solving again. Debug rendering
shows nested source proofs, valid placements, and immediate rejection reasons.
All four progressive hint levels and the shared debug region palette apply.

More reasoning, if needed by another fixture, requires a separately approved
milestone. No later milestone is implemented here.

## Terminal alignment

`render_board` keeps width estimation and padding in a single presentation
helper. `terminal_profile="auto"` selects the VS Code profile when
`TERM_PROGRAM=vscode`; that profile compensates for narrow 🩶 and 🩵 in the
older terminal width table. Use `terminal_profile="unicode"` for saved
Markdown or terminals with newer width tables. Two-digit row labels remain
presentation-only.

Font metrics cannot be inferred perfectly from Unicode. Override measured
glyph widths centrally for your setup, for example:

```python
render_board(board, use_emojis=True, terminal_profile="vscode",
             glyph_widths={"🤍": 1})
```

This adds one padding space for a white heart that advances one column on
that terminal. Overrides support entire glyph sequences, not only individual
characters. They also apply in the queen-region summary. Complex joined
emoji may need an explicit override. Text mode remains available with
`use_emojis=False`. No terminal settings are changed.

The white heart in the alignment example comes from the test's temporary
palette override; the normal palette contains ⚪, 🩶 and 🩵, not 🤍.
Before removing wcwidth, the diagnostic reported `len=1, wcswidth=2` for each
of 🔴 🔵 ⚪ 🤍 🩶 🩵 👑 ❌. Those numbers do not measure font appearance.

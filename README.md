# Double Queens Hint

Milestone 1: elementary, explainable Python hints. No runtime dependencies.

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
    print(render_hint(hint, level=1))
    print(render_hint(hint, level=4))
    board.apply(hint)
print(render_board(board))
```

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
- `rules/`: only forced remaining cells, queen adjacency, and completed groups.
- `engine.py`: `find_deductions`, `best_deduction`, and `next_hint`.
  Queries validate without mutation. Ranking uses difficulty, explicit rule
  priority (forced queens, adjacency, completed groups), evidence count,
  action count, then stable coordinate/source tie breakers.
- `Board.apply`: checks evidence freshness, rejects state conflicts, validates
  the resulting board, then commits atomically. It applies supplied actions
  without additional propagation. It is not a proof verifier for arbitrary
  caller-created deductions; use deductions returned by the engine.
- `hints/`: `render_hint` (levels 1–4), `render_deduction` (evidence and
  conclusions), and `render_board` (Markdown grid and dynamic region legend).
  Colors are cosmetic; numbered labels stay distinct beyond the palette.
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
return `LOGIC_STALLED`. There is no guessing, backtracking, candidate-set
reasoning, screenshot ingestion, exhaustive solver, or GUI. Section 23's debug
views are included as presentation helpers. No milestone 2 features are included.

Next step, only after explicit approval: milestone 2 candidate-set reasoning.

# Double Queens — Logical Hint Engine

# 1. Goal

Build a Python engine for a variant of the Queens puzzle.

The primary goal is NOT to build a brute-force solver.

The primary goal is to build an explainable logical deduction engine that can inspect a partially completed board and find the next deduction that a human player could logically make.

The same engine MAY later be used as a solver simply by repeatedly:

1. finding a logical deduction;
2. applying it;
3. repeating until the board is solved or no known deduction exists.

Therefore:

> The solver must be built on top of the hint engine, not the other way around.

A hint must NEVER be justified only by:

> "The full solver says this cell is a queen."

Every hint must have an explicit logical proof.

---

# 2. Puzzle rules

The board is an N × N square grid.

Each cell belongs to exactly one colored region.

Exactly TWO queens must exist in:

- every row;
- every column;
- every colored region.

Queens may NOT touch each other.

"Touch" means any of the 8 immediately adjacent cells:

- horizontal;
- vertical;
- diagonal.

Unlike classical chess queens, queens may share longer diagonals.

Only immediate adjacency is forbidden.

---

# 3. Cell states

Each cell has one of three states:

```python
UNKNOWN = 0
QUEEN = 1
EXCLUDED = -1
```

Meaning:

- `UNKNOWN`: no conclusion has yet been made.
- `QUEEN`: the cell definitely contains a queen.
- `EXCLUDED`: the cell definitely cannot contain a queen.

---

# 4. Board representation

Suggested initial representation:

```python
from dataclasses import dataclass

@dataclass(frozen=True)
class Cell:
    row: int
    col: int
```

Coordinates should internally be zero-based.

Human-facing coordinates should be one-based:

```text
row 0, col 0 -> L1C1
row 5, col 4 -> L6C5
```

The board should contain something equivalent to:

```python
class Board:
    size: int
    regions: list[list[RegionId]]
    state: list[list[CellState]]
```

It should provide helpers such as:

```python
board.row(r)
board.column(c)
board.region(region_id)

board.queens(cells)
board.unknown(cells)
board.excluded(cells)

board.neighbors(cell)
```

Do not put deduction logic directly inside `Board`.

`Board` represents state.

Deduction rules operate on `Board`.

---

# 5. Core architecture

Use four distinct concepts:

```text
Board
  ↓
Deduction Rules
  ↓
Deduction
  ↓
Hint Renderer / Solver
```

Suggested structure:

```text
double_queens/
    board.py
    deduction.py
    engine.py

    rules/
        completed_group.py
        forced_cells.py
        adjacency.py
        candidate_sets.py
        overlap.py

    hints/
        renderer.py

    solver.py

tests/
```

The architecture should make the logical deduction engine the central component.

The optional solver should merely consume deductions produced by the same engine.

---

# 6. Deduction object

Every logical conclusion must be represented explicitly.

Example:

```python
@dataclass
class Deduction:
    actions: list[Action]
    rule: str
    premises: list[Premise]
    explanation: Explanation
    difficulty: int
```

An `Action` could be:

```python
@dataclass
class Action:
    cell: Cell
    state: CellState
```

Example:

```python
Action(
    cell=Cell(5, 4),
    state=QUEEN
)
```

A deduction MUST contain enough structured information to explain WHY the action is valid.

Do not make explanations depend exclusively on arbitrary pre-written strings.

The structured deduction should be usable by:

- the hint renderer;
- a GUI;
- tests;
- debug output;
- the logical solver;
- a future exhaustive verifier.

---

# 7. Important design rule: premises vs consequences

Keep the evidence used for a deduction separate from its consequences.

Example:

A region contains:

- one confirmed queen;
- one remaining unknown cell;
- all other cells excluded.

Premises:

```text
Region Green requires 2 queens.
L5C2 is already a queen.
Every region cell except L6C5 is excluded.
```

Conclusion:

```text
L6C5 = QUEEN
```

Do NOT immediately include all exclusions caused by `L6C5` in the same deduction unless the rule explicitly represents propagation.

Instead:

Deduction 1:

```text
L6C5 = QUEEN
```

Then after applying it:

Deduction 2:

```text
Adjacent cells to L6C5 = EXCLUDED
```

This makes hint progression understandable and allows the logical solver to follow exactly the same steps as a human-facing hint system.

---

# 8. Basic deduction rules

## Rule A — Completed group

For every:

- row;
- column;
- region;

if it already contains exactly 2 queens:

all other `UNKNOWN` cells in that group are `EXCLUDED`.

Example:

```text
Row 4 already contains two queens.

=> every other cell of row 4 is excluded.
```

---

## Rule B — Forced remaining cells

For every row, column, or region:

```python
queens_missing = 2 - queen_count
```

If:

```python
len(unknown_cells) == queens_missing
```

then every unknown cell must be a queen.

Example:

```text
Green region:
1 queen already placed
1 unknown cell remains

=> unknown cell is a queen.
```

This is the rule that detects:

```text
L6C5 = QUEEN
```

in the example discussed during development.

---

## Rule C — Queen adjacency

For every confirmed queen:

all `UNKNOWN` adjacent cells are `EXCLUDED`.

This includes:

```text
NW N NE
W  Q  E
SW S SE
```

Only immediate neighbors are affected.

Queens do NOT attack arbitrary cells along diagonals as in chess.

---

# 9. Candidate-set reasoning

This is one of the most important features.

The engine must reason not only about confirmed queens but also about sets of cells in which queens are forced to occur.

Example:

A row still needs ONE queen.

Its only candidates are:

```text
A B
```

Therefore:

```text
exactly one queen exists somewhere in {A, B}
```

Even though the engine does not know whether `A` or `B` contains the queen, this fact may allow other cells to be excluded.

This type of intermediate knowledge should be treated as a first-class concept rather than discarded because the exact queen position is unknown.

---

# 10. Forced queen sets

Represent such information explicitly.

Suggested structure:

```python
@dataclass(frozen=True)
class QueenConstraint:
    cells: frozenset[Cell]
    queen_count: int
    source: ConstraintSource
```

Example:

```python
QueenConstraint(
    cells=frozenset({L4C7, L4C8}),
    queen_count=1,
    source=Row(4)
)
```

Meaning:

```text
Exactly one of L4C7 / L4C8 must contain a queen.
```

More generally:

```text
Exactly N queens must occur among this set of candidate cells.
```

These constraints can originate from:

- rows;
- columns;
- regions;
- deductions produced by combinations of existing constraints.

---

# 11. Common-neighbor exclusion

Suppose exactly one queen must exist among:

```text
A B
```

If cell `X` touches BOTH `A` and `B`:

`X` cannot contain a queen.

Because whichever candidate becomes the queen would touch `X`.

Therefore:

```text
queen must exist somewhere in S

AND

X is incompatible with every cell in S

=>

X = EXCLUDED
```

Example:

```text
A B
 X
```

If exactly one of `A` or `B` must be a queen, and `X` is adjacent to both:

```text
X = EXCLUDED
```

This deduction must NOT require choosing between `A` and `B`.

The uncertainty itself is enough to make the exclusion.

Start with this simple/common case first.

Later, generalize candidate-set reasoning carefully.

---

# 12. Group confinement / overlap reasoning

The engine should eventually detect deductions where candidates are confined to intersections between groups.

Example:

A region still needs two queens.

All possible cells for those two queens lie within a particular subset of rows or columns.

That confinement can impose constraints on those rows or columns.

Similarly:

If the remaining queen(s) of a row can only occur inside one region, that can constrain the remaining cells of that region.

This is conceptually similar to "locked candidates" in Sudoku.

Possible terminology:

```text
Confinement
LockedCandidateSet
GroupOverlap
```

Prefer mathematically clear names over Sudoku-specific names.

The important concept is:

> If a required number of queens for constraint A must occur entirely inside the intersection between constraint A and constraint B, then this occupancy may constrain the remainder of B.

---

# 13. General constraint model

Ultimately, each row/column/region can be viewed as a cardinality constraint:

```python
sum(cell_is_queen for cell in group) == 2
```

After accounting for confirmed queens and excluded cells, this becomes constraints such as:

```text
exactly 1 queen among {A, B, C}
```

Adjacency creates constraints:

```python
Q(a) + Q(b) <= 1
```

for adjacent cells.

Many advanced deductions can therefore be obtained by combining small cardinality constraints.

However:

DO NOT immediately replace the logical engine with an opaque SAT/SMT solver.

A SAT/SMT solver may later be used:

- to validate puzzles;
- detect contradictions;
- test uniqueness;
- verify deductions;
- identify unsupported logical situations;
- compare the logical engine with exhaustive reasoning.

But user-facing hints should come from named, explainable logical rules.

---

# 14. Hint system

The engine should separate:

```python
find_deductions(board)
```

from:

```python
render_hint(deduction, level)
```

The same deduction can therefore generate progressively stronger hints.

## Hint level 1 — Area

Example:

```text
Look at the green region.
```

The player only learns where to look.

---

## Hint level 2 — Observation

Example:

```text
The green region needs two queens.
One is already placed. How many possible cells remain?
```

The player is pointed toward the relevant logical relationship without being given the conclusion.

---

## Hint level 3 — Deduction

Example:

```text
Only L6C5 remains available for the second queen.
```

The logical conclusion is revealed.

---

## Hint level 4 — Action

Example:

```text
Place a queen at L6C5.
```

The exact action is revealed.

The renderer should preferably generate these levels from structured deduction metadata rather than storing four arbitrary strings.

---

# 15. Hint selection

`next_hint()` may find multiple deductions.

Do NOT simply return the first one found because dictionary/list iteration order happens to encounter it first.

Rank deductions.

Initial ranking criteria could be:

1. direct forced queen;
2. direct adjacency exclusion;
3. completed-group exclusions;
4. candidate-set deduction;
5. overlap/confinement deduction;
6. more complex multi-constraint deductions.

Also consider:

- number of premises;
- number of affected cells;
- conceptual difficulty;
- amount of progress created;
- whether the deduction places a queen or only excludes candidates.

Suggested API:

```python
deductions = engine.find_deductions(board)

hint = engine.best_deduction(
    deductions,
    strategy="easiest"
)
```

Possible future strategies:

```python
strategy="easiest"
strategy="most_progress"
strategy="queen_first"
```

---

# 16. Difficulty

Each rule should expose a rough difficulty.

Example:

```python
DIRECT_FORCED_CELL = 1
QUEEN_ADJACENCY = 1
COMPLETED_GROUP = 1

COMMON_NEIGHBOR = 2
LOCKED_SET = 2

GROUP_OVERLAP = 3
MULTI_CONSTRAINT = 4
```

This enables future modes such as:

```python
next_hint(max_difficulty=2)
```

or:

```python
next_hint(strategy="easiest")
next_hint(strategy="most_progress")
```

Difficulty should represent the complexity of the human reasoning required, not computational cost.

---

# 17. Applying deductions

The engine must NOT silently mutate the board when searching.

Use:

```python
deduction = engine.next_hint(board)

board.apply(deduction)
```

This is important because the UI may want to:

- display the hint;
- highlight cells;
- wait for the player;
- verify that the player performed the expected action;
- request a stronger hint;
- record logical history.

`find_deductions()` should therefore be a pure query over board state whenever practical.

---

# 18. Logical solver

The optional logical solver should be deliberately boring.

Conceptually:

```python
def solve_logically(board):

    history = []

    while not board.is_solved():

        deduction = engine.next_hint(board)

        if deduction is None:
            return LogicalSolveResult(
                solved=False,
                board=board,
                history=history,
                reason="No supported logical deduction found"
            )

        board.apply(deduction)
        history.append(deduction)

    return LogicalSolveResult(
        solved=True,
        board=board,
        history=history
    )
```

IMPORTANT:

Do not add hidden guessing or backtracking to this function.

If the deduction engine cannot proceed, report something equivalent to:

```text
LOGIC_STALLED
```

This is valuable information.

It means either:

- the puzzle requires a logical rule not yet implemented;
- the current state contains insufficient information;
- the puzzle genuinely requires guessing;
- the board was parsed incorrectly;
- the board contains an error.

---

# 19. Optional exhaustive solver

A separate solver MAY eventually use:

- backtracking;
- constraint programming;
- SAT;
- SMT.

For example:

```python
solve_exhaustive(board)
```

This is useful for:

- validating a puzzle;
- determining whether it has zero, one, or multiple solutions;
- testing the logical engine;
- generating puzzles;
- verifying deductions;
- detecting whether a logical rule is incomplete.

But it must remain architecturally separate from:

```python
solve_logically()
```

and:

```python
next_hint()
```

The exhaustive solver knows WHAT must be true.

The logical engine must explain WHY it must be true.

---

# 20. Contradiction detection

The engine should detect invalid board states.

Examples:

A group contains more than 2 queens:

```text
CONTRADICTION
```

A group needs one more queen but has zero unknown candidates:

```text
CONTRADICTION
```

Two adjacent confirmed queens:

```text
CONTRADICTION
```

A deduction attempts:

```text
QUEEN -> EXCLUDED
```

or:

```text
EXCLUDED -> QUEEN
```

This should raise a clear error rather than silently overwrite state.

Also detect impossible cardinality states such as:

```text
queens_already_placed + unknown_candidates < 2
```

for any row, column, or region.

---

# 21. Testing philosophy

Every deduction rule MUST have unit tests.

For each rule test at least:

1. a board where the deduction applies;
2. a similar board where it does NOT apply;
3. boundary cases;
4. contradictions where relevant.

Example:

```python
def test_region_last_candidate_is_queen():
    ...
```

Expected:

```python
deduction.actions == [
    Action(L6C5, QUEEN)
]
```

And verify the reason:

```python
assert deduction.rule == "forced_remaining_cells"
```

Tests should verify not only the final action but also relevant structured premises.

This protects the explainability layer from regressions.

---

# 22. Deduction verification

A useful future debugging feature:

```python
verify_deduction(board, deduction)
```

An exhaustive solver can verify that every complete solution compatible with the current board also satisfies the proposed deduction.

For example:

```text
Current board has 27 possible complete solutions.

All 27 have L6C5 = QUEEN.

=> deduction is semantically valid.
```

IMPORTANT:

This verifies the deduction.

It does NOT constitute the explanation shown to the player.

The explanation must still come from the logical rule.

This separation is important:

```text
Logical engine:
"Here is a human-understandable proof."

Exhaustive verifier:
"I independently confirmed that the conclusion is always true."
```

---

# 23. Debug output

Provide a developer-friendly representation.

Example:

```text
RULE: forced_remaining_cells
SOURCE: region green
DIFFICULTY: 1

PREMISES:
- region requires 2 queens
- confirmed queens: L5C2
- excluded: L5C3 L5C4 L6C2 L6C3 ...

CANDIDATES:
- L6C5

CONCLUSION:
- L6C5 = QUEEN
```

For candidate-set deductions:

```text
RULE: common_neighbor_exclusion
SOURCE: row 4
DIFFICULTY: 2

CONSTRAINT:
- exactly 1 queen among {L4C7, L4C8}

TARGET:
- L5C7

PREMISES:
- L5C7 touches L4C7
- L5C7 touches L4C8

CONCLUSION:
- L5C7 = EXCLUDED
```

This will be extremely useful when implementing and debugging more complicated rules.

### Visual Debug Board

In addition to the detailed deduction debug output, provide a compact
human-readable Markdown representation of the current board.

The purpose of this view is to make the current board state immediately
readable during development and debugging.

Example:

```markdown
Color Region Legend

- [R] = 🔴 red
- [B] = 🔵 blue
- [V] = 🟢 green
- [J] = 🟡 yellow
- [P] = 🟣 violet
- [O] = 🟠 orange
- [M] = 🟤 brown
- [N] = ⚫ black
- [W] = ⚪ white
- [G] = 🩶 grey
- [I] = 🩵 indigo

| Line / Col | Col 1 | Col 2 | Col 3 | Col 4 | Col 5 | Col 6 | Col 7 | Col 8 | Col 9 | Col 10 | Col 11 | Col 12 |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| Line 01  | 👑 `[R]` | ❌ `[R]` | ❌ `[B]` | ❌ `[B]` | ❌ `[B]` | ❌ `[V]` | ❌ `[V]` | ❌ `[V]` | ❌ `[J]` | ❌ `[J]` | ❌ `[J]` | ❌ `[J]` |
| Line 02  | ❌ `[R]` | ❌ `[B]` | ❌ `[B]` | 🔵 `[B]` | 🔵 `[B]` | 🟢 `[V]` | 🟢 `[V]` | 🟢 `[V]` | 🟡 `[J]` | 🟡 `[J]` | 🟡 `[J]` | 🟡 `[J]` |
| Line 03  | ❌ `[P]` | 👑 `[P]` | ❌ `[P]` | ❌ `[B]` | 🔵 `[B]` | 🟢 `[V]` | 🟢 `[V]` | 🟢 `[V]` | 🟡 `[J]` | 🟡 `[J]` | 🟡 `[J]` | 🟡 `[J]` |
| Line 04  | ❌ `[O]` | ❌ `[P]` | ❌ `[P]` | ❌ `[P]` | 🟠 `[O]` | 🟠 `[O]` | 🟠 `[O]` | 🟠 `[O]` | 🟡 `[J]` | 🟡 `[J]` | 🟡 `[J]` | 🟡 `[J]` |
| Line 05  | ❌ `[M]` | ❌ `[M]` | 🟤 `[M]` | 🟤 `[M]` | 🟤 `[M]` | 👑 `[G]` | ❌ `[G]` | ❌ `[G]` | ❌ `[N]` | ❌ `[N]` | ❌ `[N]` | ❌ `[N]` |
| Line 06  | ❌ `[M]` | ❌ `[M]` | 🟤 `[M]` | 🟤 `[M]` | ❌ `[G]` | ❌ `[G]` | ❌ `[G]` | 🩶 `[G]` | ⚫ `[N]` | ⚫ `[N]` | ⚫ `[N]` | ⚫ `[N]` |
| Line 07  | ❌ `[M]` | ❌ `[M]` | 🟤 `[M]` | 🟤 `[M]` | 🟤 `[M]` | ❌ `[G]` | 🩶 `[G]` | 🩶 `[G]` | ⚫ `[N]` | ⚫ `[N]` | ⚫ `[N]` | ⚫ `[N]` |
| Line 08  | ❌ `[W]` | ❌ `[W]` | ⚪ `[W]` | ⚪ `[W]` | ⚪ `[W]` | ❌ `[G]` | ⚪ `[W]` | 👑 `[N]` | ❌ `[N]` | ❌ `[N]` | ❌ `[N]` | ❌ `[N]` |
| Line 09  | ❌ `[W]` | ❌ `[W]` | ⚪ `[W]` | ⚪ `[W]` | ⚪ `[W]` | ❌ `[W]` | ❌ `[N]` | ❌ `[N]` | ❌ `[N]` | 🩵 `[I]` | 🩵 `[I]` | 🩵 `[I]` |
| Line 10 | ❌ `[I]` | ❌ `[I]` | 🩵 `[I]` | 🩵 `[I]` | 🩵 `[I]` | ❌ `[I]` | 🩵 `[I]` | ❌ `[N]` | 🩵 `[I]` | 🩵 `[I]` | 🩵 `[I]` | 🩵 `[I]` |
| Line 11 | ❌ `[I]` | ❌ `[I]` | 🩵 `[I]` | 🩵 `[I]` | 🩵 `[I]` | ❌ `[I]` | 🩵 `[I]` | ❌ `[N]` | 🩵 `[I]` | 🩵 `[I]` | 🩵 `[I]` | 🩵 `[I]` |
| Line 12 | ❌ `[I]` | ❌ `[I]` | 🩵 `[I]` | 🩵 `[I]` | 🩵 `[I]` | ❌ `[I]` | 🩵 `[I]` | ❌ `[N]` | 🩵 `[I]` | 🩵 `[I]` | 🩵 `[I]` | 🩵 `[I]` |
```

### Rendering semantics

Each cell must visually expose both its logical state and its region.

Use:

```text
👑 [R] = confirmed queen belonging to region R
❌ [R] = excluded cell belonging to region R
🔴 [R] = unknown/candidate cell belonging to region R
```

For an UNKNOWN cell, use the visual emoji assigned to its region.

For example:

```text
🔴 [R]
🔵 [B]
🟢 [V]
🟣 [P]
```

For a QUEEN, always display:

```text
👑 [region]
```

For an EXCLUDED cell, always display:

```text
❌ [region]
```

This means the logical state takes visual priority over the region color,
while the `[region]` suffix preserves region information.

### Presentation layer only

This Markdown representation is a HUMAN-READABLE DEBUG VIEW only.

It is NOT the internal representation of the puzzle.

Region colors, letters and emojis belong exclusively to the presentation
layer.

Logical rules must operate on stable RegionId values and must never depend
on a region being visually red, blue, green, etc.

For example, internally:

```python
RegionId("region_1")
RegionId("region_2")
RegionId("region_3")
```

may be rendered as:

```text
region_1 -> 🔴 [R]
region_2 -> 🔵 [B]
region_3 -> 🟢 [V]
```

The mapping is purely cosmetic.

### Dynamic regions

Do not hard-code the number of regions.

Do not assume that every puzzle has exactly 12 regions or uses the same
colors.

The renderer should dynamically assign a distinct visual representation to
each RegionId present on the board.

The legend should therefore also be generated dynamically.

Example:

```text
Color Region Legend

[R] = 🔴 region_1
[B] = 🔵 region_2
[V] = 🟢 region_3
...
```

If there are more regions than convenient emoji colors, the textual region
identifier remains authoritative.

The visual representation must never affect puzzle logic.

### Queen regions per row

Add one final column to the visual debug table:

```text
Queen Region(s)
```

This column indicates the region(s) of the confirmed queen(s) currently
present in that row.

Example:

```markdown
| Line / Col | Col 1 | ... | Col 12 | Queen Region(s) |
| :--- | :---: | ... | :---: | :---: |
| Line 1 | 👑 `[R]` | ... | ❌ `[J]` | 🔴 `[R]` |
| Line 2 | ❌ `[R]` | ... | 🟡 `[J]` | — |
| Line 3 | ❌ `[P]` | ... | 🟡 `[J]` | 🟣 `[P]` |
| Line 5 | ❌ `[M]` | ... | ❌ `[N]` | 🩶 `[G]` |
```

If a row contains two confirmed queens from different regions, display both:

```text
🔴 [R]  🟢 [V]
```

If both queens belong to the same region, display that region twice only if
this is useful for debugging; otherwise the preferred compact representation is:

```text
🔴 [R] ×2
```

If the row currently contains no confirmed queen, display:

```text
—
```

The information must be derived dynamically from the current Board state.

Do not store it separately and do not infer it from deduction history.

The purpose of this column is to make it immediately visible which region
quota(s) are already represented by queens on each row.

### Debug renderer API

Provide a dedicated debug renderer.

Suggested API:

```python
render_board(board) -> str
```

Example:

```python
log.info("board", board=render_board(board))
```

should output the Markdown legend and grid.

Optionally also support:

```python
render_board(
    board,
    coordinates=True,
    legend=True
)
```

The renderer must derive the entire visual state directly from the Board.

It must not modify the Board.

### Separation from deduction history

The visual board and the logical reasoning history are two separate debug
tools.

`render_board(board)` answers:

> What does the board look like right now?

A separate future function such as:

```python
render_history(history)
```

may answer:

> How did the engine reach this state?

Do not mix deduction explanations into the visual board table.

This keeps the board compact and makes it useful as a quick visual snapshot
during development.

### Debug objective

During development, it should be possible to execute:

```python
log.info("board", board=render_board(board))
```

and immediately inspect:

1. the complete region layout;
2. confirmed queens;
3. excluded cells;
4. remaining candidate cells;
5. row and column coordinates.

The output should be sufficiently readable that a developer can visually
compare it with the original puzzle screenshot.

---

# 24. Future screenshot ingestion

Eventually the application should accept a screenshot of a puzzle.

This is NOT part of the first implementation.

Future pipeline:

```text
Screenshot
    ↓
Grid detection
    ↓
Region/color detection
    ↓
Queen/cross detection
    ↓
Normalized Board
    ↓
Deduction Engine
```

Keep screenshot parsing completely separate from puzzle reasoning.

The logical engine should only receive a normalized `Board`.

This makes it possible to test the engine without computer vision.

It also allows other frontends to construct boards manually or from other sources.

The screenshot parser may eventually need to detect:

- grid dimensions;
- cell boundaries;
- region colors;
- region membership;
- confirmed queens;
- excluded/crossed cells.

But none of this should affect the logical engine API.

---

# 25. Future UI

Potential interaction:

```text
[Take screenshot / Load screenshot]

        ↓

"Give me a hint"

        ↓

Hint level 1:
"Look at the green region."

        ↓

"More"

        ↓

Hint level 2:
"It already contains one queen..."

        ↓

"More"

        ↓

Hint level 3:
"Only L6C5 remains."

        ↓

"Show answer"

        ↓

Highlight L6C5
```

The UI should be able to highlight:

- source group;
- premise cells;
- candidate cells;
- conclusion cells.

Therefore deduction metadata must retain those concepts.

Avoid designing deduction objects around text output alone.

---

# 26. Non-goals for the initial implementation

Do NOT initially implement:

- screenshot recognition;
- GUI;
- OCR;
- puzzle generation;
- SAT solving;
- web application;
- exhaustive optimization.

First milestone:

> Given a `Board` constructed in Python, reliably return explainable elementary logical deductions.

Keep the first milestone small, clean, and heavily tested.

---

# 27. First implementation milestone

Implement:

## Data model

- `Cell`
- `CellState`
- `Board`
- Region IDs
- group abstraction if useful

## Board validation

- row queen counts;
- column queen counts;
- region queen counts;
- queen adjacency;
- impossible remaining candidate counts.

## Rules

1. queen adjacency exclusion;
2. completed group;
3. forced remaining cells.

## Engine

```python
find_deductions(board) -> list[Deduction]
next_hint(board) -> Deduction | None
```

## Applying deductions

```python
board.apply(deduction)
```

## Hint renderer

At least:

```python
render_hint(deduction, level=1)
render_hint(deduction, level=2)
render_hint(deduction, level=3)
render_hint(deduction, level=4)
```

## Logical solver

```python
solve_logically(board)
```

implemented ONLY by repeatedly applying `next_hint()`.

## Tests

Full unit tests for all of the above.

Do not start milestone 2 until milestone 1 is working and tested.

---

# 28. Second milestone — Candidate-set reasoning

After milestone 1 is fully tested, implement candidate-set reasoning.

The important abstraction is:

```python
QueenConstraint(
    cells={...},
    queen_count=N
)
```

Derive these constraints from rows, columns and regions.

Example:

```text
Row 4 requires one remaining queen.

Available candidates:
L4C7
L4C8

Derived constraint:

exactly 1 queen among {L4C7, L4C8}
```

Then implement deductions that can be made without knowing the exact queen positions.

First target:

> If a queen is guaranteed to occur somewhere in candidate set S, any cell incompatible with every possible queen position in S can be excluded.

Example:

```text
A B
 X

Exactly one of A/B is a queen.

X touches both A and B.

Therefore X cannot be a queen.
```

Then generalize carefully.

---

# 29. Third milestone — Advanced local constraint reasoning

Once residual candidate constraints work reliably, add interactions between
constraints and reasoning over locally valid multi-queen placements.

Milestone 3 builds on `QueenConstraint` introduced in Milestone 2.

The objective is not to introduce a separate solving mechanism. Advanced
reasoning must produce structured logical facts and deductions that can be
consumed by the existing hint engine and by Milestone 1 and 2 rules.

Targets include:

- row/region confinement;
- column/region confinement;
- overlapping cardinality constraints;
- subset and inclusion relationships between constraints;
- locally valid placements of multiple queens inside a constraint;
- facts shared by every locally valid placement;
- derived `QueenConstraint` instances;
- immediate compatibility between intersecting constraints;
- deductions produced by comparing or refining constraints.

## 29.1 Constraint inclusion and cardinality differences

Constraints may be compared algebraically when their candidate sets overlap
through inclusion.

For example:

    Constraint A:
    exactly 1 queen among {A, B}

    Constraint B:
    exactly 1 queen among {A, B, C}

    Therefore:
    C = EXCLUDED

Likewise:

    Constraint A:
    exactly 2 queens among {A, B, C}

    Constraint B:
    exactly 2 queens among {A, B, C, D}

    Therefore:
    D = EXCLUDED

And:

    Constraint A:
    exactly 1 queen among {A, B}

    Constraint B:
    exactly 2 queens among {A, B, C}

    Therefore:
    C = QUEEN

More generally, if:

    A.cells ⊆ B.cells

then the cardinality of `B.cells - A.cells` is:

    B.queen_count - A.queen_count

provided the compared constraints are valid and the relationship directly
supports that conclusion.

This may itself produce another `QueenConstraint` rather than an immediate
cell action.

For example:

    A = exactly 1 queen among {A, B}
    B = exactly 2 queens among {A, B, C, D}

    Therefore:

    exactly 1 queen among {C, D}

Constraint interaction should therefore be capable of producing reusable
logical facts, not only immediate QUEEN or EXCLUDED actions.

## 29.2 Local valid placements

Some deductions depend on the possible arrangements of multiple queens inside
a small residual constraint.

Given:

    QueenConstraint(cells=C, queen_count=k)

the hint engine may enumerate the locally valid placements:

    P ⊆ C
    |P| = k

subject to immediately applicable puzzle constraints.

At minimum:

- queens inside the placement may not touch;
- existing queens and exclusions must be respected;
- the source constraint's residual cardinality must be respected.

Local placement generation must be deterministic.

This is local constraint reasoning, not global search.

It is valid to ask:

    In which ways can the remaining queens fit inside this constraint?

It is not valid to ask:

    If this cell were a queen, can the entire puzzle eventually be solved?

## 29.3 Facts shared by every local placement

Let `P` be the complete set of locally valid placements for a constraint.

If a candidate appears in every placement:

    for every p in P:
        cell in p

then:

    cell = QUEEN

If a candidate appears in no placement:

    for every p in P:
        cell not in p

then:

    cell = EXCLUDED

An external unknown cell may also be excluded if it necessarily touches a
queen regardless of which local placement is correct:

    for every p in P:
        some queen in p touches cell

therefore:

    cell = EXCLUDED

These are generic placement deductions.

Do not create shape-specific rules when the same deduction can be expressed
through this generic reasoning.

## 29.4 Derived subconstraints

Local placements may imply a stable queen cardinality for a subset of cells.

Given a subset `S`, if:

    for every placement p:
        |p ∩ S| = n

then the engine may derive:

    QueenConstraint(S, n)

For example, if the valid placements are:

    {A, C}
    {A, D}
    {B, C}
    {B, D}

then:

    exactly 1 queen among {A, B}
    exactly 1 queen among {C, D}

These derived `QueenConstraint` instances are first-class logical facts.

They may be consumed by later rules exactly like residual row, column, or
region constraints, provided their provenance is preserved.

This is particularly important because existing Milestone 2 rules may already
know how to use the derived constraint.

For example:

    derived QueenConstraint({A, B}, 1)
        ↓
    COMMON_NEIGHBOR_EXCLUSION
        ↓
    cells touching both A and B are excluded

Prefer deriving reusable structured knowledge over duplicating elementary
consequences in advanced rules.

## 29.5 Constraint partition and capacity reasoning

Local placement analysis may reveal that different parts of a candidate set
have forced cardinalities.

For example, suppose a region still needs two queens and its candidates consist
of:

    one isolated candidate A

    and

    two mutually touching candidates {B, C}

Because `B` and `C` cannot both contain queens:

    {B, C} contains at most 1 queen

The region still requires two queens, therefore:

    A = QUEEN
    exactly 1 queen among {B, C}

This should preferably emerge from generic local-placement and derived-
constraint reasoning rather than from a special rule for this particular
shape.

## 29.6 Immediate cross-constraint compatibility

A placement that is valid inside one constraint may be rejected when it
directly violates another intersecting structured constraint.

Allowed immediate conflicts include:

- queen adjacency;
- too many queens in a row;
- too many queens in a column;
- too many queens in a region;
- insufficient remaining capacity in an intersecting constraint;
- a directly contradictory cardinality relationship.

For example:

    A region needs two queens.

    If candidate A were part of a local placement,
    the only possible second regional queen would be B.

    A and B belong to the same row.

    That row cannot contain both queens.

    Therefore that local placement is invalid.

This remains local constraint propagation.

Do not recursively explore future deductions in order to decide whether a
local placement is valid.

## 29.7 Interaction with earlier milestones

Milestone 3 complements rather than replaces Milestones 1 and 2.

A normal solving chain may look like:

    local placement analysis
        ↓
    derived QueenConstraint
        ↓
    COMMON_NEIGHBOR_EXCLUSION
        ↓
    cell exclusions
        ↓
    FORCED_REMAINING_CELLS
        ↓
    queen placement
        ↓
    QUEEN_ADJACENCY

Advanced rules should not duplicate elementary rules when they can instead
produce information that makes those rules applicable.

The hint engine remains the single source of logical solving intelligence.

---

# 30. Constraint normalization and lifecycle

`QueenConstraint` is the normalized cardinality representation used by the
logical engine.

Conceptually:

    QueenConstraint(
        cells=frozenset({...}),
        queen_count=N,
        source=...,
    )

represents:

    exactly N queens among these candidate cells

Residual row, column, and region constraints are examples of
`QueenConstraint`.

Milestone 3 may additionally derive `QueenConstraint` instances from other
structured constraints or local placement analysis.

A confirmed queen or exclusion may simplify the effective residual constraint.

For example:

    exactly 1 queen among {A, B, C}

    A = QUEEN

implies:

    exactly 0 queens among {B, C}

therefore:

    B = EXCLUDED
    C = EXCLUDED

Likewise:

    exactly 1 queen among {A, B, C}

    A = EXCLUDED

reduces to:

    exactly 1 queen among {B, C}

Constraint normalization and simplification must remain deterministic and must
preserve enough provenance for the resulting deduction to be explained.

Do not allow normalization to become an opaque theorem prover.

---

# 31. Provenance for derived constraints and placements

Every derived constraint and advanced deduction must retain structured
information describing where it came from.

Evidence must be captured when the deduction is created.

A renderer must not need to rerun the solving algorithm against the current
board in order to reconstruct the explanation.

Depending on the deduction, structured provenance may include:

- source `QueenConstraint` instances;
- original row, column, or region premises;
- compared constraints;
- candidate cells;
- locally valid placements;
- locally rejected placements;
- the immediate structured reason a placement was rejected;
- adjacency relationships;
- subset or inclusion relationships;
- derived subconstraints;
- resulting actions.

For example:

    Row 4 still needs one queen.

    Its only available cells are L4C7 and L4C8.

    Therefore:

    exactly one queen is in {L4C7, L4C8}.

This may be represented as:

    QueenConstraint({L4C7, L4C8}, 1)

with provenance pointing back to the residual row constraint.

A later deduction may then state:

    L5C7 touches both possible queen positions.

    Therefore L5C7 cannot contain a queen.

The proof chain is therefore:

    source constraint
        ↓
    derived QueenConstraint
        ↓
    named logical rule
        ↓
    deduction

rather than:

    L5C7 is impossible.

Derived constraints are reusable logical facts, but their derivation must never
become invisible.

---

# 32. Local logical reasoning vs. search

A critical project requirement is that human-facing hints are derived from
logical evidence rather than extracted from a solved board.

The hint engine may enumerate finite local queen placements inside a row,
column, region, or derived `QueenConstraint` when those placements are used
directly as structured evidence for a deduction.

Local placement reasoning may:

- compare structured constraints;
- enumerate placements within a local constraint;
- apply immediate adjacency and cardinality restrictions;
- inspect immediately intersecting row, column, region, or derived constraints;
- reject a placement because it directly violates one of those constraints;
- derive new `QueenConstraint` facts;
- produce queens or exclusions that hold across all valid local placements.

This is considered logical constraint propagation, not search.

The human-facing hint engine must NOT:

1. assume a candidate and recursively run the hint engine;
2. assume a candidate and call `solve_logically()`;
3. explore arbitrary chains of hypothetical future deductions;
4. perform global backtracking;
5. enumerate complete board solutions;
6. use SAT/SMT or equivalent global solving to generate a hint;
7. inspect a known solution and invent an explanation afterward.

In particular, do NOT implement hints by:

    solve the puzzle exhaustively
        ↓
    inspect the solution
        ↓
    select a correct cell
        ↓
    invent a plausible explanation

Instead:

    structured premises
        ↓
    named logical rule
        ↓
    structured deduction

A deduction must be justified by bounded local evidence captured in its
provenance.

An exhaustive solver may eventually exist as an independent validation tool,
but it must not secretly generate human-facing hints.

---

# 33. Solver philosophy

The desired relationship is:

```text
                ┌───────────────┐
                │ Current Board │
                └───────┬───────┘
                        │
                        ▼
                ┌───────────────┐
                │ Hint Engine   │
                └───────┬───────┘
                        │
                        ▼
                  Deduction
                    /    \
                   /      \
                  ▼        ▼
           Human Hint   Logical Solver
```

The human player receives one deduction progressively.

The logical solver simply applies the deduction immediately and asks for another one.

Therefore:

> If `solve_logically()` solves a puzzle, every step of that solution should be reproducible as a human-facing hint.

Ideally, the solver can output the complete reasoning history.

Example:

```text
Step 1:
L6C5 = QUEEN
Reason: forced remaining cell in Green region

Step 2:
L5C4 = EXCLUDED
Reason: adjacent to L6C5

Step 3:
...

Puzzle solved in 37 logical deductions.
Maximum difficulty: 3
```

This reasoning history may eventually be useful for rating puzzle difficulty.

---

# 34. Puzzle difficulty analysis

Future optional feature:

Because every deduction has a difficulty rating, a logically solved puzzle can receive metrics such as:

```python
LogicalSolveStats(
    deductions=37,
    max_difficulty=3,
    average_difficulty=1.7,
    advanced_deductions=4
)
```

This could eventually be useful for:

- comparing puzzles;
- generating puzzles;
- estimating difficulty;
- explaining why the engine became stuck.

This is optional and should not complicate the initial implementation.

---

# 35. Guiding principle

When implementing a new rule, ask:

> "Could a human explain this deduction without knowing the final solution?"

If yes, it belongs in the logical hint engine.

If the only explanation is:

> "I searched all complete solutions and they all agree."

then it belongs in the exhaustive verifier/solver, not the hint engine.

---

# 36. Ultimate objective

The project should eventually support:

```python
board = parse_screenshot("queens.png")

hint = engine.next_hint(board)

log.info("hint", hint=render_hint(hint, level=1))
```

Example output:

```text
Look at the green region.
```

Then:

```python
log.info("hint", hint=render_hint(hint, level=2))
```

Example:

```text
It needs two queens and already contains one.
How many possible cells remain?
```

Then:

```python
log.info("hint", hint=render_hint(hint, level=3))
```

Example:

```text
Only L6C5 remains available for the second queen.
```

And finally:

```python
log.info("hint", hint=render_hint(hint, level=4))
```

Example:

```text
Place a queen at L6C5.
```

If desired:

```python
result = solve_logically(board)
```

should solve the puzzle by doing nothing more intelligent than repeatedly applying the exact same deductions available to the hint system.

---

# 37. Implementation instruction for Codex

Do NOT attempt to implement the entire specification at once.

Start with MILESTONE 1 ONLY.

Before writing code:

1. inspect the repository;
2. propose a minimal architecture consistent with this specification;
3. identify the public APIs;
4. identify the tests needed.

Then implement milestone 1.

Milestone 1 consists only of:

- board/data model;
- validation;
- adjacency deduction;
- completed-group deduction;
- forced-remaining-cells deduction;
- structured `Deduction` objects;
- deduction application;
- hint rendering levels;
- `find_deductions()`;
- `next_hint()`;
- logical solver based exclusively on repeated hints;
- comprehensive unit tests.

Do NOT implement yet:

- candidate-set reasoning;
- advanced constraint algebra;
- screenshot parsing;
- exhaustive solving;
- GUI.

Once milestone 1 passes all tests, stop and report:

- architecture created;
- APIs;
- implemented rules;
- tests;
- known limitations;
- recommended next step.

The next development step will then be milestone 2: candidate-set reasoning.

---

# 38. Core project rule

The most important architectural rule in the entire project is:

> THE HINT ENGINE IS THE SOLVER.

More precisely:

The logical solver must have no puzzle-solving intelligence of its own.

It simply asks the hint engine for a deduction, applies it, and repeats.

Conceptually:

```python
while not board.is_solved():

    deduction = hint_engine.next_hint(board)

    if deduction is None:
        return LOGIC_STALLED

    board.apply(deduction)
```

This guarantees that anything solved automatically by the logical solver can also be explained step-by-step to a human player.

An exhaustive solver may exist separately for validation and testing, but it must never become the hidden source of human-facing hints.
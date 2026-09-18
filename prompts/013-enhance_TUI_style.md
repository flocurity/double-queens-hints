Extend the colored debug/TUI board with symmetric row and column queen summaries.
This is a presentation-only change. Do not modify Board state, deductions, hint/proof rendering, solver behavior, ranking, or reasoning logic.
Keep the existing Queen(s) summary on the right of each board row, but change how multiple queens from the same region are represented:
- render one region badge per queen;
- do not collapse repeated regions into ×2 or any other multiplier;
- preserve the queens' left-to-right board order;
- use the same region badge representation already used by the colored renderer: visible region label/glyph with its matching region background.
For example, if a row contains two queens from region A, render:

> A  A

rather than:

> A ×2

This makes the row summary consistent with the new column summary described below.
Add the column-oriented counterpart below the grid.
After the last board row:
- render a plain horizontal separator spanning exactly the colored grid width;
- do not give the separator a region background;
- below it, render exactly two queen-summary rows, aligned with the board's 3-column cells.
For each column:
- find the queens currently present in that column;
- preserve their top-to-bottom board order;
- render each queen's region as a 3-column badge in the corresponding summary slot;
- use the same visible region label/glyph and matching region background as the row Queen(s) summary;
- a column with no queens leaves both slots blank;
- a column with one queen fills the first slot and leaves the second blank;
- a column with two queens fills both slots;
- do not collapse identical regions into a multiplier.
The row and column summaries should therefore be deliberately symmetric:
- right side: queens in each row, ordered left to right;
- bottom side: queens in each column, ordered top to bottom.
The region label must remain visible inside every occupied badge. The background provides fast visual recognition, while the label preserves the information when colors are unavailable, difficult to distinguish, or the output is inspected as plain text.
Empty summary slots and the horizontal separator must have no background color.
Preserve the existing three-terminal-column cell geometry, checkerboard region backgrounds, deterministic palette behavior, text fallback, and compact row/column labels.
Update/add focused renderer tests for:
- two queens from different regions in one row;
- two queens from the same region in one row, verifying that two badges are rendered and no ×2 appears;
- columns containing zero, one, and two queens;
- two queens from the same region in one column;
- left-to-right ordering for row summaries;
- top-to-bottom ordering for column summaries;
- exact 3-column alignment between bottom badges and board columns;
- absence of background styling on empty bottom slots and the separator;
- preservation of board state and deterministic rendering;
- text fallback remaining readable.
Run the focused renderer tests and then the full test suite. Do not change unrelated production code. Do not commit or tag unless explicitly requested.


##### then
Small visual cleanup for the new bottom column-queen summary:

- Remove the horizontal separator line entirely and replace it with one plain empty line between the board and the first bottom summary row.
- Add one plain empty line between the first and second bottom queen-summary rows.
- Do not add horizontal spacing between columns: each badge must remain exactly aligned with its corresponding 3-column board cell.
- Empty lines must contain no ANSI background styling.
- Keep everything else unchanged.


##### and

One final palette constraint: when assigning region styles, avoid assigning visually similar background colors to regions that are orthogonally adjacent on the board.
Preserve the existing deterministic/randomized palette behavior, but make palette assignment adjacency-aware: neighboring regions should receive sufficiently distinct base colors whenever the available palette permits it.
This is presentation-only. Do not change RegionIds or board/reasoning semantics. The checkerboard darkening remains a per-cell variation of the already assigned region color.
Add focused tests proving that adjacent regions do not receive the known similar color pairs, while seeded/randomized contexts remain deterministic.
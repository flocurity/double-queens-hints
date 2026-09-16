Update the board renderer to use a compact terminal-oriented format instead of the current Markdown-style table.

I attached a screenshot showing the exact visual direction I want.

Before modifying files:

1. inspect the current board rendering implementation;
2. inspect all call sites of `render_board`;
3. identify tests that depend on its textual output;
4. understand and preserve the existing Unicode / emoji width handling and `DebugRenderContext` palette behavior;
5. briefly summarize the smallest change you intend to make.

## Goal

The current board renderer produces a Markdown-style table with verbose headers, separators, pipes around every cell, and labels such as `Line 01` / `Col 1`.

That format is useful as Markdown, but it is unnecessarily wide and visually noisy in terminal debug traces.

I want the board to look approximately like the following board:

    1 2 3 4 5 6 7 8 9 |Queen(s)
01 🟢🟢🟢🩶🩶🩶🩵🩵🩵|-
02 🟢🟢❌🩶❌🩶❌🩵🩵|-
03 🔴🟢🟢🩶❌❌❌🩵🩵|-
04 ❌❌❌🟢❌👑❌🩵🟣|⚪
05 ❌👑❌❌❌❌❌🟣🟣|🟤
06 ❌❌❌❌👑❌🟣🟣🟣|🟤
07 🔴❌👑❌❌❌🟣🟣🟡|🔴
08 🟠❌❌❌👑❌❌🟡🟡|🟠
09 🟠❌👑❌❌❌🟡🟡🟡|⚪

The actual glyphs/colors above are illustrative only. Continue using the existing board state symbols and randomized region palette.

## Formatting requirements

For a 9×9 board:

- column headers should simply be `1 2 3 4 5 6 7 8 9`;
- row headers should be `01` through `09`;
- remove `Line`;
- remove `Col`;
- remove the `Line / Col` header;
- remove the Markdown alignment row;
- remove Markdown cell separators;
- do not put spaces between board cell glyphs;
- keep one `|` between the grid and the per-row region metadata;
- rename the metadata header `QueenRegion(s)` in `Queen(s)`;
- keep the existing region-summary semantics on the right;
- keep `-` for rows without queen-region metadata if that is the current representation.

The grid itself should visually behave as one compact block.

## Alignment

Emoji / Unicode terminal width is important.

Do NOT achieve the compact layout by assuming that every Python character has width 1.

Reuse the existing glyph-width / terminal-profile handling so that:

- emoji cells remain aligned;
- textual/non-emoji fallback rendering remains aligned;
- custom glyph widths continue to work;
- `DebugRenderContext` continues to work;
- randomized region palettes continue to use exactly the same mapping in boards and hints.

The attached screenshot is the desired terminal appearance.

## Board sizes

Do not hardcode the renderer specifically to 9×9 unless the existing Board API itself guarantees that size.

For dimensions below 10, preserve the compact style shown above. you can remove spaces in column header if needed (ex: 1 2 3 4 5 6 7 8 910111213)

If dimensions can exceed 9, adapt the coordinate/header width only as much as necessary to remain unambiguous and aligned. Do not make the common 9×9 rendering wider merely to accommodate hypothetical larger boards.

The 9×9 case is the primary UX target.

## Scope

This is a rendering change only.

Do not change:

- Board semantics;
- solving logic;
- deduction generation or ranking;
- hint semantics;
- region palette assignment;
- `DebugRenderContext` semantics;
- structlog configuration;
- `MultilineConsoleRenderer`;
- `@debug_boards` tracing semantics;
- step numbering;
- trace suspension;
- replay behavior.

Do not introduce a second renderer or a `format="compact"` / `format="markdown"` option unless inspection shows that the Markdown representation is still genuinely required by another supported use case.

Prefer replacing unnecessary formatting complexity over maintaining two formats solely for backwards compatibility with cosmetic tests.

## Tests

Update renderer-specific tests to assert the new behavior.

Tests should cover the meaningful formatting contract, including:

- compact column header;
- compact row labels;
- absence of Markdown separator rows;
- absence of `Line` / `Col`;
- no separators or spaces between grid cells;
- one separator before `QueenRegion(s)` metadata;
- correct region metadata;
- emoji alignment;
- non-emoji fallback alignment;
- existing palette/context behavior remains unchanged.

Avoid brittle assertions about irrelevant whitespace where possible, but exact-line assertions are appropriate where they define the compact renderer contract.

Run:

- the focused renderer/debug tests;
- `tests/test_known_games.py`;
- the complete test suite;
- `git diff --check`.

Also run `tests/test_known_games.py -s` and visually inspect at least one full rendered board to confirm that the result matches the attached screenshot closely.

Report:

- the design chosen;
- files changed;
- tests changed/added;
- final test counts;
- any compatibility behavior that had to be preserved.

Keep the change narrowly scoped.
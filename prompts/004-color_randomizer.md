Read AGENTS.md and inspect the current implementation of:

- double_queens/hints/debug.py
- double_queens/hints/renderer.py
- double_queens/log.py
- the debug_boards test helper
- render_hint() and its related tests

This is a SMALL DEBUG/RENDERING ENHANCEMENT ONLY.
Do not implement Milestone 2 or change solving logic.

Before modifying files:

1. explain how region colors/glyphs are currently assigned in debug.py;
2. explain how terminal emoji support is detected;
3. identify the smallest design that lets render_board() and debug hint rendering
   share the exact same randomized region palette;
4. identify the tests that should be added or updated.

Then implement the following.

GOAL 1 — Randomized debug region palette
-----------------------------------------

Currently debug region colors/glyphs are assigned in a fixed order.

For emoji-capable terminal debug rendering, randomize the mapping between
RegionId values and the available region color glyphs.

Requirements:

- Randomization must happen at an appropriate stable scope.
- Once a palette has been selected, the mapping MUST remain stable for every
  rendering that belongs to that same debug context.
- Rendering the board twice must not randomly change its colors between calls.
- Rendering hints for that board must use exactly the same RegionId -> glyph
  mapping as the board.
- Do not use global mutable state whose behavior depends unpredictably on test
  execution order.
- Tests must be deterministic. Provide an explicit seed, RNG, palette/context,
  or equivalent injection mechanism so tests never depend on random output.
- Production/debug use may choose a random palette automatically.
- Do not modify Board or logical solving structures merely to store presentation
  state.

The design should make the currently selected mapping accessible rather than
hiding it inside render_board().

Prefer a small explicit presentation object/context if appropriate, e.g. a
concept similar to:

    DebugPalette / RegionPalette / DebugRenderContext

but inspect the existing code first and choose the smallest design that fits it.

The object/API should be able to answer:

    glyph_for(region_id)

and render_board() must use that same mapping rather than independently
recomputing region colors.

Do not duplicate the list of region glyphs or the mapping algorithm between
board rendering and hint rendering.


GOAL 2 — Human-readable hints use the board's region color
----------------------------------------------------------

The debug test decorator currently logs all four render_hint() levels in
human-readable form.

When terminal capabilities allow the emoji/color debug board, replace
human-facing region identifiers such as:

    region_0

with the glyph currently representing that region on the rendered board.

For example, if the randomized palette for the current debug context maps:

    region_0 -> 🔵

then hints should read conceptually:

    level 1: Look at region 🔵.
    level 2: Region 🔵 requires 2 queens and already has 1. ...
    level 3: Only L1C4 remains available in region 🔵; ...

The glyph MUST correspond to the palette actually used to render that board.
It must continue to correspond after palette randomization.

Do not perform string replacement on the final rendered hint text.
The region display value must be supplied structurally while rendering the hint.

Keep normal render_hint() behavior independent from terminal/debug rendering.
Calling render_hint() normally should still be able to produce ordinary
human-readable region names.

Add the smallest optional rendering hook/context necessary so debug rendering
can request the colored region representation without coupling logical
Deduction objects to terminal presentation.

Level 4 usually contains only explicit cell actions and therefore does not need
a region glyph unless the hint naturally mentions a region.


GOAL 3 — Terminal fallback
--------------------------

Respect the existing terminal capability/profile logic in debug.py.

If the terminal supports the emoji region glyphs:

- render the board using the randomized palette;
- render region references in logged hints using glyphs from that SAME palette.

If the terminal does not support them:

- preserve the existing non-emoji/fallback board behavior;
- preserve readable textual region identifiers in hints;
- do not emit unsupported emoji glyphs merely because hint logging requested
  them.

Do not create a second independent terminal-capability detection mechanism if
one already exists. Reuse/refactor the existing mechanism.


GOAL 4 — Palette observability
------------------------------

Make it possible during debugging to determine which palette/mapping is active.

Do NOT spam one log line per region.

Prefer either:

- a compact structured representation exposed by the palette/context object; or
- one optional debug log when a new randomized palette/context is created.

For example, conceptually:

    region_palette
        region_0=🔵
        region_1=🟠
        region_2=🟢
        ...

The exact API/log formatting should fit the existing logging infrastructure.

If logging the palette, use get_logger()/structured logging according to
AGENTS.md. Do not use print().

Do not modify MultilineConsoleRenderer or the core logging infrastructure for
this feature unless absolutely necessary. Existing multiline values should
already be sufficient.


IMPORTANT LIFETIME REQUIREMENT
------------------------------

Think carefully about palette lifetime.

A palette is presentation state, not puzzle state.

For a single debug trace, the user must never see:

    board: region_0 = 🔵
    hint:  region_0 = 🟠

Likewise, repeated before/after board renders in one traced test must preserve
the same region colors so visual comparison remains useful.

If @debug_boards is the owner of the debug rendering session, it is acceptable
and likely desirable for it to create one render context/palette at the start
of the traced test and pass/reuse it for every board and hint rendered during
that trace.

Different traced tests/debug sessions may receive different randomized
palettes.

Do not make palette randomization occur independently inside each
render_board() call.


TESTING
-------

Add focused tests proving:

1. a seeded/fixed palette produces deterministic RegionId -> glyph mappings;
2. different seeds/palette shuffles can produce different mappings;
3. a palette never assigns the same glyph twice while unused glyphs remain;
4. repeated board rendering with the same context preserves colors;
5. board rendering and hint rendering use exactly the same glyph for a region;
6. all hint levels that mention a region use the selected glyph;
7. level 4 remains correct;
8. non-emoji terminal fallback does not emit region emoji glyphs;
9. existing render_board() behavior remains compatible unless explicitly
   exercising randomized debug rendering;
10. existing tests continue to pass.

Avoid tests that rely on the probability of two random shuffles being
different. Use explicit seeds or injected deterministic palettes.

Do not weaken semantic hint tests just to accommodate randomized presentation.
Tests of ordinary render_hint() should remain deterministic and textual;
add separate tests for debug/palette-aware rendering.


SCOPE / ARCHITECTURE
--------------------

This is presentation/debug infrastructure only.

Do NOT:

- change Board semantics;
- change Deduction semantics unless an existing generic presentation hook
  genuinely requires a minimal adjustment;
- change rule discovery;
- change next_hint(), best_deduction(), or solve_logically();
- implement candidate-set reasoning or Milestone 2;
- add guessing/backtracking;
- hard-code region_0 or any specific game;
- duplicate region palette definitions;
- make logical code depend on terminal support;
- introduce unrelated refactors.

Follow AGENTS.md logging conventions.

When finished:

1. run the complete test suite;
2. summarize the design and palette lifetime;
3. show the public/internal APIs added or changed;
4. show one example where a randomized board region glyph is reused in the
   corresponding human-readable hint;
5. explain the non-emoji fallback;
6. report all files changed.

STOP after this rendering/debug enhancement.

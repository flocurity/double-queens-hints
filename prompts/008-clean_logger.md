Make one focused cleanup/improvement to the test-only @debug_boards tracing helper.

Do not modify production solving logic, deduction logic, Board behavior,
hint semantics, or logging infrastructure.

Context
-------

The helper is now useful for inspecting the pedagogical solving path, but a
long real-game replay is still unnecessarily noisy.

Three related issues remain:

1. Step information is currently logged manually by test_known_games.py:

       log.info("step", step=len(history), ..., deduction=...)

   This belongs naturally to @debug_boards because the decorator already
   observes the deductions actually passed to Board.apply().

2. For sequential applications, we commonly emit:

       board after application N
       board before application N+1

   even when both renders are identical.

3. test_known_game_001_logical_replay performs a 32-step solve and then replays
   the same 32 deductions to verify deterministic replay. Because @debug_boards
   wraps Board.apply() for the whole test, both passes are currently traced:

       32 useful solving applications
       + 32 validation replay applications

   The second pass is valuable as a test but not useful in the pedagogical
   debug trace.

Before editing
--------------

Inspect:
- tests/debug_boards.py
- tests/test_debug_boards.py
- tests/test_known_games.py

Then briefly explain the smallest design you propose for solving these three
issues.

Prefer a small generic tracing mechanism over anything specific to
"known games", "replay", or milestone 2.

Do not introduce production APIs for this.

1. Structured step numbers
--------------------------

Move application step tracking into @debug_boards.

A deduction actually passed to Board.apply() should receive a monotonically
increasing step number scoped to one decorated test execution.

The step should be available as a structured field on the useful trace events,
especially:

    deduction used   step=N ...
    hints            step=N ...

and on application board logs where appropriate.

Do NOT duplicate the deduction by adding a separate "step" log event if
"deduction used" can carry the step itself.

Candidate deductions emitted by:

    @debug_boards(log_all_deductions=True)

are discovery candidates, not application steps. Do not assign application
step numbers to "deduction created" events.

Decide and document whether rejected Board.apply() attempts consume a step.
Prefer a simple, consistent definition such as "step = observed apply attempt".

After this works, remove the now-redundant manual per-step diagnostic log from
test_known_games.py.

2. Avoid redundant before/after board renders
---------------------------------------------

Do not blindly remove all "before application" logs.

For each Board instance, keep track of the last board state/render that the
decorator emitted.

Before Board.apply():

- if the current board is already identical to the last emitted state for that
  same Board, do not emit another identical "before application" board;
- if this is the first relevant state, or the board changed outside the traced
  apply flow, emit the before board.

After a successful application, continue emitting the resulting board.

Multiple Board instances inside one decorated test must be tracked
independently.

Rejected applications must remain diagnosable, and the existing atomicity
assertion must remain unchanged.

Do not use assumptions such as "after step N is always before step N+1";
base suppression on the observable state of that specific Board.

3. Allow test-only tracing to be temporarily suspended
------------------------------------------------------

Add the smallest generic mechanism that allows code inside a decorated test to
temporarily execute without emitting @debug_boards tracing.

Intended usage in test_known_games.py is conceptually:

    with <trace suspended>:
        replay_board = make_known_game_001()
        for deduction in history:
            assert deduction == next_hint(replay_board)
            replay_board.apply(deduction)

The deterministic replay and all its assertions MUST still execute normally.
Only debug tracing should be suppressed.

Requirements:

- generic test/debug concept; do not call the API "ignore_replay" or make it
  know anything about known games;
- scoped/context-managed behavior preferred;
- tracing must always be restored, including when the block raises;
- no production behavior changes;
- avoid global state leaking between tests;
- nested use should behave sensibly if the implementation naturally permits it.

If exposing a suspension API would require disproportionate complexity,
stop and explain the simpler alternative before implementing it.

Expected real-game result
-------------------------

For the 32-deduction solve in test_known_game_001_logical_replay, the useful
trace should conceptually become:

    initial board

    deduction used step=1
    hints step=1
    board after application step=1

    deduction used step=2
    hints step=2
    board after application step=2

    ...

    deduction used step=32
    hints step=32
    board after application step=32

    solved

The subsequent deterministic 32-deduction validation replay should still run
and pass but should not emit another 32 deduction/hint/board trace blocks.

Keep the existing default vs verbose semantics:

    @debug_boards
        -> detailed logging only for deductions actually applied

    @debug_boards(log_all_deductions=True)
        -> detailed logging for every created candidate deduction
           without duplicating applied deduction details

Tests
-----

Add focused tests proving at least:

- step numbering starts at 1 and is scoped to one decorated execution;
- applied deduction and its hints share the same step;
- candidate "deduction created" logs do not receive application steps;
- sequential successful applications do not duplicate an unchanged
  after/before board;
- an externally changed board causes a new before board to be emitted;
- multiple Board instances are tracked independently;
- rejected applications remain observable and atomic;
- tracing suspension suppresses decorator trace output inside its scope;
- tracing is restored after leaving the suspension scope;
- deterministic replay assertions in test_known_games.py still execute;
- default and log_all_deductions=True behavior remain intact;
- shared DebugRenderContext / region palette behavior remains intact.

Keep tests focused on behavior rather than console formatting.

Run:
- the focused debug helper tests;
- tests/test_known_games.py;
- the complete test suite;
- git diff --check.

Report:
- the design chosen;
- files changed;
- final test counts;
- for test_known_games.py, how many "deduction used" events are now emitted
  during the 32-step logical replay (expected: 32, not 64).

Keep the change narrowly scoped. Do not refactor unrelated logging or solving
code.
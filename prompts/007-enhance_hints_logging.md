Make a small, focused improvement to the existing @debug_boards test helper.

Do not modify solving logic, deduction logic, hint rendering, logging
infrastructure, or production behavior.

Goal
----

The decorator currently logs every Deduction when Deduction.__post_init__ runs.
This has become extremely noisy because deduction discovery creates many
candidate deductions, most of which are never selected/applied.

I want two debug modes:

1. Default:
   @debug_boards

   Log the detailed deduction + progressive hints only when that deduction is
   actually passed to Board.apply().

   In other words, the normal trace should describe the path actually chosen
   by the solver:

       board before application
       deduction used
       hint levels 1-4
       board after application

   Do not emit the current detailed "deduction created" + hints from
   traced_post_init in this mode.

2. Verbose candidate mode:
   @debug_boards(log_all_deductions=True)

   Preserve the current behavior of traced_post_init:
   log every created candidate deduction and its hint levels.

   In this mode, do NOT additionally duplicate the same detailed deduction/hint
   logging in traced_apply. The existing board before/after application logs
   should remain.

Implementation requirements
---------------------------

- Preserve backwards compatibility with existing bare usage:

      @debug_boards

- Also support:

      @debug_boards(log_all_deductions=True)

- Avoid duplicating the code that renders/logs a deduction and its four hint
  levels. Extract a small local/helper function if appropriate and reuse it
  from traced_post_init or traced_apply.

- Continue using the same DebugRenderContext so region glyphs in hints match
  the board.

- Preserve the existing handling for intentionally malformed test deductions
  whose hints cannot be rendered. Do not broaden exception handling.

- In default mode, the detailed deduction log should correspond to the
  deduction actually supplied to Board.apply(), not merely one created during
  discovery.

- Rejected Board.apply() attempts should still be observable and existing
  atomicity checks must remain unchanged.

- Keep all existing board lifecycle logs and palette behavior.

Tests
-----

Add focused tests proving:

- existing @debug_boards usage still works;
- default mode does not log every candidate deduction;
- default mode logs the deduction actually passed to Board.apply();
- log_all_deductions=True logs created candidate deductions;
- verbose mode does not duplicate the applied deduction's detailed hint log;
- progressive hints still use the same region palette as the board;
- existing malformed-deduction / rejected-application tests still pass.

Run the complete test suite after the change.

Before editing, briefly inspect the current decorator implementation and state
your intended change. Keep this scoped to the debug helper only.

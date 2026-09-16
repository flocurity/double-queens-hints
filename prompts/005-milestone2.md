Read SPEC.md and AGENTS.md in full.

Milestone 1 is complete and its tests are passing.

Implement MILESTONE 2 ONLY.

Before modifying files:

1. inspect the current repository and the Milestone 1 implementation;
2. run the existing test suite and confirm the current baseline;
3. summarize the architecture changes you intend to make for Milestone 2;
4. identify the public APIs, deduction/provenance structures, ranking changes,
   and tests that will be affected;
5. verify that your plan preserves the core architectural rule that the hint
   engine contains all logical solving intelligence and that solve_logically()
   only repeatedly asks for a deduction and applies it.

Then implement Milestone 2.

Milestone 2 goal
----------------

Add candidate-set reasoning.

Introduce a representation equivalent to:

    QueenConstraint(cells, queen_count)

A QueenConstraint means that exactly `queen_count` queens must occur among
`cells`.

Constraints must be derived from the current board state and the existing
row, column, and region requirements. They must not depend on a known final
solution, guessing, backtracking, exhaustive search, or screenshot-specific
knowledge.

The first required candidate-set deduction is common-neighbor exclusion:

If a constraint proves that at least one queen must be placed somewhere in a
candidate set S, and a currently unknown target cell is adjacent to every
possible queen cell in S, then the target cell can be excluded.

The deduction must be expressed through the existing hint/deduction system,
with enough structured provenance to explain why the exclusion is valid.

Real-game acceptance case
-------------------------

Use the existing manually transcribed real-game fixture in
tests/test_known_games.py as an acceptance test.

From that board state, Milestone 1 currently reaches a point where no
supported deduction is available.

Milestone 2 must be able to continue the logical replay and derive the
expected forced queen at:

    L6C5

The replay must use only the public logical interface:

    next_hint(board)
    board.apply(deduction)

It must not use:
- the known final solution;
- guessing;
- backtracking;
- exhaustive solving;
- fixture-specific logic;
- coordinates hard-coded for this puzzle.

The deduction that ultimately enables L6C5 must arise from general
candidate-set reasoning applicable to arbitrary valid boards.

Architecture requirements
-------------------------

Keep deduction discovery pure: finding deductions must not mutate the Board.

Candidate-set reasoning belongs in the logical hint engine/rules layer, not
in solve_logically().

solve_logically() must remain a thin loop that:
1. asks the hint engine for the next logical deduction;
2. applies it;
3. repeats until solved or stalled.

Do not introduce a second independent solving implementation.

Represent provenance structurally rather than only as human-readable text.
The hint renderer should consume that provenance.

Integrate the new deduction(s) into the existing deterministic ranking system.
Repeated calls on the same board must return the same best deduction.

Preserve all Milestone 1 behavior and tests.

Follow the logging conventions defined in AGENTS.md.
Do not introduce new diagnostic print() calls.
Do not modify the logging infrastructure or MultilineConsoleRenderer unless
Milestone 2 explicitly requires it.

Progressive natural-language hints
----------------------------------

Preserve and extend the progressive hint model required by SPEC sections
14 and 15.

Logical deduction and hint rendering must remain separate:

    find_deductions(board)
        -> structured Deduction

    render_hint(deduction, level)
        -> natural-language explanation

Every deduction type introduced or used by Milestone 2 must carry enough
structured provenance for render_hint() to explain it progressively without
re-running solving logic and without relying on preformatted explanation
strings stored in the deduction.

The four hint levels must have distinct purposes:

Level 1 — attention
    Direct the player toward the relevant row, column, region, candidate set,
    or local area without revealing the conclusion.

Level 2 — observation / reasoning prompt
    Describe the relevant facts or ask the player to notice the useful
    relationship, without revealing the target action or target cell when
    avoidable.

Level 3 — deduction
    Explain the logical consequence and may identify the affected cell(s),
    but should still describe WHY the conclusion follows.

Level 4 — explicit action
    Tell the player exactly what to do, e.g. place a queen or exclude a cell.

For example, a forced-cell deduction should conceptually progress like:

    L1: "Look at region A."
    L2: "Region A needs two queens. One is already placed. How many possible
         cells remain?"
    L3: "Only L6C5 remains available for the second queen."
    L4: "Place a queen at L6C5."

The exact wording may vary where appropriate, but the information progression
must be preserved.

Candidate-set deductions introduced in Milestone 2 must receive the same
four-level treatment. Do not make levels 1–3 trivial paraphrases of level 4.

Hint rendering must use the structured provenance carried by Deduction.
Do not hard-code explanations for particular fixtures, coordinates, or known
games.

Testing
-------

Add focused tests for:

- QueenConstraint construction/normalization and validation as appropriate;
- constraints derived from rows, columns, and irregular regions;
- common-neighbor exclusion;
- cases where common-neighbor exclusion must NOT fire;
- deduction provenance;
- deduction discovery being non-mutating;
- deterministic ranking;
- interaction with existing Milestone 1 rules;
- the real-game acceptance fixture leading logically to L6C5.
- progressive render_hint() behavior for every Milestone 1 deduction type;
- progressive render_hint() behavior for every new Milestone 2 deduction type;
- level 1 does not reveal the final action;
- level 2 exposes the relevant observations without prematurely giving away
  the answer;
- level 3 explains the logical conclusion;
- level 4 gives the explicit action;
- hint text is derived from structured deduction provenance rather than
  fixture-specific or preformatted solution text;

Prefer small synthetic boards for individual rule tests.
Use the real-game fixture only as an integration/acceptance test.

Do not weaken existing tests merely to make the implementation pass.

Scope
-----

Do not implement later milestones.

Do not add:
- guessing or backtracking;
- an exhaustive solver;
- screenshot/image parsing;
- GUI or interactive-game features;
- unrelated refactors or production changes.

Small refactors are acceptable only when directly required to support the
Milestone 2 architecture.

When implementation is complete:

1. run the complete test suite;
2. report the files changed;
3. summarize the candidate-set model and new deduction logic;
4. show how the real-game fixture progresses compared with Milestone 1,
   including whether L6C5 is now derived;
5. report any remaining logical stall after the Milestone 2 rules are
   exhausted;
6. identify, without implementing, any reasoning pattern that appears to be
   required for a later milestone.

STOP after Milestone 2.
Do not begin implementing any later milestone.

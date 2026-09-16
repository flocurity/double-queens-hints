Read AGENTS.md and SPEC.md in full.

Pay particular attention to SPEC.md sections 29–32, which define Milestone 3, QueenConstraint lifecycle/provenance, and the strict boundary between local logical reasoning and forbidden search.

We are continuing the Double Queens project.

Implement MILESTONE 3 ONLY.

Milestones 1 and 2 are complete and must remain working.

Before modifying files:

1. inspect the current repository and existing tests;
2. run the existing test suite and establish the baseline;
3. inspect the current QueenConstraint, Deduction, provenance, rule-ranking,
   hint-rendering, and solve_logically architecture;
4. inspect known_game_001 and known_game_002;
5. summarize the architecture you intend to use for Milestone 3;
6. identify which existing M1/M2 mechanisms can be reused rather than duplicated;
7. identify any new structured evidence/provenance types that are actually needed;
8. explain how your design preserves the strict boundary between local logical
   reasoning and forbidden global search.

Do not modify files until you have completed that analysis.

## Milestone 3 goal

Add advanced LOCAL constraint reasoning.

Milestone 2 can represent residual QueenConstraints and derive
common-neighbor exclusions, but known_game_002 demonstrates that the engine
cannot initially progress because it cannot yet reason about:

- interactions between residual constraints;
- locally valid multi-queen placements;
- cardinality information shared by all local placements;
- derived subconstraints;
- immediate compatibility between intersecting row/column/region constraints.

The engine must gain these capabilities without becoming an exhaustive solver.

## Core architectural rule

The hint engine remains the ONLY source of logical solving intelligence.

solve_logically() must continue to make progress exclusively by repeatedly
requesting and applying deductions from the hint engine.

Do NOT add solving intelligence directly to solve_logically().

Do NOT add guessing, recursive trial-and-error, backtracking, complete board
solution enumeration, SAT/SMT solving, or solution-aware hints.

## Required reasoning capabilities

### 1. Equal-cardinality constraint inclusion

Given two residual constraints A and B:

    A.cells ⊆ B.cells
    A.queen_count == B.queen_count

then every cell in:

    B.cells - A.cells

contains zero queens and may be excluded.

The deduction must preserve both source constraints and the inclusion/cardinality
relationship as structured provenance.

### 2. Local valid placements

For a residual QueenConstraint(C, k), support reasoning about the locally valid
placements of its k remaining queens.

A placement is a subset P of C such that:

    |P| == k

and it satisfies the immediately applicable local puzzle constraints.

At minimum this includes queen non-adjacency.

Existing queens, exclusions, and residual cardinalities must be respected.

Placement generation must be deterministic.

IMPORTANT:

This is LOCAL placement enumeration.

It is allowed to ask:

    "In which ways can the remaining queens fit inside this local constraint?"

It is NOT allowed to:

- assume a candidate;
- mutate/copy the board and recursively solve it;
- run solve_logically() under the assumption;
- explore arbitrary future deductions;
- enumerate complete board solutions;
- reject a placement because some distant recursive branch eventually fails.

### 3. Facts common to all local placements

Given the complete locally valid placement set P for a constraint, support these
generic conclusions:

A. A candidate present in every placement is QUEEN.

B. A candidate present in no placement is EXCLUDED.

C. An unknown external cell that is adjacent to at least one queen in every
   placement is EXCLUDED.

These must be represented as structured, independently renderable deductions.

Do not implement separate ad-hoc rules for specific region shapes when the
generic placement rule already explains them.

### 4. Derived subconstraints

If a subset S has the same queen cardinality in every valid placement:

    for every placement p:
        |p ∩ S| == n

then the engine may derive the logical fact:

    QueenConstraint(S, n)

This is a key Milestone 3 capability.

Prefer deriving reusable structured constraints when existing M1/M2 rules can
consume them instead of duplicating their consequences.

For example:

    derived QueenConstraint({A, B}, 1)
        ->
    existing COMMON_NEIGHBOR_EXCLUSION
        ->
    common neighbors become EXCLUDED

Do not create a special rule for every occurrence of this pattern.

### 5. Constraint partition/capacity reasoning

Local placement analysis must be capable of discovering cases where candidate
subsets have forced cardinality because of their geometry.

Example:

A region requires 2 queens and its remaining candidates consist of:

- one isolated candidate;
- two mutually touching candidates.

The touching pair can contain at most one queen.

Therefore:

- the isolated candidate contains exactly one queen;
- the pair contains exactly one queen.

The singleton becomes a forced queen and the pair may become a derived
QueenConstraint(pair, 1).

Prefer obtaining this through the generic placement/subconstraint machinery
rather than shape-specific code.

### 6. Immediate cross-constraint compatibility

A locally valid placement may be rejected when it DIRECTLY violates an
intersecting structured row, column, or region constraint.

Examples of allowed immediate rejection:

- too many queens in an intersecting group;
- insufficient remaining capacity in an intersecting group;
- queen adjacency;
- a placement's forced local cardinality directly contradicts another known
  residual QueenConstraint.

Example from known_game_002:

Assuming one green candidate as part of the local green placement forced the
other green queen onto the same row, which would violate that row's queen
cardinality.

That local placement may be rejected directly.

However, this must remain immediate constraint propagation.

Do NOT turn this into recursive hypothetical solving.

## Reuse existing milestones

Milestone 3 must complement M1/M2 rather than replace them.

The intended architecture is approximately:

    M3 local reasoning
        ->
    queens / exclusions / derived QueenConstraints
        ->
    existing M1/M2 rules
        ->
    further elementary deductions
        ->
    M3 may become applicable again

In particular, do not reimplement:

- QUEEN_ADJACENCY;
- COMPLETED_GROUP;
- FORCED_REMAINING_CELLS;
- COMMON_NEIGHBOR_EXCLUSION

inside the advanced reasoning layer when existing rules can consume the newly
derived information.

If the current engine cannot yet expose derived QueenConstraints to other rules,
design the smallest clean extension that enables this while preserving the
existing architecture.

## Structured provenance

Every Milestone 3 deduction must capture enough immutable evidence at creation
time to remain independently explainable after the board changes.

Depending on the deduction, evidence may include:

- source QueenConstraint(s);
- local candidate set;
- valid local placements;
- rejected local placements and their immediate rejection reason;
- derived subconstraints;
- adjacency facts;
- inclusion/cardinality relationships;
- resulting actions.

Do not require renderers to rerun the solving algorithm.

Do not store opaque prose as the only proof.

Extend structured evidence types only where necessary.

## Hint rendering

Integrate new deductions with the existing progressive four-level hint system.

Preserve the existing philosophy:

- early levels guide without revealing the action;
- later levels expose progressively more reasoning;
- the final level gives the explicit action;
- debug rendering exposes structured proof details.

Do not move solving logic into renderers.

## Determinism and purity

The same board must produce the same:

- local placements;
- derived constraints;
- deductions;
- ranking;
- next_hint();
- logical replay.

Discovery APIs must not mutate the board.

Do not depend on set/dict iteration order.

Existing stale-deduction atomicity must continue to work for Milestone 3
deductions.

## known_game_002

known_game_002 is a real 10x10 game transcribed from the original puzzle.

Its initial board contains 100 UNKNOWN cells and no queens or exclusions.

Milestone 2 intentionally stalls immediately on it.

Use known_game_002 as an integration/regression fixture for Milestone 3.

IMPORTANT:

Do NOT encode the historical human solving order.

Do NOT encode known placements from screenshots into the solver.

Do NOT use a known final solution as evidence.

The engine may legitimately find deductions in a different deterministic order.

For this milestone, require that the engine makes strictly more logical progress
from the initial known_game_002 state than the Milestone 2 baseline.

Do NOT make "fully solves known_game_002" a hard implementation requirement
unless it follows naturally from the generic Milestone 3 rules.

If it stalls later, preserve that state as useful information for the next
milestone rather than adding puzzle-specific logic merely to make the test pass.

## Tests

Add focused behavioral tests for at least:

1. equal-cardinality constraint inclusion;
2. candidate present in every local placement -> QUEEN;
3. candidate present in no local placement -> EXCLUDED;
4. external cell necessarily adjacent to a queen in every local placement
   -> EXCLUDED;
5. derived QueenConstraint(S, n);
6. singleton forced by partition/capacity reasoning;
7. local placement rejected by an immediately intersecting row/column/region
   constraint;
8. deterministic placement generation;
9. deterministic deduction ordering;
10. query purity;
11. stale deduction rejection / atomic application where applicable;
12. progressive hint rendering and debug provenance;
13. interaction with existing M1/M2 rules;
14. known_game_002 making strictly more progress than its M2 empty-board
    baseline;
15. known_game_001 remaining replayable and valid.

Prefer small synthetic boards for unit tests.

Use known_game_001 and known_game_002 for integration/regression behavior.

Tests must validate behavior and structured evidence, not private implementation
details.

## Scope discipline

Implement Milestone 3 only.

Do not:

- add screenshot ingestion;
- add OCR;
- add GUI features;
- add exhaustive solving;
- add backtracking;
- add speculative future milestone infrastructure;
- refactor unrelated working code;
- rewrite M1/M2 without a concrete architectural need;
- weaken existing tests to make the new implementation pass.

If the mini-spec conflicts with the existing repository architecture or SPEC.md,
stop and explain the conflict before making a broad architectural change.

## Validation

Before finishing:

1. run the focused Milestone 3 tests;
2. run known-game tests;
3. run the full test suite;
4. run git diff --check;
5. verify known_game_001 still replays correctly;
6. report how far known_game_002 now progresses from its empty initial state;
7. report the exact reason/rule where it stalls, if it stalls;
8. explicitly confirm that no recursive/global search was introduced;
9. summarize new public APIs and structured evidence types;
10. summarize any SPEC.md or README documentation changes.

Do not commit or tag anything unless explicitly requested.

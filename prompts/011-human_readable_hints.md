# Hint wording and progressive-disclosure review

Milestone 3 is complete and logically validated. The full suite currently passes 156 tests.

This task is NOT a new reasoning milestone.

Its purpose is to review and improve the human-facing hint renderer across M1, M2, and M3, based on examples observed while replaying Known Game 002.

The deduction engine, proof model, rule semantics, ranking, solver behavior, and board behavior must remain unchanged.

## Goal

Hints should explain the same deductions in natural, concise English while preserving the four progressive hint levels:

1. where to look;
2. what relationship or rule to think about;
3. the complete human-readable reasoning;
4. the exact board action(s).

The internal proof representation may remain formal and exhaustive.

The human-facing hint renderer should NOT merely stringify that proof representation.

A key design principle for this task is:

> proof renderer != hint renderer

The proof/debug representation answers:

> "Why is this deduction formally valid?"

The hint renderer answers:

> "How can a human player discover and understand this deduction without unnecessarily revealing other deductions?"

Before changing code, inspect the current renderer architecture, deduction/proof types, and tests. Explain briefly how you intend to implement the wording improvements without moving reasoning logic into the renderer.

Do not modify production code until that analysis is complete.

---

# 1. General wording principles

Prefer puzzle-domain language over internal constraint-engine terminology.

Good concepts for player-facing hints include:

- row
- column
- region
- remaining candidates
- remaining queen(s)
- valid placement
- touches
- must contain a queen
- cannot contain a queen

Avoid exposing implementation terminology when a natural puzzle description exists, including phrases such as:

- candidate set
- subset / superset
- nonempty queen set
- cardinality
- subtracting counts
- intersecting constraint, when the actual row/column/region can be named instead
- "Every placement contains 0 queen(s) in {...}"
- "All its cells ... are needed"

Internal proof/debug output may continue using formal terminology where appropriate.

Do not weaken or alter the logical meaning merely to make wording shorter.

---

# 2. Grammar and list formatting

Remove mechanical constructions such as:

- `queen(s)`
- `region X and their remaining candidates`
- `L3C9 touch every candidate`
- repeated independent actions such as `Exclude A. Exclude B. Exclude C.`

Pluralization MUST be derived from the actual count.

Never use parenthesized plural forms such as:

    queen(s)
    cell(s)
    candidate(s)

For every count-dependent noun, render the grammatically correct form:

    0 queens
    1 queen
    2 queens

    0 candidates
    1 candidate
    2 candidates

    1 cell
    2 cells

This applies everywhere in human-facing hints, not only to the examples listed in this prompt.

Prefer natural wording when the numeric form would sound mechanical:

    still needs one queen

rather than:

    still needs 1 queen

when appropriate.

Implement this through reusable count/pluralization helpers where useful, rather than scattered special cases.

Add tests covering at least counts 0, 1, and 2, and ensure no human-facing hint produced by the tested rule families contains parenthesized plural forms such as `(s)`.

Introduce reusable formatting helpers where appropriate rather than fixing individual strings independently.

Examples:

One cell:

    L3C9

Two cells:

    L3C9 and L4C9

Three or more cells:

    L3C9, L4C9, and L5C9

Use natural singular/plural grammar:

    one queen
    2 queens

    L3C9 touches ...
    L3C9 and L4C9 touch ...

    L3C9 cannot contain a queen.
    L3C9 and L4C9 cannot contain queens.

Use Oxford commas for lists of three or more items.

Cell coordinates must use the canonical formatting already used by the project:

    L10C3

Never accidentally render:

    l10c3

Aggregate identical level-4 actions:

    Exclude L3C9.

    Exclude L3C9 and L4C9.

    Exclude L3C9, L4C9, and L5C9.

Likewise:

    Place a queen at L3C9.

    Place queens at L3C9 and L4C9.

---

# 3. Four-level progressive disclosure

Keep the semantic purpose of each level consistent across rule families.

## Level 1

Direct attention to the relevant board area.

Examples:

    Look at column 6.

    Look at the remaining candidates in column 6.

    Look at region 🟢.

    Look at the remaining candidates in region 🟢.

Avoid:

    Look at column 6 and their remaining candidates.

For relationships involving two groups:

    Look at the remaining candidates in region 🩵 and row 10.

## Level 2

Suggest the relevant rule, relationship, or question without fully giving the conclusion.

Do not ask irrelevant mechanical questions.

For example, completed groups currently say:

    Column 10 requires 2 queens and already has 2.
    How many unknown cells remain?

The number of unknown cells is irrelevant to the reasoning.

Prefer:

    Column 10 already contains its 2 required queens.
    What does that mean for its remaining candidates?

For a group that still needs one queen:

    Region 🟢 still needs one queen among L4C7 and L5C6.
    Which cells touch both candidates?

For local placement reasoning, adapt the question to the remaining quota instead of always using the generic:

    Consider the ways they can fit without touching or violating intersecting quotas.
    What holds in every local placement?

For example:

    Column 7 still needs 2 queens among 5 candidates.
    Which pairs can be placed without touching or violating another quota?

Or, when one queen remains:

    Row 3 still needs one queen.
    Can L3C8 be a valid position for it?

Do not overfit these exact sentences if the existing proof data supports a cleaner generic design.

## Level 3

Give the complete human-readable reasoning for THIS deduction.

This is where the current renderer most needs improvement.

The explanation should be logically sufficient but should not unnecessarily dump the entire internal proof or reveal sibling deductions.

Prefer explaining derived human concepts such as:

    Exactly one of L10C3 and L10C4 must contain a queen.

rather than exposing:

    Every placement contains 1 queen(s) in {L10C3, L10C4}.

## Level 4

Give the exact action or actions, compactly.

Examples:

    Exclude L3C9.

    Exclude L3C9 and L4C9.

    Place a queen at L7C2.

    Place queens at L2C10 and L4C10.

---

# 4. M1 — queen adjacency

Current style:

    level 1: Look around L8C4.
    level 2: L8C4 is a queen. Queens cannot touch, even diagonally.
    level 3: L7C3, L7C4, L7C5 touch the queen at L8C4, so cannot contain queens.
    level 4: Exclude L7C3. Exclude L7C4. Exclude L7C5.

Preferred style:

    level 1: Look around L8C4.
    level 2: L8C4 contains a queen. Queens cannot touch, even diagonally.
    level 3: L7C3, L7C4, and L7C5 all touch the queen at L8C4, so none of them can contain a queen.
    level 4: Exclude L7C3, L7C4, and L7C5.

Handle the singleton naturally:

    L3C9 touches the queen at L4C10, so it cannot contain a queen.

Do not change the adjacency rule itself.

---

# 5. M1 — completed groups

Observed example:

    level 1: Look at column 10.
    level 2: Column 10 requires 2 queens and already has 2. How many unknown cells remain?
    level 3: Column 10 already has two queens, so L8C10, L9C10, L10C10 cannot contain queens.
    level 4: Exclude L8C10. Exclude L9C10. Exclude L10C10.

Preferred direction:

    level 1: Look at column 10.
    level 2: Column 10 already contains its 2 required queens. What does that mean for its remaining candidates?
    level 3: Column 10 already contains its 2 required queens, so L8C10, L9C10, and L10C10 cannot contain queens.
    level 4: Exclude L8C10, L9C10, and L10C10.

Singleton example:

    Column 9 already contains its 2 required queens, so L10C9 cannot contain a queen.

---

# 6. M1 — forced remaining cells

Observed singleton example:

    level 1: Look at region 🟠.
    level 2: Region 🟠 requires 2 queens and already has 1. How many unknown cells remain?
    level 3: Only L8C4 remain available in region 🟠; all are needed to reach two queens.
    level 4: Place a queen at L8C4.

Preferred direction:

    level 1: Look at region 🟠.
    level 2: Region 🟠 still needs one queen. Which candidates are still available?
    level 3: Only L8C4 remains available in region 🟠. The region still needs one queen, so L8C4 must contain it.
    level 4: Place a queen at L8C4.

Handle plural forced cells naturally:

    Only A and B remain available.
    The group still needs 2 queens, so both cells must contain queens.

Do not force the total group quota into every sentence when the remaining quota is more natural.

---

# 7. M2 — common-neighbor exclusion

Observed example:

    Region 🟣 still needs 2 queen(s) among L2C10, L3C10, L4C10.
    ...
    At least one queen must occur among L2C10, L3C10, L4C10 in region 🟣.
    L3C9 touch every candidate, so cannot contain queens.

The level-3 explanation currently weakens exact information from "2 among 3" to "at least one".

Preserve useful exact cardinality.

Preferred direction:

    level 2:
    Region 🟣 still needs 2 queens among L2C10, L3C10, and L4C10.
    Which cells touch all three candidates?

    level 3:
    Region 🟣 must place 2 queens among L2C10, L3C10, and L4C10.
    L3C9 touches all three cells, so it will necessarily touch at least one of those queens.
    Therefore L3C9 cannot contain a queen.

For a 1-of-2 case:

    One of L4C7 and L5C6 must contain a queen.
    L5C7 touches both cells, so it will necessarily touch that queen.
    Therefore L5C7 cannot contain a queen.

For a derived fixed-cardinality subset:

    Exactly one of L10C3 and L10C4 must contain a queen.
    L9C4 touches both cells, so it will necessarily touch that queen.
    Therefore L9C4 cannot contain a queen.

Avoid phrases such as:

    nonempty queen set

---

# 8. M3 — constraint inclusion

Observed example conceptually represents:

    region 🩵 remaining candidates ⊂ row 10 remaining candidates
    both require 2 queens
    therefore row-10 candidates outside the region require 0 queens

Current renderer exposes the abstract set algebra directly.

Prefer contextualizing the proof with actual puzzle groups.

Example direction:

    level 1:
    Look at the remaining candidates in region 🩵 and row 10.

    level 2:
    All remaining candidates in region 🩵 are in row 10.
    Both the region and the row still need 2 queens.
    How many queens can row 10 have outside the region?

    level 3:
    Region 🩵 must place its 2 remaining queens among L10C3, L10C4, L10C8, and L10C9.
    Row 10 also needs exactly 2 queens, so those queens already account for everything the row needs.
    Therefore L10C1 and L10C2 cannot contain queens.

    level 4:
    Exclude L10C1 and L10C2.

The internal proof may continue to be:

    A subset B
    count(A) = 2
    count(B) = 2
    count(B - A) = 0

but player-facing hints should name the actual row/column/region whenever provenance allows it.

The renderer should also work for nonzero differences, e.g.:

    count(B) - count(A) = 1

Do not special-case only the 2-minus-2 example.

---

# 9. M3 — local placements, forced queens

Observed singleton-common-to-all example:

    valid placements:
    {L7C2, L7C6}
    {L7C2, L7C7}

Current wording:

    Every placement contains 1 queen(s) in {L7C2}.
    All its cells, L7C2, are needed and must contain queens.

Preferred:

    The valid placements are {L7C2, L7C6} and {L7C2, L7C7}.
    Both contain L7C2, so L7C2 must contain a queen.

For more than two placements:

    Every valid placement contains L7C7, so L7C7 must contain a queen.

For exactly one valid placement:

    The only valid placement is {L2C10, L4C10}.
    Therefore both cells must contain queens.

Then:

    Place queens at L2C10 and L4C10.

Avoid:

    Every placement contains 2 queen(s) in {L2C10, L4C10}.
    All its cells ... are needed ...

Consider whether listing placements remains readable.

A reasonable renderer may distinguish:

- one valid placement;
- a small number of valid placements;
- many valid placements.

Do not dump a combinatorially large placement list into a player hint.

Choose and document a deterministic threshold if one is needed.

---

# 10. M3 — local placements, impossible cells

Observed example:

    Row 3 still needs one queen among 5 candidates.

Valid local placements place it at:

    L3C1
    L3C2
    L3C3
    L3C7

Therefore L3C8 is impossible.

Current wording:

    Every placement contains 0 queen(s) in {L3C8}.
    No queen can remain at L3C8.

Avoid expressing zero-cardinality consequences this way.

For a singleton exclusion, prefer the semantic idea:

    L3C8 cannot be part of any valid placement, so it cannot contain a queen.

Or, progressively:

    level 2:
    Row 3 still needs one queen.
    Can L3C8 be a valid position for it?

    level 3:
    There is no valid way to place the remaining queen at L3C8 without violating another constraint.
    Therefore L3C8 cannot contain a queen.

For multiple exclusions:

    Neither L1C7 nor L4C7 can be part of a valid placement, so neither can contain a queen.

For larger sets:

    None of A, B, and C can be part of a valid placement, so those cells cannot contain queens.

If `RejectedPlacement` provenance provides a concise, specific reason for why a target is impossible, prefer that concrete reason over a generic "violating another constraint", provided doing so remains understandable and does not expose unrelated deductions.

Do not invent a reason that is not represented by the proof.

---

# 11. Avoid sibling-deduction spoilers

This is important.

Known Game 002 exposed this sequence:

Step 14:

    Column 6 needs one queen among 7 candidates.

The renderer listed every valid placement:

    {L1C6}
    {L2C6}
    {L5C6}
    {L6C6}
    {L7C6}

and concluded only:

    L3C6 = EXCLUDED

Step 15 then used the same valid-placement set to conclude:

    L4C6 = EXCLUDED

Therefore the level-3 hint for step 14 already revealed the conclusion of step 15: L4C6 was visibly absent from every listed placement.

The proof is correct, but progressive disclosure is not ideal.

A hint for one deduction should not unnecessarily expose independent sibling deductions that the engine intends to present later.

For a deduction whose action is only:

    L3C6 = EXCLUDED

prefer a target-focused explanation such as:

    There is no valid way to place the remaining queen at L3C6 without violating another constraint.
    Therefore L3C6 cannot contain a queen.

Do not enumerate all placements if doing so reveals additional conclusions unrelated to the selected deduction.

Add a focused regression test for this Known Game 002 behavior or an equivalent minimal synthetic board.

The test should ensure the hint for the first exclusion does not reveal the sibling target that is intended to be a later deduction.

Do not change deduction ranking or combine the two deductions merely to make the hint easier.

---

# 12. Derived constraints should be explained as knowledge, not implementation

M3 may derive a `QueenConstraint`, which is then consumed by M2 or M1.

For example, local placements may establish:

    exactly 1 queen among {L10C3, L10C4}

and common-neighbor reasoning may then exclude L9C4.

The player-facing explanation should preferably say:

    Exactly one of L10C3 and L10C4 must contain a queen.
    L9C4 touches both cells, so it will necessarily touch that queen.
    Therefore L9C4 cannot contain a queen.

It should not require the player to inspect the entire local-placement enumeration that originally produced that derived constraint unless that enumeration is itself useful and appropriately scoped.

The proof DAG should remain intact.

This is purely about selecting the most useful human-facing layer of that proof.

---

# 13. Debug/proof verbosity

While reviewing this code, inspect the distinction between meaningful proof premises and freshness/state snapshots.

M3 deductions currently may produce very large debug output because many observed cells are retained for stale-deduction validation.

Do NOT weaken freshness validation or remove provenance merely to shorten debug output.

If the existing architecture makes it clean and low-risk, consider presenting these separately in debug output, conceptually like:

    PROOF PREMISES:
    - meaningful logical premises

    VALID LOCAL PLACEMENTS:
    - ...

    CHECKED CONSTRAINTS:
    - ...

    FRESHNESS SNAPSHOT:
    - N observed cells

Detailed freshness cells may remain available in an explicitly verbose representation.

However, this is secondary to the human-facing hint wording.

Do not perform a large debug-renderer refactor if it is not naturally supported by the current model. Report what you found instead.

---

# 14. Preserve architecture and soundness

This task must NOT:

- change which deductions exist;
- change deduction ranking;
- change `best_deduction()` selection;
- change `solve_logically()` behavior;
- add guessing;
- add search;
- add backtracking;
- add hypothetical recursive reasoning;
- modify Board semantics;
- weaken stale-deduction checks;
- remove proof provenance;
- special-case Known Game 002 coordinates in production code;
- move solving intelligence into the renderer.

The renderer may inspect structured deduction/proof information in order to choose a natural explanation.

It must not independently derive new logical facts.

If a desired wording would require reasoning that is not represented in structured provenance, do not reconstruct it heuristically in the renderer. Either use a faithful generic wording or explain what additional structured provenance would be needed.

---

# 15. Tests

Add focused tests for wording behavior rather than only snapshotting huge complete strings.

Cover at least:

- singular queen / plural queens;
- singular target / multiple targets;
- natural cell-list formatting;
- canonical uppercase coordinates;
- queen adjacency;
- completed group;
- forced remaining cell;
- common-neighbor exclusion;
- inclusion with zero difference;
- inclusion with nonzero difference;
- local-placement forced singleton queen;
- local-placement multiple forced queens;
- local-placement singleton exclusion;
- local-placement multiple exclusions;
- exactly one valid placement;
- multiple valid placements;
- sufficiently many placements that the renderer should avoid an excessive dump, if a threshold is implemented;
- no sibling-deduction spoiler for the column-6 Game 002 pattern;
- derived fixed-cardinality constraint consumed by another rule.

Where useful, assert that undesirable phrases no longer occur:

    queen(s)
    nonempty queen set
    Every placement contains 0
    All its cells

Do not make tests unnecessarily brittle to harmless punctuation changes, but ensure the important progressive-disclosure and semantic properties are protected.

---

# 16. Known-game regression

Replay Known Game 001 and Known Game 002 after the renderer changes.

The logical deduction sequence must remain unchanged.

Current expected baseline before this task:

- Known Game 001 solves/replays in exactly 32 deductions.
- Known Game 002 solves in exactly 55 deductions.
- Known Game 002 uses 16 advanced/M3 deductions.
- Known Game 002 reaches 20 queens.
- The current full suite passes 156 tests.

Confirm these remain unchanged unless the current repository state demonstrates a different already-established baseline.

The wording may change.

The deductions and actions must not.

---

# 17. Implementation approach

Before editing:

1. inspect the current hint renderer and proof structures;
2. identify the existing rule-family templates;
3. identify reusable language helpers that would remove duplicated grammar/list logic;
4. determine which improvements can be made from existing structured provenance;
5. identify any requested wording that would require unavailable provenance;
6. explain how sibling-deduction spoilers will be prevented without changing deduction selection.

Then implement the smallest coherent renderer refactor that addresses these issues.

Prefer semantic helpers over scattered string patches.

Examples of potentially useful concepts, without prescribing exact API names:

    format_cell_list(...)
    format_queen_count(...)
    format_action_list(...)
    describe_group(...)
    describe_remaining_quota(...)

Do not introduce a general natural-language framework or unnecessary abstraction layer.

Keep it proportionate to this project.

---

# 18. Validation and final report

Run focused renderer tests first, then the complete suite.

Also run the repository's normal formatting/lint/type checks if configured.

At the end report:

1. files changed;
2. renderer/template architecture changes;
3. wording families improved;
4. tests added;
5. Known Game 001 deduction count;
6. Known Game 002 deduction count;
7. Known Game 002 advanced/M3 deduction count;
8. total test count and result;
9. any wording improvement intentionally not implemented because the proof model lacks the required structured provenance;
10. any debug/proof verbosity improvement made or deliberately deferred.

Do not commit.

Do not tag.

Stop after implementation, validation, and report so I can review the diff.
"""Bounded local proofs; expected placements are hand-written, not searched."""
from dataclasses import FrozenInstanceError, replace

import pytest

from double_queens import (
    Action, Board, Cell, CellFact, CellState, ContradictionError, DebugRenderContext,
    GroupKind, InclusionProof, PlacementConflict, PlacementSubsetProof, QueenConstraint,
    Rule, analyze_local_placements, best_deduction, derive_constraints,
    derive_inclusions, derive_local_constraints, derive_subconstraint,
    find_deductions, next_hint, render_deduction, render_hint,
)
from double_queens.rules import candidate_sets, completed_group, forced_cells, local_constraints

U, Q, X = CellState.UNKNOWN, CellState.QUEEN, CellState.EXCLUDED


def row_board(columns=(0, 3, 4)):
    state = [[U] * 8 for _ in range(8)]
    state[0] = [U if c in columns else X for c in range(8)]
    return Board([[str(r)] * 8 for r in range(8)], state)


def source(board, kind=GroupKind.ROW, index=0):
    return next(c for c in derive_constraints(board)
                if c.source.group.kind == kind and c.source.group.index == index)


def test_equal_cardinality_inclusion_reuses_completed_group_with_both_sources():
    # Column 1 is wholly inside region 0, which also includes L1C2.
    regions = [[str(c) for c in range(8)] for _ in range(8)]
    regions[0][1] = '0'
    board = Board(regions)
    small, large = source(board, GroupKind.COLUMN, 0), source(board, GroupKind.REGION, '0')
    derived, = derive_inclusions((small, large))
    assert derived.cells == frozenset((Cell(0, 1),)) and derived.queen_count == 0
    assert derived.derivation == InclusionProof(small, large)
    deduction, = completed_group.find_deductions(board, (derived,))
    assert deduction.rule == Rule.COMPLETED_GROUP
    assert deduction.premises == (small.source, large.source)
    assert deduction.actions == (Action(Cell(0, 1), X),)
    board.apply(deduction)
    assert board.at(Cell(0, 1)) == X


def test_inclusion_difference_can_be_a_reusable_nontrivial_constraint():
    a, b, c, d = (Cell(0, i) for i in range(4))
    small = QueenConstraint({a, b}, 1)
    large = QueenConstraint({a, b, c, d}, 2)
    derived, = derive_inclusions((large, small))
    assert derived.cells == frozenset((c, d)) and derived.queen_count == 1
    assert derived.derivation == InclusionProof(small, large)
    assert derive_inclusions((small, small)) == ()
    assert derive_inclusions((small, QueenConstraint({c, d}, 1))) == ()
    with pytest.raises(ContradictionError):
        derive_inclusions((small, QueenConstraint({a, b, c}, 0)))
    with pytest.raises(ContradictionError):
        derive_inclusions((small, QueenConstraint({a, b}, 2)))


def test_partition_forces_singleton_and_pair_with_complete_placement_evidence():
    board = row_board()
    constraint = source(board)
    before = board.state
    analysis = analyze_local_placements(board, constraint)
    a, b, c = Cell(0, 0), Cell(0, 3), Cell(0, 4)
    assert analysis.placements == (frozenset((a, b)), frozenset((a, c)))
    assert len(analysis.rejected) == 1
    rejection = analysis.rejected[0]
    assert rejection.placement == frozenset((b, c))
    assert rejection.reason == PlacementConflict.ADJACENCY
    assert {rejection.adjacency.target, rejection.adjacency.candidate} == {b, c}
    singleton = derive_subconstraint(analysis, {a})
    pair = derive_subconstraint(analysis, {b, c})
    assert singleton.queen_count == pair.queen_count == 1
    assert pair.derivation == PlacementSubsetProof(analysis)
    assert derive_subconstraint(analysis, {b}) is None
    assert all(c in derive_local_constraints(board) for c in (singleton, pair))
    deduction, = forced_cells.find_deductions(board, (singleton,))
    assert deduction.actions == (Action(a, Q),)
    assert deduction.rule == Rule.FORCED_REMAINING_CELLS and deduction.difficulty == 3
    assert deduction.premises == analysis.premises
    neighbor, = candidate_sets.find_deductions(board, (pair,))
    assert neighbor.rule == Rule.COMMON_NEIGHBOR_EXCLUSION
    assert neighbor.constraint == pair
    assert neighbor.actions == (Action(Cell(1, 3), X), Action(Cell(1, 4), X))
    assert board.state == before
    board.apply(deduction)
    assert board.at(Cell(1, 0)) == U  # Queen adjacency is a separate next hint.
    assert next_hint(board).rule == Rule.QUEEN_ADJACENCY
    with pytest.raises(FrozenInstanceError):
        analysis.placements = ()


def test_candidate_absent_from_all_placements_is_excluded():
    board = row_board((0, 1, 2))
    analysis = analyze_local_placements(board, source(board))
    assert analysis.placements == (frozenset((Cell(0, 0), Cell(0, 2))),)
    absent = derive_subconstraint(analysis, {Cell(0, 1)})
    assert absent.queen_count == 0
    deduction, = completed_group.find_deductions(board, (absent,))
    assert deduction.actions == (Action(Cell(0, 1), X),)
    board.apply(deduction)
    assert board.at(Cell(0, 1)) == X


def test_external_exclusion_can_have_different_witnesses_in_each_placement():
    board = row_board((0, 2, 4))
    analysis = analyze_local_placements(board, source(board))
    a, b, c = Cell(0, 0), Cell(0, 2), Cell(0, 4)
    assert analysis.placements == (frozenset((a, b)), frozenset((a, c)), frozenset((b, c)))
    deduction, = local_constraints.placement_exclusions(board, analysis)
    assert deduction.rule == Rule.LOCAL_PLACEMENT_EXCLUSION
    assert deduction.actions == (Action(Cell(1, 1), X), Action(Cell(1, 3), X))
    assert not candidate_sets.find_deductions(board, (analysis.constraint,))
    for coverage in deduction.coverage:
        assert len(coverage.witnesses) == len(analysis.placements)
        for placement, witness in zip(analysis.placements, coverage.witnesses):
            assert witness.target == coverage.target
            assert witness.candidate in placement
            assert witness.candidate in board.neighbors(coverage.target)
    assert len({w.candidate for w in deduction.coverage[0].witnesses}) > 1
    assert Action(Cell(2, 2), X) not in deduction.actions
    board.apply(deduction)
    assert board.at(Cell(2, 2)) == U


def test_external_exclusion_requires_a_witness_in_every_placement():
    board = row_board((0, 2, 4, 6))
    analysis = analyze_local_placements(board, source(board))
    assert not local_constraints.placement_exclusions(board, analysis)
    # L2C2 touches candidates L1C1 and L1C3, but neither queen in {L1C5,L1C7}.
    assert frozenset((Cell(0, 4), Cell(0, 6))) in analysis.placements


def test_zero_remaining_queens_produces_only_the_empty_placement():
    board = row_board()
    zero = QueenConstraint({Cell(2, 2)}, 0)
    analysis = analyze_local_placements(board, zero)
    assert analysis.placements == (frozenset(),)
    assert not local_constraints.placement_exclusions(board, analysis)
    assert derive_subconstraint(analysis, zero.cells).queen_count == 0


def cross_board(kind, under=False):
    state = [[U] * 8 for _ in range(8)]
    if kind == GroupKind.REGION:
        regions = [[str(max(1, r))] * 8 for r in range(8)]
        for r, c in ((0, 0), (0, 3), (3, 7)):
            regions[r][c] = '0'
        state[0] = [U if c in (0, 3, 6) else X for c in range(8)]
        state[3][7] = Q
        return Board(regions, state), GroupKind.ROW, 0
    regions = [[str(max(1, r))] * 8 for r in range(8)]
    for r, c in ((0, 0), (0, 3), (3, 0)):
        regions[r][c] = '0'
    if under:
        state[0] = [U if c in (0, 3) else X for c in range(8)]
    else:
        state[0][7] = Q
    if kind == GroupKind.COLUMN:
        regions = list(zip(*regions))
        state = list(zip(*state))
    return Board(regions, state), GroupKind.REGION, '0'


@pytest.mark.parametrize('kind', list(GroupKind))
def test_immediate_intersecting_quota_rejects_overfilled_placement(kind):
    board, source_kind, index = cross_board(kind)
    analysis = analyze_local_placements(board, source(board, source_kind, index))
    pair = frozenset((Cell(0, 0), Cell(3, 0))) if kind == GroupKind.COLUMN else frozenset((Cell(0, 0), Cell(0, 3)))
    rejected = next(r for r in analysis.rejected if r.placement == pair)
    assert rejected.reason == PlacementConflict.OVER_CAPACITY
    assert rejected.constraint.source.group.kind == kind
    assert rejected.occupied == 2 and rejected.constraint.queen_count == 1
    assert len(analysis.placements) == 2


def test_immediate_capacity_rejects_unfillable_intersecting_group():
    board, kind, index = cross_board(GroupKind.ROW, under=True)
    analysis = analyze_local_placements(board, source(board, kind, index))
    assert analysis.placements == (frozenset((Cell(0, 0), Cell(0, 3))),)
    assert all(r.reason == PlacementConflict.UNDER_CAPACITY for r in analysis.rejected)
    assert all(r.occupied + len(r.available) < r.constraint.queen_count for r in analysis.rejected)


@pytest.mark.parametrize('last_column,block_external,reject', [
    (4, False, True),
    (6, False, False),
    (6, True, True),
])
def test_under_capacity_for_partially_overlapping_inclusion_constraint(
    last_column, block_external, reject,
):
    # Column 1 needs one more queen. Region 0 contains its remaining candidates
    # plus {L1C3, L2C2, L2C4}, and needs two queens. Subtraction proves exactly
    # one queen in that three-cell set, which overlaps row 1 only at L1C3.
    regions = [[str(c) for c in range(8)] for _ in range(8)]
    regions[7][0] = '7'
    a, b, c = Cell(0, 2), Cell(1, 1), Cell(1, 3)
    for cell in (a, b, c):
        regions[cell.row][cell.col] = '0'
    state = [[U] * 8 for _ in range(8)]
    state[7][0] = Q
    state[0] = [U if col in (0, 2, last_column) else X for col in range(8)]
    if block_external:
        state[2][4] = Q  # Blocks L2C4 without touching any row-1 candidate.
    board = Board(regions, state)
    before = board.state
    base = derive_constraints(board)
    column = source(board, GroupKind.COLUMN, 0)
    region = source(board, GroupKind.REGION, '0')
    derived, = derive_inclusions((column, region))
    assert derived.cells == frozenset((a, b, c))
    assert derived.queen_count == 1
    assert derived.derivation == InclusionProof(column, region)
    row = source(board)
    assert row.cells & derived.cells == frozenset((a,))
    assert row.cells - derived.cells and derived.cells - row.cells

    placement = frozenset((Cell(0, 0), Cell(0, last_column)))
    native = analyze_local_placements(board, row, base)
    assert placement in native.placements  # Native quotas alone allow this.
    analysis = analyze_local_placements(board, row, base + (derived,))
    assert derived in analysis.checked_constraints
    if reject:
        rejection = next(r for r in analysis.rejected if r.placement == placement)
        assert rejection.reason == PlacementConflict.UNDER_CAPACITY
        assert rejection.constraint == derived
        assert rejection.occupied == 0
        assert rejection.available == frozenset()
        assert analysis.placements == tuple(p for p in native.placements if p != placement)
    else:
        # L2C4 is still available: 0 occupied + 1 available meets the quota.
        assert analysis.placements == native.placements
        assert placement in analysis.placements
    # If L1C3 is selected, it already fills the derived quota. Removing it
    # from 'available' must not cause rejection: it counts in 'occupied'.
    assert frozenset((Cell(0, 0), a)) in analysis.placements
    assert column.source in analysis.premises and region.source in analysis.premises
    assert board.state == before


def test_existing_queen_and_exclusions_are_respected():
    board = row_board((0, 3, 4))
    state = [list(row) for row in board.state]
    state[1][5] = Q
    board = Board(board.regions, state)
    analysis = analyze_local_placements(board, source(board))
    assert analysis.placements == (frozenset((Cell(0, 0), Cell(0, 3))),)
    rejection = next(r for r in analysis.rejected if r.reason == PlacementConflict.EXISTING_QUEEN)
    assert rejection.adjacency.candidate == Cell(1, 5)
    assert all(board.at(c) == U for p in analysis.placements for c in p)


def test_empty_placement_set_is_a_contradiction_not_a_vacuous_proof():
    board = row_board((0, 1))
    with pytest.raises(ContradictionError, match='No locally valid placement'):
        analyze_local_placements(board, source(board))
    normal = row_board()
    analysis = analyze_local_placements(normal, source(normal))
    with pytest.raises(ContradictionError):
        derive_subconstraint(replace(analysis, placements=()), {Cell(0, 0)})
    with pytest.raises(ValueError):
        derive_subconstraint(analysis, {Cell(7, 7)})
    with pytest.raises(ValueError, match='at most two'):
        analyze_local_placements(normal, QueenConstraint({Cell(1, i) for i in range(4)}, 3))


def test_purity_determinism_and_no_hypothetical_solver_calls(monkeypatch):
    from double_queens import engine, solver
    board = row_board()
    before = board.state
    def forbidden(*args, **kwargs):
        pytest.fail('Local discovery must not create/apply a hypothetical board or call the solver')
    monkeypatch.setattr(Board, '__init__', forbidden)
    monkeypatch.setattr(Board, 'apply', forbidden)
    monkeypatch.setattr(solver, 'solve_logically', forbidden)
    # analyze_local_placements must not delegate to the hint engine either.
    with monkeypatch.context() as patch:
        patch.setattr(engine, 'next_hint', forbidden)
        patch.setattr(engine, 'find_deductions', forbidden)
        first = analyze_local_placements(board, source(board))
        assert first == analyze_local_placements(board, source(board))
        assert derive_local_constraints(board) == derive_local_constraints(board)
    deductions = find_deductions(board)
    assert deductions == find_deductions(board)
    assert best_deduction(deductions) == best_deduction(reversed(deductions)) == next_hint(board)
    assert board.state == before


@pytest.mark.parametrize('changed_cell', [Cell(0, 3), Cell(1, 3), Cell(7, 0)])
def test_advanced_evidence_freshness_is_atomic(changed_cell):
    board = row_board()
    analysis = analyze_local_placements(board, source(board))
    pair = derive_subconstraint(analysis, {Cell(0, 3), Cell(0, 4)})
    deduction, = candidate_sets.find_deductions(board, (pair,))
    assert any(CellFact(changed_cell, U) in p.facts for p in deduction.premises)
    state = [list(row) for row in board.state]
    state[changed_cell.row][changed_cell.col] = X
    changed = Board(board.regions, state)
    changed.validate()
    before = changed.state
    with pytest.raises(ValueError, match='stale'):
        changed.apply(deduction)
    assert changed.state == before


@pytest.mark.parametrize('rule', [Rule.FORCED_REMAINING_CELLS, Rule.COMPLETED_GROUP,
                                  Rule.COMMON_NEIGHBOR_EXCLUSION, Rule.LOCAL_PLACEMENT_EXCLUSION])
def test_advanced_progressive_hints_and_independent_debug_proof(rule):
    board = row_board((0, 1, 2) if rule == Rule.COMPLETED_GROUP else
                      (0, 2, 4) if rule == Rule.LOCAL_PLACEMENT_EXCLUSION else (0, 3, 4))
    deductions = local_constraints.find_deductions(board)
    deduction = next(d for d in deductions if d.rule == rule)
    hints = [render_hint(deduction, level) for level in range(1, 5)]
    assert len(set(hints)) == 4 and hints[0].startswith('Look')
    assert 'candidates' in hints[1]
    for a in deduction.actions:
        assert str(a.cell) not in hints[0] + hints[1]
        assert str(a.cell) in hints[2] + hints[3]
    assert ('placement' in hints[2] or 'must contain a queen' in hints[2])
    assert 'must' in hints[2] or 'cannot' in hints[2]
    assert hints[3].count('.') == 1
    assert all(str(a.cell) in hints[3] for a in deduction.actions)
    debug = render_deduction(deduction)
    assert 'VALID LOCAL PLACEMENTS:' in debug and 'REJECTED LOCAL PLACEMENTS:' in debug
    board.apply(deduction)
    assert [render_hint(deduction, level) for level in range(1, 5)] == hints
    assert render_deduction(deduction) == debug


def test_inclusion_hints_explain_subtraction_and_debug_retains_parent_counts():
    board = row_board()
    # Derive a pair via placements, then subtract it from its original row.
    row = source(board)
    analysis = analyze_local_placements(board, row)
    pair = derive_subconstraint(analysis, {Cell(0, 3), Cell(0, 4)})
    singleton, = derive_inclusions((pair, row))
    deduction, = forced_cells.find_deductions(board, (singleton,))
    assert 'remaining candidates' in render_hint(deduction, 2)
    assert 'leaves one queen' in render_hint(deduction, 3)
    debug = render_deduction(deduction)
    assert 'INCLUSION:' in debug and 'SUBCONSTRAINT:' in debug
    assert 'VALID LOCAL PLACEMENTS:' in debug


def test_derived_constraints_are_recomputed_and_region_hints_keep_palette():
    board = row_board()
    constraint = source(board, GroupKind.REGION, '0')
    analysis = analyze_local_placements(board, constraint)
    singleton = derive_subconstraint(analysis, {Cell(0, 0)})
    deduction, = forced_cells.find_deductions(board, (singleton,))
    context = DebugRenderContext.randomized(seed=17, use_emojis=True)
    assert context.glyph_for('0') in render_hint(deduction, 1, region_display=context.display_region)
    old = derive_local_constraints(board)
    board.apply(deduction)
    new = derive_local_constraints(board)
    assert old != new
    assert all(board.at(c) == U for constraint in new for c in constraint.cells)
    assert next_hint(board).difficulty == 1

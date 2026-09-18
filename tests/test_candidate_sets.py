"""Candidate cardinalities and immediate-neighbor proofs, without search."""
from dataclasses import FrozenInstanceError

import pytest

from double_queens import (
    Action, AdjacencyFact, Board, Cell, CellFact, CellState, ContradictionError,
    DebugRenderContext, GroupKind, QueenConstraint, Rule, best_deduction,
    derive_constraints, find_deductions, next_hint, render_board,
    render_deduction, render_hint,
)

U, Q, X = CellState.UNKNOWN, CellState.QUEEN, CellState.EXCLUDED


def candidate_board(kind=GroupKind.ROW, candidates=(3, 4), queens=(0,)):
    regions = [[str(r)] * 8 for r in range(8)]
    state = [[U] * 8 for _ in range(8)]
    for c in range(8):
        state[0][c] = Q if c in queens else U if c in candidates else X
    if kind == GroupKind.COLUMN:
        state = list(map(list, zip(*state)))
    elif kind == GroupKind.REGION:
        # Move one cell across the boundary: both regions remain contiguous.
        regions[1][3] = '0'
        state[1][3] = X
    return Board(regions, state)


def common_deduction(board, kind):
    return next(d for d in find_deductions(board)
                if d.rule == Rule.COMMON_NEIGHBOR_EXCLUSION
                and d.premises[0].group.kind == kind)


def test_constraint_normalization_and_immutability():
    cells = [Cell(0, 4), Cell(0, 3), Cell(0, 4)]
    constraint = QueenConstraint(cells, 1)
    cells.clear()
    assert constraint.cells == frozenset((Cell(0, 3), Cell(0, 4)))
    assert constraint == QueenConstraint(reversed(sorted(constraint.cells)), 1)
    assert hash(constraint)
    with pytest.raises(FrozenInstanceError):
        constraint.queen_count = 2
    assert QueenConstraint([], 0).cells == frozenset()


@pytest.mark.parametrize('cells,count', [([], 1), ([Cell(0, 0)], -1),
    ([Cell(0, 0)], 2), ([Cell(0, 0)], 1.0), ([Cell(0, 0)], True), (['L1C1'], 1)])
def test_constraint_rejects_invalid_cardinality_or_cells(cells, count):
    with pytest.raises(ValueError):
        QueenConstraint(cells, count)


@pytest.mark.parametrize('kind', list(GroupKind))
def test_group_constraints_and_common_neighbor_provenance(kind):
    board = candidate_board(kind)
    before = board.state
    constraints = derive_constraints(board)
    assert len(constraints) == 3 * board.size
    for constraint in constraints:
        source = constraint.source
        assert source.required_queens == 2
        assert constraint.cells == frozenset(board.unknown(source.group.cells))
        assert constraint.queen_count == 2 - len(board.queens(source.group.cells))
        assert source.facts == tuple(CellFact(c, board.at(c)) for c in source.group.cells)
    deduction = common_deduction(board, kind)
    candidates = (Cell(3, 0), Cell(4, 0)) if kind == GroupKind.COLUMN else (Cell(0, 3), Cell(0, 4))
    targets = ((Cell(3, 1), Cell(4, 1)) if kind == GroupKind.COLUMN else
               (Cell(1, 4),) if kind == GroupKind.REGION else (Cell(1, 3), Cell(1, 4)))
    assert deduction.constraint in constraints
    assert deduction.constraint.source == deduction.premises[0]
    assert deduction.constraint.cells == frozenset(candidates)
    assert deduction.constraint.queen_count == 1
    assert deduction.actions == tuple(Action(c, X) for c in targets)
    assert deduction.adjacencies == tuple(AdjacencyFact(t, c) for t in targets for c in candidates)
    assert deduction.premises[1].facts == tuple(CellFact(t, U) for t in targets)
    assert all(f.candidate in board.neighbors(f.target) for f in deduction.adjacencies)
    assert deduction.difficulty == 2 and board.state == before
    board.apply(deduction)
    assert all(board.at(c) == U for c in candidates)
    assert all(board.at(c) == X for c in targets)
    with pytest.raises(ValueError, match='stale'):
        board.apply(deduction)


@pytest.mark.parametrize('candidates,queens', [((3, 6), (0,)), ((3, 4, 7), (0,)),
                                             ((3, 4), (0, 7))])
def test_no_common_neighbor_without_universal_adjacency_or_positive_quota(candidates, queens):
    board = candidate_board(candidates=candidates, queens=queens)
    assert not any(d.rule == Rule.COMMON_NEIGHBOR_EXCLUSION for d in find_deductions(board))


@pytest.mark.parametrize('candidates', [(3,), (3, 5)])
def test_singleton_and_two_required_queens(candidates):
    board = candidate_board(candidates=candidates, queens=(0,) if len(candidates) == 1 else ())
    deduction = common_deduction(board, GroupKind.ROW)
    assert deduction.constraint.queen_count == len(candidates)
    assert Action(Cell(1, 4), X) in deduction.actions
    assert not set(candidates) & {a.cell.col for a in deduction.actions if a.cell.row == 0}
    assert next_hint(board).rule == Rule.FORCED_REMAINING_CELLS


def test_known_targets_are_not_reemitted_and_long_diagonals_are_untouched():
    board = candidate_board()
    deduction = common_deduction(board, GroupKind.ROW)
    # L3C6 is two diagonal steps from candidate L1C4, and two rows from
    # candidate L1C5: neither is an immediate neighbor, so no exclusion follows.
    assert Action(Cell(2, 5), X) not in deduction.actions
    board.apply(deduction)
    assert not any(d.rule == Rule.COMMON_NEIGHBOR_EXCLUSION for d in find_deductions(board))


def test_invalid_board_is_rejected_before_constraint_derivation():
    with pytest.raises(ContradictionError):
        derive_constraints(candidate_board(candidates=(), queens=(0,)))


def test_new_rule_ranks_after_elementary_rules_and_queries_are_pure():
    board = candidate_board()
    before = board.state
    deductions = find_deductions(board)
    assert find_deductions(board) == deductions
    assert next_hint(board) == best_deduction(reversed(deductions))
    assert next_hint(board).rule == Rule.QUEEN_ADJACENCY
    candidate_hints = [d for d in deductions if d.rule == Rule.COMMON_NEIGHBOR_EXCLUSION]
    assert candidate_hints
    assert best_deduction(candidate_hints) == best_deduction(reversed(candidate_hints))
    assert board.state == before


@pytest.mark.parametrize('kind', list(GroupKind))
def test_progressive_candidate_hints_use_only_structured_evidence(kind):
    board = candidate_board(kind)
    deduction = common_deduction(board, kind)
    hints = [render_hint(deduction, level) for level in range(1, 5)]
    assert len(set(hints)) == 4
    assert hints[0].startswith('Look at')
    assert 'still needs one queen' in hints[1] and 'touch both candidates?' in hints[1]
    assert 'must place one queen' in hints[2] and ('touches both cells' if len(deduction.actions) == 1 else 'touch both cells') in hints[2]
    for action in deduction.actions:
        assert str(action.cell) not in hints[0] + hints[1]
        assert str(action.cell) in hints[2]
    expected = {GroupKind.ROW: 'Exclude L2C4 and L2C5.',
                GroupKind.COLUMN: 'Exclude L4C2 and L5C2.',
                GroupKind.REGION: 'Exclude L2C5.'}
    assert hints[3] == expected[kind]
    debug = render_deduction(deduction)
    assert 'CONSTRAINT:' in debug and 'exactly 1' in debug
    for fact in deduction.adjacencies:
        assert f'{fact.target} touches {fact.candidate}' in debug
    # The deduction remains independently renderable after its board changes.
    board.apply(deduction)
    assert hints == [render_hint(deduction, level) for level in range(1, 5)]


def test_candidate_hints_share_debug_region_palette():
    board = candidate_board(GroupKind.REGION)
    deduction = common_deduction(board, GroupKind.REGION)
    context = DebugRenderContext.randomized(seed=31, use_emojis=True)
    text = render_board(board, context=context)
    glyph = context.glyph_for('0')
    assert glyph in text
    for level in (1, 2, 3):
        assert glyph in render_hint(deduction, level, region_display=context.display_region)
    assert render_hint(deduction, 4, region_display=context.display_region) == render_hint(deduction, 4)


def test_changed_source_evidence_is_rejected_atomically():
    board = candidate_board()
    deduction = common_deduction(board, GroupKind.ROW)
    state = [list(row) for row in board.state]
    state[0][3] = X
    changed = Board(board.regions, state)
    before = changed.state
    with pytest.raises(ValueError, match='stale'):
        changed.apply(deduction)
    assert changed.state == before


def test_changed_target_evidence_is_rejected_atomically():
    board = candidate_board()
    deduction = common_deduction(board, GroupKind.ROW)
    target = deduction.actions[0].cell
    assert board.at(target) == U
    assert target not in deduction.constraint.source.group.cells
    state = [list(row) for row in board.state]
    state[target.row][target.col] = X
    changed = Board(board.regions, state)
    changed.validate()
    assert all(changed.at(c) == board.at(c) for c in board.cells() if c != target)
    assert deduction.constraint in derive_constraints(changed)
    before = changed.state
    with pytest.raises(ValueError, match='stale'):
        changed.apply(deduction)
    assert changed.state == before


@pytest.mark.parametrize('rule', [Rule.FORCED_REMAINING_CELLS,
                                  Rule.QUEEN_ADJACENCY, Rule.COMPLETED_GROUP])
def test_elementary_hint_progression_preserves_reason_and_explicit_action(rule):
    board = candidate_board(candidates=(3,) if rule == Rule.FORCED_REMAINING_CELLS else (3, 4),
                            queens=(0, 7) if rule == Rule.COMPLETED_GROUP else (0,))
    deduction = next(d for d in find_deductions(board) if d.rule == rule)
    levels = [render_hint(deduction, level) for level in range(1, 5)]
    assert len(set(levels)) == 4
    assert levels[0].startswith('Look')
    for action in deduction.actions:
        assert str(action.cell) not in levels[0] + levels[1]
        assert str(action.cell) in levels[2]
    if rule == Rule.QUEEN_ADJACENCY:
        assert 'Queens cannot touch' in levels[1]
        assert 'touch the queen' in levels[2]
    else:
        assert ('still needs one queen' if rule == Rule.FORCED_REMAINING_CELLS
                else 'already contains its 2 required queens') in levels[1]
        assert ('remains available' if rule == Rule.FORCED_REMAINING_CELLS
                else 'already contains its 2 required queens') in levels[2]
    assert levels[3].startswith('Place a queen at' if rule == Rule.FORCED_REMAINING_CELLS else 'Exclude ')
    assert levels[3].count('.') == 1
    assert all(str(a.cell) in levels[3] for a in deduction.actions)

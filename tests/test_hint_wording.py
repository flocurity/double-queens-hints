"""Player explanations consume proofs without exposing unrelated conclusions."""
from dataclasses import replace

import pytest

from double_queens import (
    Action, Cell, CellState, Deduction, InclusionProof, LocalPlacements,
    QueenConstraint, Rule, analyze_local_placements,
    derive_subconstraint, next_hint, render_hint,
)
from double_queens.hints.renderer import _count
from double_queens.rules import completed_group, forced_cells, candidate_sets
from test_candidate_sets import candidate_board, common_deduction
from test_local_constraints import row_board, source
from test_known_games import make_known_game_001, make_known_game_002
from double_queens import GroupKind

Q, X = CellState.QUEEN, CellState.EXCLUDED


@pytest.mark.parametrize('noun', ['queen', 'candidate', 'cell'])
@pytest.mark.parametrize('count', [0, 1, 2])
def test_count_grammar(noun, count):
    assert _count(count, noun) == f"{'one' if count == 1 else count} {noun}{'' if count == 1 else 's'}"


@pytest.mark.parametrize('count,expected', [
    (1, 'L10C1'), (2, 'L10C1 and L10C2'), (3, 'L10C1, L10C2, and L10C3'),
])
@pytest.mark.parametrize('state', [Q, X])
def test_actions_are_aggregated_with_canonical_coordinates(count, expected, state):
    base = next_hint(candidate_board())
    d = replace(base, actions=tuple(Action(Cell(9, c), state) for c in range(count)))
    prefix = ('Place a queen at ' if count == 1 else 'Place queens at ') if state == Q else 'Exclude '
    assert render_hint(d, 4) == prefix + expected + '.'


def test_singleton_and_plural_adjacency_grammar():
    d = next_hint(candidate_board())
    single = replace(d, actions=d.actions[:1])
    assert 'touches the queen' in render_hint(single, 3)
    assert 'it cannot contain a queen' in render_hint(single, 3)
    assert 'all touch the queen' in render_hint(d, 3)
    assert 'none of them can contain a queen' in render_hint(d, 3)


@pytest.mark.parametrize('columns', [(3,), (3, 5)])
def test_forced_remaining_cells_match_remaining_quota(columns):
    board = candidate_board(candidates=columns, queens=(0,) if len(columns) == 1 else ())
    d = next(d for d in forced_cells.find_deductions(board))
    assert ('one queen' if len(columns) == 1 else '2 queens') in render_hint(d, 2)
    assert ('remains available' if len(columns) == 1 else 'remain available') in render_hint(d, 3)


@pytest.mark.parametrize('columns', [(3,), (3, 4)])
def test_completed_groups_ask_about_consequence_not_unknown_count(columns):
    board = candidate_board(candidates=columns, queens=(0, 7))
    d = completed_group.find_deductions(board)[0]
    assert 'already contains its 2 required queens' in render_hint(d, 2)
    assert 'What does that mean' in render_hint(d, 2)
    assert ('cannot contain a queen' if len(columns) == 1 else 'cannot contain queens') in render_hint(d, 3)


def test_common_neighbors_preserve_exact_two_queen_quota():
    d = common_deduction(candidate_board(candidates=(3, 4, 5), queens=()), GroupKind.ROW)
    assert 'must place 2 queens' in render_hint(d, 3)
    assert 'touches all cells' in render_hint(d, 3)


@pytest.mark.parametrize('count', [0, 1])
def test_inclusion_zero_and_nonzero_difference_names_groups(count):
    board = row_board()
    large = source(board)
    small = QueenConstraint({Cell(0, 3), Cell(0, 4)}, 2-count,
                            source=source(board, GroupKind.REGION, '0').source)
    result = QueenConstraint({Cell(0, 0)}, count, derivation=InclusionProof(small, large))
    d = Deduction((Action(Cell(0, 0), Q if count else X),),
                  Rule.FORCED_REMAINING_CELLS if count else Rule.COMPLETED_GROUP,
                  (large.source,), constraint=result)
    assert 'region 0 and row 1' in render_hint(d, 1)
    assert 'How many queens can remain outside region 0?' in render_hint(d, 2)
    assert ('account for everything' if count == 0 else 'leaves one queen') in render_hint(d, 3)
    assert 'L1C1' in render_hint(d, 3)


@pytest.mark.parametrize('columns,targets', [
    ((0, 3, 4), (0,)), ((0, 2), (0, 2)), ((0, 3, 4, 5, 6, 7), (0,)),
])
def test_local_forced_queen_explanations_are_bounded(columns, targets):
    board = row_board(columns)
    analysis = analyze_local_placements(board, source(board))
    # For the many-placement wording case, a self-contained proof fixture
    # records placements all containing the selected queen, without solving.
    if len(columns) > 3:
        analysis = replace(analysis, placements=tuple(frozenset((Cell(0, 0), Cell(0, c))) for c in columns[1:]))
    constraint = derive_subconstraint(analysis, {Cell(0, c) for c in targets})
    d = forced_cells.find_deductions(board, (constraint,))[0]
    text = render_hint(d, 3)
    assert 'must contain' in text
    if len(analysis.placements) == 1:
        assert 'only valid placement' in text
        assert '{L1C1 and L1C3}' in text
    else:
        assert 'Every valid placement' in text
        assert '{' not in text
        assert all(str(Cell(0, c)) not in text for c in columns if c not in targets)


@pytest.mark.parametrize('targets', [(1,), (1, 3)])
def test_impossible_cells_are_target_focused(targets):
    board = row_board((0, 1, 2, 3, 4))
    native = source(board)
    analysis = LocalPlacements(native, (frozenset((Cell(0, 0), Cell(0, 4))),), (), (), (native.source,))
    constraint = derive_subconstraint(analysis, {Cell(0, c) for c in targets})
    d = completed_group.find_deductions(board, (constraint,))[0]
    text = render_hint(d, 3)
    assert 'cannot be part of any valid placement' in text
    assert 'L1C1' not in text and 'L1C5' not in text
    assert '{' not in text


def test_derived_pair_is_explained_as_exact_knowledge():
    board = row_board()
    analysis = analyze_local_placements(board, source(board))
    pair = derive_subconstraint(analysis, {Cell(0, 3), Cell(0, 4)})
    d = candidate_sets.find_deductions(board, (pair,))[0]
    text = render_hint(d, 3)
    assert 'Exactly one of L1C4 and L1C5 must contain a queen' in text
    assert 'touch both cells' in text
    assert 'L1C1' not in text and '{' not in text


def test_known_games_wording_preserves_replay_and_hides_sibling_exclusions():
    for make, count, advanced in ((make_known_game_001, 32, 0), (make_known_game_002, 55, 16)):
        board = make()
        history = []
        while not board.is_solved():
            d = next_hint(board)
            assert d is not None
            hints = [render_hint(d, level) for level in range(1, 5)]
            assert len(set(hints)) == 4
            assert all(bad not in text for text in hints for bad in
                       ('(s)', 'nonempty queen set', 'Every placement contains 0', 'All its cells', 'candidate set'))
            if make == make_known_game_002 and len(history) == 13:
                assert d.actions == (Action(Cell(2, 5), X),)
                assert 'L3C6' in hints[2]
                assert 'L4C6' not in hints[2]
                assert '{' not in hints[2]
            history.append(d)
            board.apply(d)
            assert hints == [render_hint(d, level) for level in range(1, 5)]
        assert len(history) == count
        assert sum(d.difficulty == 3 for d in history) == advanced
        assert len(board.queens(board.cells())) == board.size * 2
        replay = make()
        for d in history:
            assert next_hint(replay) == d
            replay.apply(d)
        assert replay.state == board.state

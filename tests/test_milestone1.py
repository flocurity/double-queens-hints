import pytest

from debug_boards import debug_boards

from double_queens import (
    Action, Board, Cell, CellFact, CellState, ContradictionError, Deduction,
    GroupKind, Premise, Rule, SolveStatus, best_deduction, find_deductions,
    next_hint, render_board, render_deduction, render_hint, solve_logically,
)
from double_queens.log import get_logger

log = get_logger(__name__)
U, Q, X = CellState.UNKNOWN, CellState.QUEEN, CellState.EXCLUDED


def board_with(changes=(), size=8, regions=None):
    state = [[U] * size for _ in range(size)]
    for r, c, state_value in changes:
        state[r][c] = state_value
    return Board(regions or [[f"region_{r}" for _ in range(size)] for r in range(size)], state)


def deduction_for(board, rule, kind=None):
    return next(d for d in find_deductions(board) if d.rule == rule
                and (kind is None or d.premises[0].group.kind == kind))


@debug_boards
def test_model_helpers_and_copy():
    regions = [[str(r)] * 8 for r in range(8)]
    state = [[U] * 8 for _ in range(8)]
    board = Board(regions, state)
    regions[0][0] = "changed"
    state[0][0] = Q
    assert board.at(Cell(0, 0)) == U
    assert board.regions[0][0] == "0"
    assert str(Cell(5, 4)) == "L6C5"
    assert board.row(0) == board.region("0")
    assert board.column(2) == tuple(Cell(r, 2) for r in range(8))
    assert len(board.unknown(board.cells())) == 64
    assert not board.queens(board.cells()) and not board.excluded(board.cells())
    with pytest.raises(KeyError):
        board.region("absent")
    with pytest.raises(IndexError):
        board.at(Cell(-1, 0))


@pytest.mark.parametrize("cell,count", [(Cell(0, 0), 3), (Cell(0, 3), 5), (Cell(3, 3), 8)])
@debug_boards
def test_neighbors(cell, count):
    board = board_with()
    assert len(board.neighbors(cell)) == count
    assert cell not in board.neighbors(cell)


@pytest.mark.parametrize("regions,state", [([], None), ([["a", "b"]], None),
    ([[""]], None), ([["a"]], [[7]]), ([["a"]], [])])
@debug_boards
def test_malformed_board(regions, state):
    with pytest.raises(ValueError):
        Board(regions, state)


@pytest.mark.parametrize("kind", list(GroupKind))
@pytest.mark.parametrize("rule", [Rule.COMPLETED_GROUP, Rule.FORCED_REMAINING_CELLS])
@debug_boards
def test_group_rules_positive_negative_and_provenance(kind, rule):
    def location(i):
        return (i, 0) if kind == GroupKind.COLUMN else (0, i)
    changes = [( *location(0), Q)]
    if rule == Rule.COMPLETED_GROUP:
        changes.append((*location(3), Q))
    else:
        changes.extend((*location(i), X) for i in range(8) if i not in (0, 3))
    board = board_with(changes)
    before = board.state
    deduction = deduction_for(board, rule, kind)
    assert board.state == before
    assert deduction.difficulty == 1
    premise = deduction.premises[0]
    assert premise.required_queens == 2
    assert premise.facts == tuple(CellFact(c, board.at(c)) for c in premise.group.cells)
    expected = X if rule == Rule.COMPLETED_GROUP else Q
    assert deduction.actions == tuple(Action(c, expected) for c in board.unknown(premise.group.cells))
    negative = board_with([(*location(0), Q)])
    assert not any(d.rule == rule and d.premises[0].group.kind == kind for d in find_deductions(negative))


@debug_boards
def test_forces_two_cells_without_propagation():
    board = board_with([(0, c, X) for c in range(8) if c not in (0, 3)])
    deduction = deduction_for(board, Rule.FORCED_REMAINING_CELLS)
    assert deduction.actions == (Action(Cell(0, 0), Q), Action(Cell(0, 3), Q))
    board.apply(deduction)
    assert board.at(Cell(1, 0)) == U
    assert any(d.rule == Rule.QUEEN_ADJACENCY for d in find_deductions(board))


@pytest.mark.parametrize("cell", [Cell(0, 0), Cell(0, 3), Cell(3, 3)])
@debug_boards
def test_adjacency_positive_negative_and_boundary(cell):
    board = board_with([(cell.row, cell.col, Q)])
    deduction = deduction_for(board, Rule.QUEEN_ADJACENCY)
    assert deduction.actions == tuple(Action(c, X) for c in board.neighbors(cell))
    assert deduction.premises[0].facts[0] == CellFact(cell, Q)
    assert not find_deductions(board_with())
    cleared = board_with([(cell.row, cell.col, Q)] + [(c.row, c.col, X) for c in board.neighbors(cell)])
    assert not any(d.rule == Rule.QUEEN_ADJACENCY for d in find_deductions(cleared))


@debug_boards
def test_long_diagonals_allowed():
    board = board_with([(0, 0, Q), (2, 2, Q)])
    board.validate()
    assert all(Action(Cell(4, 4), X) not in d.actions for d in find_deductions(board))


@pytest.mark.parametrize("kind", list(GroupKind))
@pytest.mark.parametrize("too_many", [True, False])
@debug_boards
def test_group_contradictions(kind, too_many):
    regions = [[str(c if kind == GroupKind.COLUMN else r) for c in range(8)] for r in range(8)]
    if kind == GroupKind.REGION:
        regions = [[str((r + c) % 8) for c in range(8)] for r in range(8)]
        cells = [Cell(r, (-r) % 8) for r in range(8)]
    else:
        cells = list(board_with().column(0) if kind == GroupKind.COLUMN else board_with().row(0))
    selected = cells[::3] if too_many else cells[:-1]
    board = board_with([(c.row, c.col, Q if too_many else X) for c in selected], regions=regions)
    with pytest.raises(ContradictionError):
        find_deductions(board)


@pytest.mark.parametrize("neighbor", [Cell(0, 1), Cell(1, 0), Cell(1, 1)])
@debug_boards
def test_adjacent_queen_contradiction(neighbor):
    with pytest.raises(ContradictionError, match="Adjacent"):
        board_with([(0, 0, Q), (neighbor.row, neighbor.col, Q)]).validate()


@debug_boards
def test_region_total_contradiction():
    with pytest.raises(ContradictionError, match="N regions"):
        Board([["one"] * 8 for _ in range(8)]).validate()


def manual(actions):
    return Deduction(tuple(actions), Rule.QUEEN_ADJACENCY,
                     (Premise((CellFact(Cell(7, 7), U),)),))


@pytest.mark.parametrize("old,new", [(Q, X), (X, Q)])
@debug_boards
def test_apply_conflict_is_atomic(old, new):
    board = board_with([(0, 0, old)])
    before = board.state
    with pytest.raises(ContradictionError):
        board.apply(manual([Action(Cell(3, 3), X), Action(Cell(0, 0), new)]))
    assert board.state == before


@debug_boards
def test_apply_invalid_result_and_stale_hint():
    board = board_with([(0, 0, Q)])
    before = board.state
    with pytest.raises(ContradictionError):
        board.apply(manual([Action(Cell(0, 1), Q)]))
    assert board.state == before
    deduction = next_hint(board)
    board.apply(deduction)
    with pytest.raises(ValueError, match="stale"):
        board.apply(deduction)
    with pytest.raises(ValueError):
        Action(Cell(0, 0), U)


@debug_boards
def test_ranking_is_explicit_and_query_is_pure():
    board = board_with([(0, 0, Q), (0, 3, Q)] + [(4, c, X) for c in range(8) if c not in (1, 5)])
    before = board.state
    deductions = find_deductions(board)
    assert {d.rule for d in deductions} == {
        Rule.FORCED_REMAINING_CELLS, Rule.QUEEN_ADJACENCY, Rule.COMPLETED_GROUP,
    }
    assert next_hint(board).rule == Rule.FORCED_REMAINING_CELLS
    assert best_deduction(reversed(deductions)) == next_hint(board)
    assert board.state == before
    assert best_deduction([]) is None


@pytest.mark.parametrize("rule", [Rule.FORCED_REMAINING_CELLS,
                                  Rule.QUEEN_ADJACENCY, Rule.COMPLETED_GROUP])
@debug_boards
def test_hint_levels_and_debug(rule):
    changes = [(0, 0, Q)]
    if rule == Rule.COMPLETED_GROUP:
        changes += [(0, 3, Q)]
    if rule == Rule.FORCED_REMAINING_CELLS:
        changes += [(0, c, X) for c in range(8) if c not in (0, 3)]
    deduction = deduction_for(board_with(changes), rule)
    hints = [render_hint(deduction, level) for level in range(1, 5)]
    assert len(set(hints)) == 4
    log.hint(hints[0], level=1)
    log.hint(hints[1], level=2)
    log.hint(hints[2], level=3)
    log.hint(hints[3], level=4)
    log.hint(hints)
    assert hints[0].startswith("Look")
    for action in deduction.actions:
        assert str(action.cell) in hints[2] and str(action.cell) in hints[3]
        assert str(action.cell) not in hints[0] and str(action.cell) not in hints[1]
    debug = render_deduction(deduction)
    assert rule.value in debug and "PREMISES:" in debug and "CONCLUSION:" in debug
    with pytest.raises(ValueError):
        render_hint(deduction, 0)


@debug_boards
def test_debug_board_dynamic_and_pure():
    board = board_with([(0, 0, Q), (0, 3, Q), (1, 0, X)], size=13)
    before = board.state
    rendered = render_board(board, use_emojis=True)
    assert rendered.splitlines()[0].split('|')[0].endswith('10111213')
    assert rendered.splitlines()[-1].startswith('13 ')
    assert "Color Region Legend" not in rendered
    assert not any(line.startswith("- ") for line in rendered.splitlines())
    assert "Queen(s)" in rendered and "×2" in rendered
    assert "👑" in rendered and "❌" in rendered and "|-" in rendered
    assert board.state == before


@debug_boards
def test_solver_stalls_without_guessing(monkeypatch):
    from double_queens import engine
    board = board_with([(0, 0, Q)])
    before = board.state
    calls = []
    def no_hint(current):
        calls.append(current)
        return None
    monkeypatch.setattr(engine, "next_hint", no_hint)
    result = solve_logically(board)
    assert calls == [board]
    assert result.status == SolveStatus.LOGIC_STALLED and not result.history
    assert board.state == before and result.reason


@debug_boards
def test_solver_solves_with_replayable_hints():
    # Hand-constructed valid placement, not a search-generated test oracle.
    pairs = [(0, 2), (4, 6), (8, 0), (2, 4), (6, 8),
             (1, 3), (5, 7), (9, 1), (3, 5), (7, 9)]
    changes = [(r, c, X) for r in range(10) for c in range(10) if c not in pairs[r]]
    board = board_with(changes, size=10)
    replay = board_with(changes, size=10)
    result = solve_logically(board)
    assert result.solved and result.board is board and result.reason is None
    assert result.history
    for deduction in result.history:
        assert deduction == next_hint(replay)
        replay.apply(deduction)
    assert replay.state == board.state and replay.is_solved()
    assert solve_logically(board).history == ()


@debug_boards
def test_empty_board_stalls():
    result = solve_logically(board_with())
    assert not result.solved and result.status == SolveStatus.LOGIC_STALLED


@debug_boards
def test_finished_group_produces_no_empty_deductions():
    board = board_with([(0, c, Q if c in (0, 3) else X) for c in range(8)])
    assert not any(d.premises[0].group and d.premises[0].group.cells == board.row(0)
                   for d in find_deductions(board))


@debug_boards
def test_apply_out_of_bounds_and_conflicting_batch_roll_back():
    board = board_with()
    before = board.state
    with pytest.raises(IndexError):
        board.apply(manual([Action(Cell(0, 0), X), Action(Cell(8, 0), Q)]))
    assert board.state == before
    with pytest.raises(ContradictionError):
        board.apply(manual([Action(Cell(0, 0), X), Action(Cell(0, 0), Q)]))
    assert board.state == before


@debug_boards
def test_debug_queen_summary_tracks_different_regions():
    regions = [[str(c) for c in range(8)] for _ in range(8)]
    board = board_with([(0, 0, Q), (0, 3, Q)], regions=regions)
    line = render_board(board, use_emojis=True).splitlines()[1]
    assert line.split('|')[1] == '🔴  🟡'


@debug_boards
def test_debug_board_text_mode():
    board = board_with([(0, 0, Q), (0, 3, Q), (1, 0, X)])
    rendered = render_board(board, use_emojis=False)
    assert rendered.isascii()
    assert 'Q region_0' in rendered
    assert 'X region_1' in rendered
    assert 'region_2' in rendered
    assert rendered.splitlines()[1].split('|')[1] == 'region_0 x2'


@debug_boards
def test_debug_board_emoji_cells_have_no_region_labels():
    board = board_with([(0, 0, Q), (1, 0, X)])
    rendered = render_board(board, use_emojis=True)
    grid = '\n'.join(rendered.splitlines()[1:])
    assert 'region_' not in grid and '[R' not in grid
    assert all(glyph in grid for glyph in ('👑', '❌', '🔴'))


@pytest.mark.parametrize('encoding,term,expected', [
    ('utf-8', 'xterm-256color', True), ('ascii', 'xterm', False),
    ('utf-8', 'dumb', False), (None, 'xterm', False),
    ('invalid-encoding', 'xterm', False),
])
@debug_boards
def test_debug_board_terminal_detection(monkeypatch, encoding, term, expected):
    from types import SimpleNamespace
    from double_queens.hints import debug
    board = board_with()
    with monkeypatch.context() as patch:
        patch.setattr(debug.sys, 'stdout', SimpleNamespace(encoding=encoding))
        patch.setenv('TERM', term)
        rendered = render_board(board)
        forced = render_board(board, use_emojis=not expected)
    assert ('🔴' in rendered) == expected
    assert ('🔴' in forced) == (not expected)

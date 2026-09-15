"""Elementary rules on contiguous, irregular regions; no solution search."""
from collections.abc import Callable
from dataclasses import dataclass

import pytest

from debug_boards import debug_boards
from double_queens import (
    Action, Board, Cell, CellFact, CellState, Deduction, GroupKind, Rule,
    best_deduction, find_deductions, next_hint, render_board, render_hint,
)

U, Q, X = CellState.UNKNOWN, CellState.QUEEN, CellState.EXCLUDED


@dataclass(frozen=True)
class IrregularLayout:
    regions: tuple[tuple[str, ...], ...]
    queens: frozenset[Cell]
    transform: Callable[[Cell], Cell]

    def board(self, changes: dict[Cell, CellState] | None = None) -> Board:
        state = [[U] * 10 for _ in range(10)]
        for cell, value in (changes or {}).items():
            state[cell.row][cell.col] = value
        return Board(self.regions, state)


@pytest.fixture(params=['stepped', 'transposed', 'rotated'])
def irregular_layout(request: pytest.FixtureRequest) -> IrregularLayout:
    # Each pair of rows contains two regions with a stepped shared boundary.
    # All ten regions span rows AND columns and are orthogonally contiguous.
    rows = (
        'ABBBBBBBBB',
        'AAAAABBBBB',
        'CCCCDDDDDD',
        'CCCDDDDDDD',
        'EEEEEFFFFF',
        'EEEEFFFFFF',
        'GGGGGGHHHH',
        'GGGGHHHHHH',
        'IIIIIIJJJJ',
        'IIIIIIIJJJ',
    )
    # A fixed witness validates the fixtures, never supplies engine deductions.
    pairs = [(0, 2), (4, 6), (8, 0), (2, 4), (6, 8),
             (1, 3), (5, 7), (9, 1), (3, 5), (7, 9)]
    transforms = {
        'stepped': lambda c: c,
        'transposed': lambda c: Cell(c.col, c.row),
        'rotated': lambda c: Cell(c.col, 9 - c.row),
    }
    transform = transforms[request.param]
    regions = [[''] * 10 for _ in range(10)]
    for r, row in enumerate(rows):
        for c, region in enumerate(row):
            target = transform(Cell(r, c))
            regions[target.row][target.col] = region
    queens = frozenset(transform(Cell(r, c)) for r, pair in enumerate(pairs) for c in pair)
    return IrregularLayout(tuple(tuple(row) for row in regions), queens, transform)


def group_deduction(board: Board, rule: Rule, kind: GroupKind, index: int | str) -> Deduction:
    return next(d for d in find_deductions(board) if d.rule == rule
                and d.premises[0].group is not None
                and d.premises[0].group.kind == kind
                and d.premises[0].group.index == index)


@debug_boards
def test_layouts_are_contiguous_irregular_and_have_valid_witness(irregular_layout):
    board = irregular_layout.board()
    assert len(board.region_ids) == 10
    for region in board.region_ids:
        cells = set(board.region(region))
        rows, cols = {c.row for c in cells}, {c.col for c in cells}
        assert len(rows) > 1 and len(cols) > 1
        assert len(cells) < len(rows) * len(cols)  # Not a rectangle.
        visited = {next(iter(cells))}
        pending = list(visited)
        while pending:
            cell = pending.pop()
            for neighbor in cells - visited:
                if abs(cell.row - neighbor.row) + abs(cell.col - neighbor.col) == 1:
                    visited.add(neighbor)
                    pending.append(neighbor)
        assert visited == cells
    solved = irregular_layout.board({c: Q if c in irregular_layout.queens else X for c in board.cells()})
    assert solved.is_solved()
    assert find_deductions(board) == []


@debug_boards
def test_irregular_region_forces_last_queen_with_exact_provenance(irregular_layout):
    empty = irregular_layout.board()
    queen = irregular_layout.transform(Cell(0, 0))
    target = irregular_layout.transform(Cell(1, 4))
    changes = {c: X for c in empty.region('A') if c not in (queen, target)}
    changes[queen] = Q
    board = irregular_layout.board(changes)
    before = board.state
    deduction = group_deduction(board, Rule.FORCED_REMAINING_CELLS, GroupKind.REGION, 'A')
    assert deduction.actions == (Action(target, Q),)
    premise = deduction.premises[0]
    assert premise.group.cells == empty.region('A')
    assert premise.required_queens == 2
    assert premise.facts == tuple(CellFact(c, board.at(c)) for c in empty.region('A'))
    assert board.state == before
    assert render_hint(deduction, 1) == 'Look at region A.'
    assert str(target) not in render_hint(deduction, 2)
    assert str(target) in render_hint(deduction, 3)
    assert render_hint(deduction, 4) == f'Place a queen at {target}.'
    board.apply(deduction)
    assert board.at(target) == Q
    assert all(board.at(c) == before[c.row][c.col] for c in board.cells() if c != target)
    # Restore another unknown: the region alone no longer forces either cell.
    del changes[next(c for c in changes if changes[c] == X)]
    negative = irregular_layout.board(changes)
    assert not any(d.rule == Rule.FORCED_REMAINING_CELLS and d.premises[0].group.index == 'A'
                   for d in find_deductions(negative))


@debug_boards
def test_irregular_region_becomes_completed_and_excludes_only_its_cells(irregular_layout):
    first, second = (irregular_layout.transform(c) for c in (Cell(0, 0), Cell(1, 4)))
    board = irregular_layout.board({first: Q})
    assert not any(d.rule == Rule.COMPLETED_GROUP for d in find_deductions(board))
    # A second confirmed queen is supplied as puzzle input, not an invented deduction.
    board = irregular_layout.board({first: Q, second: Q})
    before = board.state
    deduction = group_deduction(board, Rule.COMPLETED_GROUP, GroupKind.REGION, 'A')
    expected = tuple(c for c in board.region('A') if c not in (first, second))
    assert deduction.actions == tuple(Action(c, X) for c in expected)
    assert {f.cell for f in deduction.premises[0].facts if f.state == Q} == {first, second}
    board.apply(deduction)
    assert all(board.at(c) == X for c in expected)
    assert all(board.at(c) == before[c.row][c.col] for c in board.cells() if c not in expected)
    assert not any(d.rule == Rule.COMPLETED_GROUP and d.premises[0].group.index == 'A'
                   for d in find_deductions(board))


@debug_boards
def test_row_column_region_rules_coexist_and_rank_explicitly(irregular_layout):
    empty = irregular_layout.board()
    transform = irregular_layout.transform
    changes = {c: X for c in empty.region('A') if c not in irregular_layout.queens}
    changes[transform(Cell(0, 0))] = Q
    for original in (Cell(8, 3), Cell(8, 5), Cell(7, 9), Cell(9, 9)):
        changes[transform(original)] = Q
    board = irregular_layout.board(changes)
    before = board.state
    deductions = find_deductions(board)
    assert {d.rule for d in deductions} == set(Rule)
    for deduction in deductions:
        for action in deduction.actions:
            assert (action.cell in irregular_layout.queens) == (action.state == Q)
    for kind in (GroupKind.ROW, GroupKind.COLUMN):
        completed = [d for d in deductions if d.rule == Rule.COMPLETED_GROUP
                     and d.premises[0].group.kind == kind]
        assert completed
        for deduction in completed:
            group = deduction.premises[0].group
            assert len({board.regions[c.row][c.col] for c in group.cells}) > 1
            assert deduction.actions == tuple(Action(c, X) for c in board.unknown(group.cells))
            assert deduction.premises[0].facts == tuple(CellFact(c, board.at(c)) for c in group.cells)
    assert next_hint(board).rule == Rule.FORCED_REMAINING_CELLS
    assert best_deduction(reversed(deductions)) == next_hint(board)
    exclusions = [d for d in deductions if d.rule != Rule.FORCED_REMAINING_CELLS]
    assert best_deduction(exclusions).rule == Rule.QUEEN_ADJACENCY
    assert board.state == before


@debug_boards
def test_adjacency_crosses_irregular_region_boundaries(irregular_layout):
    queen = irregular_layout.transform(Cell(1, 4))
    board = irregular_layout.board({queen: Q})
    expected = tuple(sorted(irregular_layout.transform(Cell(r, c))
                            for r in (0, 1, 2) for c in (3, 4, 5) if (r, c) != (1, 4)))
    deduction = next(d for d in find_deductions(board) if d.rule == Rule.QUEEN_ADJACENCY)
    assert deduction.actions == tuple(Action(c, X) for c in expected)
    assert len({board.regions[c.row][c.col] for c in expected}) >= 3
    assert deduction.premises[0].facts[0] == CellFact(queen, Q)
    board.apply(deduction)
    assert all(board.at(c) == X for c in expected)
    distant = irregular_layout.transform(Cell(3, 6))
    assert board.at(distant) == U  # Longer diagonals remain available.


@debug_boards
def test_render_irregular_board_without_legend(irregular_layout):
    queen = irregular_layout.transform(Cell(1, 4))
    excluded = irregular_layout.transform(Cell(0, 2))
    board = irregular_layout.board({queen: Q, excluded: X})
    before = board.state
    text = render_board(board, use_emojis=False)
    emojis = render_board(board, use_emojis=True)
    print('\nRealistic irregular board:\n' + emojis)
    assert 'Color Region Legend' not in text + emojis
    rows = [line.split('|')[2:-2] for line in text.splitlines() if '**Line ' in line]
    assert len(rows) == 10 and all(len(row) == 10 for row in rows)
    for r in range(10):
        for c in range(10):
            prefix = 'Q ' if Cell(r, c) == queen else 'X ' if Cell(r, c) == excluded else ''
            assert rows[r][c].strip() == prefix + irregular_layout.regions[r][c]
    assert emojis.count('👑') == 1 and emojis.count('❌') == 1
    queen_row = next(line for line in text.splitlines() if f'**Line {queen.row + 1:02d}**' in line)
    assert queen_row.split('|')[-2].strip() == 'A'
    assert board.state == before

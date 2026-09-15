"""The sole source of logical solving intelligence."""
from collections.abc import Iterable

from .board import Board
from .deduction import Deduction, Rule
from .rules import adjacency, completed_group, forced_cells

_PRIORITY = {Rule.FORCED_REMAINING_CELLS: 0, Rule.QUEEN_ADJACENCY: 1,
             Rule.COMPLETED_GROUP: 2}


def _rank(deduction: Deduction) -> tuple:
    return (deduction.difficulty, _PRIORITY[deduction.rule],
            sum(len(p.facts) for p in deduction.premises), -len(deduction.actions),
            tuple((a.cell.row, a.cell.col, a.state.value) for a in deduction.actions),
            tuple(p.group.label if p.group else "" for p in deduction.premises))


def find_deductions(board: Board) -> list[Deduction]:
    board.validate()
    return sorted(forced_cells.find_deductions(board)
                  + adjacency.find_deductions(board)
                  + completed_group.find_deductions(board), key=_rank)


def best_deduction(deductions: Iterable[Deduction]) -> Deduction | None:
    return min(deductions, key=_rank, default=None)


def next_hint(board: Board) -> Deduction | None:
    return best_deduction(find_deductions(board))

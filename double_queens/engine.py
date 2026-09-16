"""The sole source of logical solving intelligence."""
from collections.abc import Iterable
from dataclasses import fields, is_dataclass
from enum import Enum

from .board import Board
from .deduction import Deduction, Rule
from .rules import adjacency, candidate_sets, completed_group, forced_cells, local_constraints

_PRIORITY = {Rule.FORCED_REMAINING_CELLS: 0, Rule.QUEEN_ADJACENCY: 1,
             Rule.COMPLETED_GROUP: 2, Rule.COMMON_NEIGHBOR_EXCLUSION: 3,
             Rule.LOCAL_PLACEMENT_EXCLUSION: 4}


def _evidence_key(value) -> tuple:
    """Canonical structural tie-breaker, independent of set iteration order."""
    if is_dataclass(value):
        return (type(value).__name__, tuple(_evidence_key(getattr(value, f.name)) for f in fields(value)))
    if isinstance(value, frozenset):
        return ("set", tuple(sorted(_evidence_key(v) for v in value)))
    if isinstance(value, tuple):
        return ("tuple", tuple(_evidence_key(v) for v in value))
    if isinstance(value, Enum):
        return (type(value).__name__, str(value.value))
    return (type(value).__name__, str(value))


def _rank(deduction: Deduction) -> tuple:
    return (deduction.difficulty, _PRIORITY[deduction.rule],
            sum(len(p.facts) for p in deduction.premises), -len(deduction.actions),
            tuple((a.cell.row, a.cell.col, a.state.value) for a in deduction.actions),
            tuple(p.group.label if p.group else "" for p in deduction.premises),
            _evidence_key((deduction.constraint, deduction.local_placements, deduction.coverage)))


def find_deductions(board: Board) -> list[Deduction]:
    """Return M1/M2 deductions when available, otherwise the local M3 tier."""
    board.validate()
    elementary = (forced_cells.find_deductions(board)
                  + adjacency.find_deductions(board)
                  + completed_group.find_deductions(board)
                  + candidate_sets.find_deductions(board))
    return sorted(elementary or local_constraints.find_deductions(board), key=_rank)


def best_deduction(deductions: Iterable[Deduction]) -> Deduction | None:
    return min(deductions, key=_rank, default=None)


def next_hint(board: Board) -> Deduction | None:
    return best_deduction(find_deductions(board))

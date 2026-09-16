"""Residual group cardinalities and common immediate-neighbor exclusions."""
from ..board import Board, CellState
from ..deduction import (
    Action, AdjacencyFact, CellFact, Deduction, Premise, QueenConstraint, Rule,
)


def derive_constraints(board: Board) -> tuple[QueenConstraint, ...]:
    """Snapshot each group's unknown cells and remaining quota, without mutation."""
    board.validate()
    return tuple(
        QueenConstraint(
            frozenset(board.unknown(group.cells)),
            2 - len(board.queens(group.cells)),
            Premise(tuple(CellFact(c, board.at(c)) for c in group.cells), group, 2),
        )
        for group in board.groups()
    )


def find_deductions(board: Board) -> list[Deduction]:
    result = []
    for constraint in derive_constraints(board):
        if constraint.queen_count == 0:
            continue
        candidates = sorted(constraint.cells)
        common = set(board.neighbors(candidates[0]))
        for cell in candidates[1:]:
            common.intersection_update(board.neighbors(cell))
        targets = board.unknown(sorted(common))
        if not targets:
            continue
        assert constraint.source is not None
        result.append(Deduction(
            actions=tuple(Action(c, CellState.EXCLUDED) for c in targets),
            rule=Rule.COMMON_NEIGHBOR_EXCLUSION,
            premises=(constraint.source,
                      Premise(tuple(CellFact(c, CellState.UNKNOWN) for c in targets))),
            difficulty=2,
            constraint=constraint,
            adjacencies=tuple(AdjacencyFact(t, c) for t in targets for c in candidates),
        ))
    return result

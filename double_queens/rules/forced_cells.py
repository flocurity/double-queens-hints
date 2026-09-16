from ..board import Board, CellState
from ..deduction import Action, Deduction, QueenConstraint, Rule, constraint_premises
from .candidate_sets import derive_constraints


def find_deductions(board: Board, constraints: tuple[QueenConstraint, ...] | None = None) -> list[Deduction]:
    result = []
    for constraint in derive_constraints(board) if constraints is None else constraints:
        unknown = sorted(constraint.cells)
        if unknown and len(unknown) == constraint.queen_count:
            result.append(Deduction(
                tuple(Action(c, CellState.QUEEN) for c in unknown),
                Rule.FORCED_REMAINING_CELLS,
                constraint_premises(constraint),
                difficulty=3 if constraint.derivation is not None else 1,
                constraint=constraint if constraint.derivation is not None else None,
            ))
    return result

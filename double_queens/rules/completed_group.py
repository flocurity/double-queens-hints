from ..board import Board, CellState
from ..deduction import Action, Deduction, QueenConstraint, Rule, constraint_premises
from .candidate_sets import derive_constraints


def find_deductions(board: Board, constraints: tuple[QueenConstraint, ...] | None = None) -> list[Deduction]:
    result = []
    for constraint in derive_constraints(board) if constraints is None else constraints:
        unknown = sorted(constraint.cells)
        if constraint.queen_count == 0 and unknown:
            result.append(Deduction(
                tuple(Action(c, CellState.EXCLUDED) for c in unknown),
                Rule.COMPLETED_GROUP,
                constraint_premises(constraint),
                difficulty=3 if constraint.derivation is not None else 1,
                constraint=constraint if constraint.derivation is not None else None,
            ))
    return result

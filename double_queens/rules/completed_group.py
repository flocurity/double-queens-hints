from ..board import Board, CellState
from ..deduction import Action, CellFact, Deduction, Premise, Rule


def find_deductions(board: Board) -> list[Deduction]:
    result = []
    for group in board.groups():
        unknown = board.unknown(group.cells)
        if len(board.queens(group.cells)) == 2 and unknown:
            result.append(Deduction(
                tuple(Action(c, CellState.EXCLUDED) for c in unknown),
                Rule.COMPLETED_GROUP,
                (Premise(tuple(CellFact(c, board.at(c)) for c in group.cells), group, 2),),
            ))
    return result

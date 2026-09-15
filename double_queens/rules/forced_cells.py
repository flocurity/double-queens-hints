from ..board import Board, CellState
from ..deduction import Action, CellFact, Deduction, Premise, Rule


def find_deductions(board: Board) -> list[Deduction]:
    result = []
    for group in board.groups():
        unknown = board.unknown(group.cells)
        if unknown and len(unknown) == 2 - len(board.queens(group.cells)):
            result.append(Deduction(
                tuple(Action(c, CellState.QUEEN) for c in unknown),
                Rule.FORCED_REMAINING_CELLS,
                (Premise(tuple(CellFact(c, board.at(c)) for c in group.cells), group, 2),),
            ))
    return result

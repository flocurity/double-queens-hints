from ..board import Board, CellState
from ..deduction import Action, CellFact, Deduction, Premise, Rule


def find_deductions(board: Board) -> list[Deduction]:
    result = []
    for queen in board.queens(board.cells()):
        unknown = board.unknown(board.neighbors(queen))
        if unknown:
            result.append(Deduction(
                tuple(Action(c, CellState.EXCLUDED) for c in unknown),
                Rule.QUEEN_ADJACENCY,
                (Premise((CellFact(queen, CellState.QUEEN),)
                         + tuple(CellFact(c, CellState.UNKNOWN) for c in unknown)),),
            ))
    return result

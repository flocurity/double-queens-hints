from dataclasses import dataclass
from enum import Enum

from . import engine
from .board import Board
from .deduction import Deduction


class SolveStatus(str, Enum):
    SOLVED = "SOLVED"
    LOGIC_STALLED = "LOGIC_STALLED"


@dataclass(frozen=True)
class LogicalSolveResult:
    board: Board
    history: tuple[Deduction, ...]
    status: SolveStatus

    @property
    def solved(self) -> bool:
        return self.status == SolveStatus.SOLVED

    @property
    def reason(self) -> str | None:
        return None if self.solved else "No supported logical deduction found"


def solve_logically(board: Board) -> LogicalSolveResult:
    """Mutate board by applying exactly the hints available to a human."""
    history = []
    while not board.is_solved():
        deduction = engine.next_hint(board)
        if deduction is None:
            return LogicalSolveResult(board, tuple(history), SolveStatus.LOGIC_STALLED)
        board.apply(deduction)
        history.append(deduction)
    return LogicalSolveResult(board, tuple(history), SolveStatus.SOLVED)

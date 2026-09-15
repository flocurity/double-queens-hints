"""Immutable evidence, separate from the actions it justifies."""
from dataclasses import dataclass
from enum import Enum

from .board import Cell, CellState, Group


class Rule(str, Enum):
    FORCED_REMAINING_CELLS = "forced_remaining_cells"
    QUEEN_ADJACENCY = "queen_adjacency"
    COMPLETED_GROUP = "completed_group"


@dataclass(frozen=True)
class Action:
    cell: Cell
    state: CellState

    def __post_init__(self) -> None:
        object.__setattr__(self, "state", CellState(self.state))
        if self.state == CellState.UNKNOWN:
            raise ValueError("An action must establish a queen or exclusion")


@dataclass(frozen=True)
class CellFact:
    cell: Cell
    state: CellState


@dataclass(frozen=True)
class Premise:
    facts: tuple[CellFact, ...]
    group: Group | None = None
    required_queens: int | None = None


@dataclass(frozen=True)
class Deduction:
    actions: tuple[Action, ...]
    rule: Rule
    premises: tuple[Premise, ...]
    difficulty: int = 1

    def __post_init__(self) -> None:
        if not self.actions or not self.premises:
            raise ValueError("Deductions require actions and evidence")

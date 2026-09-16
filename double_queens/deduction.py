"""Immutable evidence, separate from the actions it justifies."""
from dataclasses import dataclass
from enum import Enum

from .board import Cell, CellState, Group


class Rule(str, Enum):
    FORCED_REMAINING_CELLS = "forced_remaining_cells"
    QUEEN_ADJACENCY = "queen_adjacency"
    COMPLETED_GROUP = "completed_group"
    COMMON_NEIGHBOR_EXCLUSION = "common_neighbor_exclusion"


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
class QueenConstraint:
    """Exactly queen_count queens among cells, with optional source evidence."""

    cells: frozenset[Cell]
    queen_count: int
    source: Premise | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "cells", frozenset(self.cells))
        if any(not isinstance(cell, Cell) for cell in self.cells):
            raise ValueError("Constraint candidates must be cells")
        if type(self.queen_count) is not int or not 0 <= self.queen_count <= len(self.cells):
            raise ValueError("Invalid queen count for candidate set")


@dataclass(frozen=True)
class AdjacencyFact:
    target: Cell
    candidate: Cell


@dataclass(frozen=True)
class Deduction:
    actions: tuple[Action, ...]
    rule: Rule
    premises: tuple[Premise, ...]
    difficulty: int = 1
    constraint: QueenConstraint | None = None
    adjacencies: tuple[AdjacencyFact, ...] = ()

    def __post_init__(self) -> None:
        if not self.actions or not self.premises:
            raise ValueError("Deductions require actions and evidence")

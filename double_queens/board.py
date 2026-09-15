"""Puzzle state and local consistency checks; no deduction rules."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Iterable, NewType, Sequence, TYPE_CHECKING

if TYPE_CHECKING:
    from .deduction import Deduction

RegionId = NewType("RegionId", str)


class CellState(IntEnum):
    UNKNOWN = 0
    QUEEN = 1
    EXCLUDED = -1


@dataclass(frozen=True, order=True)
class Cell:
    row: int
    col: int

    def __str__(self) -> str:
        return f"L{self.row + 1}C{self.col + 1}"


class GroupKind(str, Enum):
    ROW = "row"
    COLUMN = "column"
    REGION = "region"


@dataclass(frozen=True)
class Group:
    kind: GroupKind
    index: int | RegionId
    cells: tuple[Cell, ...]

    @property
    def label(self) -> str:
        value = self.index + 1 if isinstance(self.index, int) else self.index
        return f"{self.kind.value} {value}"


class ContradictionError(ValueError):
    """A state or attempted action violates puzzle rules."""


class Board:
    def __init__(self, regions: Sequence[Sequence[RegionId | str]],
                 state: Sequence[Sequence[CellState | int]] | None = None) -> None:
        self.size = len(regions)
        if not self.size or any(len(row) != self.size for row in regions):
            raise ValueError("Regions must be a nonempty square grid")
        if any(not isinstance(r, str) or not r for row in regions for r in row):
            raise ValueError("Region IDs must be nonempty strings")
        self.regions = tuple(tuple(RegionId(r) for r in row) for row in regions)
        self.region_ids = tuple(sorted({r for row in self.regions for r in row}))
        if state is None:
            state = [[CellState.UNKNOWN] * self.size for _ in range(self.size)]
        if len(state) != self.size or any(len(row) != self.size for row in state):
            raise ValueError("State must match the region grid")
        self._state = tuple(tuple(CellState(s) for s in row) for row in state)

    @property
    def state(self) -> tuple[tuple[CellState, ...], ...]:
        return self._state

    def row(self, r: int) -> tuple[Cell, ...]:
        self._check(Cell(r, 0))
        return tuple(Cell(r, c) for c in range(self.size))

    def column(self, c: int) -> tuple[Cell, ...]:
        self._check(Cell(0, c))
        return tuple(Cell(r, c) for r in range(self.size))

    def region(self, region_id: RegionId | str) -> tuple[Cell, ...]:
        if region_id not in self.region_ids:
            raise KeyError(region_id)
        return tuple(c for c in self.cells() if self.regions[c.row][c.col] == region_id)

    def cells(self) -> tuple[Cell, ...]:
        return tuple(Cell(r, c) for r in range(self.size) for c in range(self.size))

    def groups(self) -> tuple[Group, ...]:
        return tuple(
            [Group(GroupKind.ROW, r, self.row(r)) for r in range(self.size)]
            + [Group(GroupKind.COLUMN, c, self.column(c)) for c in range(self.size)]
            + [Group(GroupKind.REGION, r, self.region(r)) for r in self.region_ids]
        )

    def _check(self, cell: Cell) -> None:
        if not (0 <= cell.row < self.size and 0 <= cell.col < self.size):
            raise IndexError(f"Cell outside board: {cell}")

    def at(self, cell: Cell) -> CellState:
        self._check(cell)
        return self._state[cell.row][cell.col]

    def queens(self, cells: Iterable[Cell]) -> tuple[Cell, ...]:
        return tuple(c for c in cells if self.at(c) == CellState.QUEEN)

    def unknown(self, cells: Iterable[Cell]) -> tuple[Cell, ...]:
        return tuple(c for c in cells if self.at(c) == CellState.UNKNOWN)

    def excluded(self, cells: Iterable[Cell]) -> tuple[Cell, ...]:
        return tuple(c for c in cells if self.at(c) == CellState.EXCLUDED)

    def neighbors(self, cell: Cell) -> tuple[Cell, ...]:
        self._check(cell)
        return tuple(Cell(r, c)
                     for r in range(max(0, cell.row - 1), min(self.size, cell.row + 2))
                     for c in range(max(0, cell.col - 1), min(self.size, cell.col + 2))
                     if Cell(r, c) != cell)

    def validate(self) -> None:
        # Total row and region quotas must agree, without assuming a fixed N.
        if len(self.region_ids) != self.size:
            raise ContradictionError("Exactly N regions are required by the total queen quotas")
        for group in self.groups():
            queens = len(self.queens(group.cells))
            if queens > 2:
                raise ContradictionError(f"{group.label} has more than two queens")
            if queens + len(self.unknown(group.cells)) < 2:
                raise ContradictionError(f"{group.label} has too few remaining candidates")
        for queen in self.queens(self.cells()):
            if self.queens(self.neighbors(queen)):
                raise ContradictionError(f"Adjacent queens at {queen}")

    def is_solved(self) -> bool:
        self.validate()
        return all(len(self.queens(g.cells)) == 2 for g in self.groups())

    def apply(self, deduction: Deduction) -> None:
        """Apply atomically, rejecting stale evidence and invalid resulting states."""
        self.validate()
        for premise in deduction.premises:
            if premise.group is not None and premise.group not in self.groups():
                raise ValueError("Deduction source does not match this board")
            if any(self.at(f.cell) != f.state for f in premise.facts):
                raise ValueError("Deduction premises are stale")
        updated = [list(row) for row in self.state]
        for action in deduction.actions:
            self._check(action.cell)
            current = updated[action.cell.row][action.cell.col]
            if current not in (CellState.UNKNOWN, action.state):
                raise ContradictionError(f"Cannot change {action.cell} from {current.name} to {action.state.name}")
            updated[action.cell.row][action.cell.col] = action.state
        candidate = Board(self.regions, updated)
        candidate.validate()
        self._state = candidate.state

"""Immutable evidence, separate from the actions it justifies."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from .board import Cell, CellState, Group


class Rule(str, Enum):
    FORCED_REMAINING_CELLS = "forced_remaining_cells"
    QUEEN_ADJACENCY = "queen_adjacency"
    COMPLETED_GROUP = "completed_group"
    COMMON_NEIGHBOR_EXCLUSION = "common_neighbor_exclusion"
    LOCAL_PLACEMENT_EXCLUSION = "local_placement_exclusion"


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
    derivation: InclusionProof | PlacementSubsetProof | None = None

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
class InclusionProof:
    """The result is superset minus subset, with the cardinalities subtracted."""
    subset: QueenConstraint
    superset: QueenConstraint


class PlacementConflict(str, Enum):
    ADJACENCY = "adjacency"
    EXISTING_QUEEN = "existing_queen"
    OVER_CAPACITY = "over_capacity"
    UNDER_CAPACITY = "under_capacity"


@dataclass(frozen=True)
class PlacementRejection:
    placement: frozenset[Cell]
    reason: PlacementConflict
    constraint: QueenConstraint | None = None
    adjacency: AdjacencyFact | None = None
    occupied: int = 0
    available: frozenset[Cell] = frozenset()


@dataclass(frozen=True)
class LocalPlacements:
    constraint: QueenConstraint
    placements: tuple[frozenset[Cell], ...]
    rejected: tuple[PlacementRejection, ...]
    checked_constraints: tuple[QueenConstraint, ...]
    premises: tuple[Premise, ...]


@dataclass(frozen=True)
class PlacementSubsetProof:
    """Every recorded placement has the result constraint's cardinality in S."""
    analysis: LocalPlacements


@dataclass(frozen=True)
class PlacementCoverage:
    """For each placement, an explicit queen touching the excluded target."""
    target: Cell
    witnesses: tuple[AdjacencyFact, ...]


def constraint_premises(constraint: QueenConstraint) -> tuple[Premise, ...]:
    """Flatten a finite proof DAG into the snapshots checked by Board.apply."""
    proof = constraint.derivation
    if isinstance(proof, InclusionProof):
        premises = constraint_premises(proof.subset) + constraint_premises(proof.superset)
    elif isinstance(proof, PlacementSubsetProof):
        premises = proof.analysis.premises
    else:
        premises = (constraint.source,) if constraint.source is not None else ()
    return tuple(dict.fromkeys(premises))


@dataclass(frozen=True)
class Deduction:
    actions: tuple[Action, ...]
    rule: Rule
    premises: tuple[Premise, ...]
    difficulty: int = 1
    constraint: QueenConstraint | None = None
    adjacencies: tuple[AdjacencyFact, ...] = ()
    local_placements: LocalPlacements | None = None
    coverage: tuple[PlacementCoverage, ...] = ()

    def __post_init__(self) -> None:
        if not self.actions or not self.premises:
            raise ValueError("Deductions require actions and evidence")

"""One bounded pass of local cardinality reasoning; no hypothetical boards.

Placements contain at most two queens in ONE residual constraint. Each is
checked directly against intersecting constraints. Derived facts are consumed
by the elementary rules, never fed into a recursive hypothetical solver.
"""
from itertools import combinations

from ..board import Board, Cell, CellState, ContradictionError
from ..deduction import (
    Action, AdjacencyFact, CellFact, Deduction, InclusionProof, LocalPlacements,
    PlacementConflict, PlacementCoverage, PlacementRejection, PlacementSubsetProof,
    Premise, QueenConstraint, Rule, constraint_premises,
)
from . import candidate_sets, completed_group, forced_cells


def _key(constraint: QueenConstraint) -> tuple:
    return tuple(sorted(constraint.cells)), constraint.queen_count


def derive_inclusions(constraints: tuple[QueenConstraint, ...]) -> tuple[QueenConstraint, ...]:
    """Subtract directly included constraints once; retain both source proofs."""
    result = {}
    for small in constraints:
        for large in constraints:
            if small.cells == large.cells and small.queen_count != large.queen_count:
                raise ContradictionError("Conflicting counts for the same candidate set")
            if not small.cells or not small.cells < large.cells:
                continue
            cells = large.cells - small.cells
            count = large.queen_count - small.queen_count
            if not 0 <= count <= len(cells):
                raise ContradictionError("Incompatible included queen constraints")
            constraint = QueenConstraint(cells, count, large.source, InclusionProof(small, large))
            result.setdefault(_key(constraint), constraint)
    return tuple(result[key] for key in sorted(result))


def analyze_local_placements(
    board: Board, constraint: QueenConstraint,
    constraints: tuple[QueenConstraint, ...] | None = None,
) -> LocalPlacements:
    """Enumerate complete local placements and their first immediate rejection.

    Inputs are current, proven residual constraints. No assumptions are applied
    to a Board, no other placements are explored under an assumption, and no
    downstream rule is run. An empty placement set is a local contradiction.
    """
    board.validate()
    if constraint.queen_count > 2:
        raise ValueError("Local placement analysis supports at most two remaining queens")
    if any(board.at(c) != CellState.UNKNOWN for c in constraint.cells):
        raise ValueError("Local constraint candidates are stale")
    known = candidate_sets.derive_constraints(board) if constraints is None else constraints
    checked = tuple(c for c in known if c.cells & constraint.cells and c != constraint)
    if any(board.at(cell) != CellState.UNKNOWN for c in checked for cell in c.cells):
        raise ValueError("Intersecting constraint candidates are stale")
    sources = tuple(dict.fromkeys(
        p for c in (constraint, *checked) for p in constraint_premises(c)
    ))
    for premise in sources:
        if premise.group is not None and premise.group not in board.groups():
            raise ValueError("Constraint source does not match this board")
        if any(board.at(f.cell) != f.state for f in premise.facts):
            raise ValueError("Constraint premises are stale")
    # Snapshot every consulted candidate and its halo. This includes existing
    # queens outside a group that can remove its remaining capacity.
    relevant = set(constraint.cells)
    for other in checked:
        relevant.update(other.cells)
    neighbors = {c: frozenset(board.neighbors(c)) for c in relevant}
    observed = relevant | set().union(*neighbors.values())
    facts = Premise(tuple(CellFact(c, board.at(c)) for c in sorted(observed)))
    premises = sources + (facts,)
    occupied_neighbors = {c: board.queens(neighbors[c]) for c in relevant}
    unavailable = {c for c in relevant if occupied_neighbors[c]}
    accepted, rejected = [], []
    for cells in combinations(sorted(constraint.cells), constraint.queen_count):
        placement = frozenset(cells)
        conflict = next((AdjacencyFact(a, b) for a, b in combinations(cells, 2)
                         if b in neighbors[a]), None)
        if conflict is not None:
            rejected.append(PlacementRejection(placement, PlacementConflict.ADJACENCY,
                                               adjacency=conflict))
            continue
        blocked = next((c for c in cells if c in unavailable), None)
        if blocked is not None:
            rejected.append(PlacementRejection(
                placement, PlacementConflict.EXISTING_QUEEN,
                adjacency=AdjacencyFact(blocked, occupied_neighbors[blocked][0])))
            continue
        attacked = set().union(*(neighbors[c] for c in cells))
        rejection = None
        for other in checked:
            occupied = len(placement & other.cells)
            available = other.cells - constraint.cells - attacked - unavailable
            if occupied > other.queen_count:
                reason = PlacementConflict.OVER_CAPACITY
            elif occupied + len(available) < other.queen_count:
                reason = PlacementConflict.UNDER_CAPACITY
            else:
                continue
            rejection = PlacementRejection(placement, reason, other,
                                           occupied=occupied, available=frozenset(available))
            break
        if rejection is None:
            accepted.append(placement)
        else:
            rejected.append(rejection)
    if not accepted:
        label = constraint.source.group.label if constraint.source and constraint.source.group else "constraint"
        raise ContradictionError(f"No locally valid placement for {label}")
    return LocalPlacements(constraint, tuple(accepted), tuple(rejected), checked, premises)


def derive_subconstraint(analysis: LocalPlacements, cells: frozenset[Cell]) -> QueenConstraint | None:
    """Return the exact cardinality on a given subset if all placements agree."""
    cells = frozenset(cells)
    if not cells <= analysis.constraint.cells:
        raise ValueError("Subconstraint must be inside the analyzed constraint")
    if not analysis.placements:
        raise ContradictionError("Cannot derive facts from an empty placement set")
    counts = {len(p & cells) for p in analysis.placements}
    if len(counts) != 1:
        return None
    return QueenConstraint(cells, counts.pop(), analysis.constraint.source,
                           PlacementSubsetProof(analysis))


def _subsets(board: Board, constraint: QueenConstraint) -> tuple[frozenset[Cell], ...]:
    """A polynomial family: singletons, group intersections, touching components.

    Complements capture the corresponding remainder cardinality. Arbitrary
    subsets and unions across unrelated constraints are not enumerated.
    """
    cells = constraint.cells
    subsets = {frozenset((c,)) for c in cells}
    subsets.update(cells & frozenset(g.cells) for g in board.groups())
    pending = set(cells)
    while pending:
        component = {min(pending)}
        frontier = list(component)
        pending.difference_update(component)
        while frontier:
            adjacent = pending.intersection(board.neighbors(frontier.pop()))
            pending.difference_update(adjacent)
            component.update(adjacent)
            frontier.extend(sorted(adjacent))
        subsets.add(frozenset(component))
    subsets.update(cells - s for s in tuple(subsets))
    return tuple(sorted((s for s in subsets if s and s != cells), key=lambda s: tuple(sorted(s))))


def _analyze(board: Board) -> tuple[tuple[QueenConstraint, ...], tuple[LocalPlacements, ...]]:
    base = candidate_sets.derive_constraints(board)
    inclusions = derive_inclusions(base)
    known = base + inclusions
    # Equivalent residual constraints need only one placement analysis.
    unique = {}
    for constraint in base:
        unique.setdefault(_key(constraint), constraint)
    analyses = tuple(analyze_local_placements(board, c, known)
                     for c in unique.values() if c.queen_count > 0)
    derived = {_key(c): c for c in inclusions}
    for analysis in analyses:
        for cells in _subsets(board, analysis.constraint):
            constraint = derive_subconstraint(analysis, cells)
            if constraint is not None:
                derived.setdefault(_key(constraint), constraint)
    base_keys = {_key(c) for c in base}
    return tuple(derived[k] for k in sorted(derived) if k not in base_keys), analyses


def derive_local_constraints(board: Board) -> tuple[QueenConstraint, ...]:
    """Recompute proven local facts from the current board; nothing is persisted."""
    return _analyze(board)[0]


def placement_exclusions(board: Board, analysis: LocalPlacements) -> list[Deduction]:
    """External targets touched in every placement, possibly by different queens."""
    if not analysis.placements:
        raise ContradictionError("Cannot derive facts from an empty placement set")
    common = None
    for placement in analysis.placements:
        attacked = set().union(*(board.neighbors(c) for c in placement))
        common = attacked if common is None else common & attacked
    targets = board.unknown(sorted((common or set()) - analysis.constraint.cells))
    if not targets:
        return []
    coverage = tuple(PlacementCoverage(t, tuple(
        AdjacencyFact(t, next(c for c in sorted(p) if c in board.neighbors(t)))
        for p in analysis.placements)) for t in targets)
    return [Deduction(
        tuple(Action(c, CellState.EXCLUDED) for c in targets),
        Rule.LOCAL_PLACEMENT_EXCLUSION,
        analysis.premises + (Premise(tuple(CellFact(c, CellState.UNKNOWN) for c in targets)),),
        difficulty=3, local_placements=analysis, coverage=coverage,
    )]


def find_deductions(board: Board) -> list[Deduction]:
    derived, analyses = _analyze(board)
    # Reuse the existing cardinality/neighbor consumers, including provenance.
    result = (forced_cells.find_deductions(board, derived)
              + completed_group.find_deductions(board, derived)
              + candidate_sets.find_deductions(board, derived))
    for analysis in analyses:
        result.extend(placement_exclusions(board, analysis))
    return result

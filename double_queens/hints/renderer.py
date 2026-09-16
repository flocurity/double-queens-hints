from collections.abc import Callable

from ..board import CellState, GroupKind, RegionId
from ..deduction import (Deduction, InclusionProof, LocalPlacements,
                         PlacementSubsetProof, QueenConstraint, Rule)


def _cells(cells) -> str:
    return ", ".join(map(str, sorted(cells)))


def _constraint_text(constraint: QueenConstraint) -> str:
    return f"exactly {constraint.queen_count} queen(s) among {{{_cells(constraint.cells)}}}"


def _local_reason(analysis: LocalPlacements) -> str:
    placements = "; ".join("{" + _cells(p) + "}" for p in analysis.placements)
    return (f"The locally valid placements are {placements}, after checking immediate "
            "adjacency and intersecting queen quotas.")


def _derived_reason(constraint: QueenConstraint) -> str:
    proof = constraint.derivation
    if isinstance(proof, InclusionProof):
        return (f"{_constraint_text(proof.subset).capitalize()} is included in "
                f"{_constraint_text(proof.superset)}. Subtracting their counts leaves "
                f"{_constraint_text(constraint)}.")
    if isinstance(proof, PlacementSubsetProof):
        return (f"{_local_reason(proof.analysis)} Every placement contains "
                f"{constraint.queen_count} queen(s) in {{{_cells(constraint.cells)}}}.")
    return _constraint_text(constraint)


def render_hint(
    deduction: Deduction,
    level: int = 1,
    *,
    region_display: Callable[[RegionId], str] | None = None,
) -> str:
    if level not in (1, 2, 3, 4):
        raise ValueError("Hint level must be 1, 2, 3, or 4")
    premise = deduction.premises[0]
    targets = ", ".join(str(a.cell) for a in deduction.actions)
    advanced = deduction.local_placements is not None or (
        deduction.constraint is not None and deduction.constraint.derivation is not None)
    if advanced and level < 4:
        constraint = (deduction.constraint if deduction.constraint is not None
                      else deduction.local_placements.constraint)
        proof = constraint.derivation
        attention_sources = ([proof.subset.source, proof.superset.source]
                             if isinstance(proof, InclusionProof) else [constraint.source])
        labels = []
        for p in attention_sources:
            if p is None or p.group is None:
                continue
            label = (f"region {region_display(RegionId(p.group.index))}"
                     if p.group.kind == GroupKind.REGION and region_display else p.group.label)
            if label not in labels:
                labels.append(label)
        if level == 1:
            return f"Look at {', '.join(labels) or 'the local candidate set'} and their remaining candidates."
        if level == 2:
            if deduction.constraint and isinstance(deduction.constraint.derivation, InclusionProof):
                proof = deduction.constraint.derivation
                return (f"One candidate set lies inside the other. They require "
                        f"{proof.subset.queen_count} and {proof.superset.queen_count} queen(s). "
                        "What count must remain outside the smaller set?")
            analysis = (proof.analysis if isinstance(proof, PlacementSubsetProof)
                        else deduction.local_placements)
            return (f"This local set needs {analysis.constraint.queen_count} queen(s) among "
                    f"{len(analysis.constraint.cells)} candidates. Consider the ways they can fit without touching or "
                    "violating intersecting quotas. What holds in every local placement?")
        if deduction.local_placements is not None:
            return (f"{_local_reason(deduction.local_placements)} Each of {targets} touches "
                    "at least one queen in every placement, so cannot contain a queen.")
        reason = _derived_reason(deduction.constraint)
        if deduction.rule == Rule.COMMON_NEIGHBOR_EXCLUSION:
            return f"{reason} {targets} touch every candidate of this nonempty queen set, so cannot contain queens."
        if deduction.rule == Rule.FORCED_REMAINING_CELLS:
            return f"{reason} All its cells, {targets}, are needed and must contain queens."
        return f"{reason} No queen can remain at {targets}."
    if advanced:
        return " ".join(f"Place a queen at {a.cell}." if a.state == CellState.QUEEN
                        else f"Exclude {a.cell}." for a in deduction.actions)
    if deduction.rule == Rule.QUEEN_ADJACENCY:
        queen = next(f.cell for f in premise.facts if f.state == CellState.QUEEN)
        if level == 1:
            return f"Look around {queen}."
        if level == 2:
            return f"{queen} is a queen. Queens cannot touch, even diagonally."
        if level == 3:
            return f"{targets} touch the queen at {queen}, so cannot contain queens."
    else:
        if premise.group is None:
            raise ValueError("Group deduction requires a source group")
        if premise.group.kind == GroupKind.REGION and region_display is not None:
            source = f"region {region_display(RegionId(premise.group.index))}"
        else:
            source = premise.group.label
        count = sum(f.state == CellState.QUEEN for f in premise.facts)
        if deduction.rule == Rule.COMMON_NEIGHBOR_EXCLUSION:
            constraint = deduction.constraint
            if constraint is None:
                raise ValueError("Common-neighbor deduction requires a constraint")
            candidates = ", ".join(map(str, sorted(constraint.cells)))
            if level == 1:
                return f"Look at the remaining candidates in {source}."
            if level == 2:
                return (f"{source.capitalize()} still needs {constraint.queen_count} queen(s) "
                        f"among {candidates}. Which cells touch every possible position?")
            if level == 3:
                return (f"At least one queen must occur among {candidates} in {source}. "
                        f"{targets} touch every candidate, so cannot contain queens.")
        elif level == 1:
            return f"Look at {source}."
        elif level == 2:
            return (f"{source.capitalize()} requires {premise.required_queens} queens and already has {count}. "
                    "How many unknown cells remain?")
        elif level == 3:
            if deduction.rule == Rule.FORCED_REMAINING_CELLS:
                return f"Only {targets} remain available in {source}; all are needed to reach two queens."
            return f"{source.capitalize()} already has two queens, so {targets} cannot contain queens."
    return " ".join(
        f"Place a queen at {a.cell}." if a.state == CellState.QUEEN
        else f"Exclude {a.cell}." for a in deduction.actions
    )


def render_deduction(deduction: Deduction) -> str:
    lines = [f"RULE: {deduction.rule.value}", f"DIFFICULTY: {deduction.difficulty}", "PREMISES:"]
    for premise in deduction.premises:
        if premise.group:
            lines.append(f"- {premise.group.label} requires {premise.required_queens} queens")
        lines.extend(f"- {fact.cell} = {fact.state.name}" for fact in premise.facts)
    if deduction.constraint is not None:
        cells = ", ".join(map(str, sorted(deduction.constraint.cells)))
        lines.extend(["CONSTRAINT:",
                      f"- exactly {deduction.constraint.queen_count} queen(s) among {{{cells}}}"])
        _render_constraint_proof(deduction.constraint, lines, set())
    if deduction.local_placements is not None:
        _render_placements(deduction.local_placements, lines, set())
    for coverage in deduction.coverage:
        for index, witness in enumerate(coverage.witnesses, 1):
            lines.append(f"- placement {index}: {coverage.target} touches {witness.candidate}")
    lines.extend(f"- {fact.target} touches {fact.candidate}" for fact in deduction.adjacencies)
    lines.append("CONCLUSION:")
    lines.extend(f"- {a.cell} = {a.state.name}" for a in deduction.actions)
    return "\n".join(lines)


def _render_constraint_proof(constraint: QueenConstraint, lines: list[str], seen: set[int]) -> None:
    if id(constraint) in seen:
        return
    seen.add(id(constraint))
    proof = constraint.derivation
    if isinstance(proof, InclusionProof):
        lines.extend(["INCLUSION:", f"- subset: {_constraint_text(proof.subset)}",
                      f"- superset: {_constraint_text(proof.superset)}",
                      f"- difference: {_constraint_text(constraint)}"])
        _render_constraint_proof(proof.subset, lines, seen)
        _render_constraint_proof(proof.superset, lines, seen)
    elif isinstance(proof, PlacementSubsetProof):
        lines.append(f"SUBCONSTRAINT: {_constraint_text(constraint)}")
        _render_placements(proof.analysis, lines, seen)


def _render_placements(analysis: LocalPlacements, lines: list[str], seen: set[int]) -> None:
    if id(analysis) in seen:
        return
    seen.add(id(analysis))
    lines.append(f"LOCAL CONSTRAINT: {_constraint_text(analysis.constraint)}")
    lines.append("VALID LOCAL PLACEMENTS:")
    lines.extend(f"- {{{_cells(p)}}}" for p in analysis.placements)
    lines.append("CHECKED CONSTRAINTS:")
    for constraint in analysis.checked_constraints:
        label = constraint.source.group.label if constraint.source and constraint.source.group else "derived"
        lines.append(f"- {label}: {_constraint_text(constraint)}")
        _render_constraint_proof(constraint, lines, seen)
    lines.append("REJECTED LOCAL PLACEMENTS:")
    for rejection in analysis.rejected:
        lines.append(f"- {{{_cells(rejection.placement)}}}: {rejection.reason.value}")
        if rejection.adjacency:
            lines.append(f"  {rejection.adjacency.target} touches {rejection.adjacency.candidate}")
        if rejection.constraint:
            lines.append(f"  {_constraint_text(rejection.constraint)}; occupied={rejection.occupied}; "
                         f"available={{{_cells(rejection.available)}}}")

from collections.abc import Callable, Iterable

from ..board import Cell, CellState, GroupKind, RegionId
from ..deduction import (Deduction, InclusionProof, LocalPlacements, Premise,
                         PlacementConflict, PlacementSubsetProof, QueenConstraint, Rule)


def _cells(cells) -> str:
    """Formal cell list for the exhaustive debug proof."""
    return ", ".join(map(str, sorted(cells)))


def _constraint_text(constraint: QueenConstraint) -> str:
    return f"exactly {constraint.queen_count} queen(s) among {{{_cells(constraint.cells)}}}"


def _list(items: Iterable[str]) -> str:
    values = list(items)
    if len(values) < 3:
        return " and ".join(values)
    return ", ".join(values[:-1]) + ", and " + values[-1]


def _cell_list(cells: Iterable[Cell]) -> str:
    return _list(str(c) for c in sorted(cells))


def _count(count: int, noun: str) -> str:
    return f"{'one' if count == 1 else count} {noun}{'' if count == 1 else 's'}"


def _sentence(text: str) -> str:
    # str.capitalize() would also lowercase region names and coordinates.
    return text[:1].upper() + text[1:]


def _group(premise: Premise | None, display) -> str | None:
    if premise is None or premise.group is None:
        return None
    group = premise.group
    if group.kind == GroupKind.REGION and display is not None:
        return f"region {display(RegionId(group.index))}"
    return group.label


def _area(constraint: QueenConstraint, display) -> str:
    if isinstance(constraint.derivation, PlacementSubsetProof):
        return _area(constraint.derivation.analysis.constraint, display)
    return _group(constraint.source, display) or 'the indicated cells'


def _scope(constraint: QueenConstraint, display) -> str:
    # A derived constraint's source names its origin, not necessarily its scope.
    if constraint.derivation is None:
        label = _group(constraint.source, display)
        if label:
            return label
    return f"the candidates {_cell_list(constraint.cells)}"


def _knowledge(constraint: QueenConstraint) -> str:
    cells = _cell_list(constraint.cells)
    if constraint.queen_count == 1:
        if len(constraint.cells) == 1:
            return f"{cells} must contain a queen."
        return f"Exactly one of {cells} must contain a queen."
    if constraint.queen_count == 0:
        return f"There are 0 queens among {cells}."
    return f"Exactly {_count(constraint.queen_count, 'queen')} must occur among {cells}."


def _conclusion(targets: tuple[Cell, ...], queen: bool = False) -> str:
    noun = 'a queen' if len(targets) == 1 else 'queens'
    return f"{_cell_list(targets)} {'must' if queen else 'cannot'} contain {noun}."


def _actions(deduction: Deduction) -> str:
    sentences = []
    for state in dict.fromkeys(a.state for a in deduction.actions):
        cells = tuple(a.cell for a in deduction.actions if a.state == state)
        if state == CellState.QUEEN:
            sentences.append(f"Place {'a queen' if len(cells) == 1 else 'queens'} at {_cell_list(cells)}.")
        else:
            sentences.append(f"Exclude {_cell_list(cells)}.")
    return ' '.join(sentences)


def _inclusion(constraint: QueenConstraint, level: int, display) -> str:
    proof = constraint.derivation
    small, large = proof.subset, proof.superset
    a, b = _scope(small, display), _scope(large, display)
    relation = f"All remaining candidates in {a} are among the remaining candidates in {b}."
    quotas = (f"{_sentence(a)} needs {_count(small.queen_count, 'queen')}; "
              f"{b} needs {_count(large.queen_count, 'queen')}.")
    if level == 2:
        return f"{relation} {quotas} How many queens can remain outside {a}?"
    result = ("Those queens account for everything the larger group needs."
              if constraint.queen_count == 0 else
              f"This leaves {_count(constraint.queen_count, 'queen')} among {_cell_list(constraint.cells)}.")
    return f"{relation} {quotas} {result}"


def _common(constraint: QueenConstraint, targets: tuple[Cell, ...], level: int, display) -> str:
    source = _area(constraint, display)
    candidates = _cell_list(constraint.cells)
    count = constraint.queen_count
    both = 'both' if len(constraint.cells) == 2 else 'all'
    touched = 'that cell' if len(constraint.cells) == 1 else f'{both} cells'
    if level == 2:
        if constraint.derivation is None:
            fact = f"{_sentence(source)} still needs {_count(count, 'queen')} among {candidates}."
        else:
            fact = f"Consider the remaining candidates in {source}."
        return f"{fact} Which cells touch {both} candidates?"
    fact = (_knowledge(constraint) if constraint.derivation is not None else
            f"{_sentence(source)} must place {_count(count, 'queen')} among {candidates}.")
    touch = 'touches' if len(targets) == 1 else 'all touch'
    queen = 'that queen' if count == 1 else 'at least one of those queens'
    return (f"{fact} {_cell_list(targets)} {touch} {touched}, so "
            f"{'it' if len(targets) == 1 else 'each'} will necessarily touch {queen}. "
            f"Therefore {_conclusion(targets)}")


def _rejection_reason(analysis: LocalPlacements, targets: tuple[Cell, ...], display) -> str:
    # Only summarize explicitly recorded singleton rejections. Multi-queen
    # combinations can fail for different reasons; do not reconstruct a proof.
    if analysis.constraint.queen_count != 1 or len(targets) != 1:
        return ''
    rejection = next((r for r in analysis.rejected if r.placement == frozenset(targets)), None)
    if rejection is None:
        return ''
    if rejection.reason in (PlacementConflict.ADJACENCY, PlacementConflict.EXISTING_QUEEN):
        return 'It would touch another queen. '
    if rejection.constraint is not None:
        group = _group(rejection.constraint.source, display)
        if group and rejection.constraint.derivation is None:
            if rejection.reason == PlacementConflict.OVER_CAPACITY:
                return f"It would put too many queens in {group}. "
            if rejection.reason == PlacementConflict.UNDER_CAPACITY:
                return f"It would leave too few available cells for the remaining queens in {group}. "
    return ''


def _local_hint(deduction: Deduction, analysis: LocalPlacements, level: int, display) -> str:
    targets = tuple(a.cell for a in deduction.actions)
    source = _area(analysis.constraint, display)
    if level == 2:
        count = analysis.constraint.queen_count
        question = ('Which positions allow a valid placement?' if count == 1 else
                    'Which pairs can be placed without touching or exceeding another group’s quota?')
        return (f"{_sentence(source)} still needs {_count(count, 'queen')} among "
                f"{_count(len(analysis.constraint.cells), 'candidate')}. {question}")
    if deduction.local_placements is not None:
        return (f"In every valid placement of the remaining queens in {source}, "
                f"{_cell_list(targets)} {'touches' if len(targets) == 1 else 'each touch'} "
                f"at least one queen. Therefore {_conclusion(targets)}")
    if deduction.rule == Rule.COMPLETED_GROUP:
        reason = _rejection_reason(analysis, targets, display)
        return (f"{_cell_list(targets)} cannot be part of any valid placement of the remaining queens "
                f"in {source}. {reason}Therefore {_conclusion(targets)}")
    # Never list placements for exclusions. For forced queens, at most two are
    # listed, and only if they contain no cells outside the selected actions.
    # This deliberately conservative display policy prevents sibling spoilers.
    placements = analysis.placements
    if len(placements) <= 2 and all(p <= frozenset(targets) for p in placements):
        listing = _list('{' + _cell_list(p) + '}' for p in placements)
        intro = f"The only valid placement is {listing}." if len(placements) == 1 else f"The valid placements are {listing}."
    else:
        intro = f"Every valid placement of the remaining queens in {source} contains {_cell_list(targets)}."
    return f"{intro} Therefore {_conclusion(targets, queen=True)}"


def render_hint(
    deduction: Deduction,
    level: int = 1,
    *,
    region_display: Callable[[RegionId], str] | None = None,
) -> str:
    """Explain recorded evidence progressively, without discovering new facts."""
    if level not in (1, 2, 3, 4):
        raise ValueError("Hint level must be 1, 2, 3, or 4")
    premise = deduction.premises[0]
    targets = tuple(a.cell for a in deduction.actions)
    if deduction.rule == Rule.QUEEN_ADJACENCY:
        queen = next(f.cell for f in premise.facts if f.state == CellState.QUEEN)
        if level == 1:
            return f"Look around {queen}."
        if level == 2:
            return f"{queen} contains a queen. Queens cannot touch, even diagonally."
        if level == 3:
            return (f"{_cell_list(targets)} {'touches' if len(targets) == 1 else 'all touch'} "
                    f"the queen at {queen}, so "
                    f"{'it' if len(targets) == 1 else 'none of them'} can{'not' if len(targets) == 1 else ''} contain a queen.")
        return _actions(deduction)
    constraint = deduction.constraint
    proof = constraint.derivation if constraint else None
    analysis = (proof.analysis if isinstance(proof, PlacementSubsetProof) else deduction.local_placements)
    advanced = proof is not None or analysis is not None
    if not advanced and premise.group is None:
        raise ValueError("Group deduction requires a source group")
    if deduction.rule == Rule.COMMON_NEIGHBOR_EXCLUSION and constraint is None:
        raise ValueError("Common-neighbor deduction requires a constraint")
    if level == 4:
        return _actions(deduction)
    if advanced:
        origin = constraint if constraint is not None else analysis.constraint
        if level == 1:
            sources = (proof.subset, proof.superset) if isinstance(proof, InclusionProof) else (origin,)
            areas = list(dict.fromkeys(_area(c, region_display) for c in sources))
            return f"Look at the remaining candidates in {_list(areas)}."
        if deduction.rule == Rule.COMMON_NEIGHBOR_EXCLUSION:
            return _common(constraint, targets, level, region_display)
        if isinstance(proof, InclusionProof):
            text = _inclusion(constraint, level, region_display)
            return text if level == 2 else f"{text} Therefore {_conclusion(targets, deduction.rule == Rule.FORCED_REMAINING_CELLS)}"
        return _local_hint(deduction, analysis, level, region_display)
    source = _group(premise, region_display)
    if deduction.rule == Rule.COMMON_NEIGHBOR_EXCLUSION:
        if level == 1:
            return f"Look at the remaining candidates in {source}."
        return _common(constraint, targets, level, region_display)
    if level == 1:
        return f"Look at {source}."
    count = sum(f.state == CellState.QUEEN for f in premise.facts)
    remaining = premise.required_queens - count
    if deduction.rule == Rule.COMPLETED_GROUP:
        fact = f"{_sentence(source)} already contains its {premise.required_queens} required queens"
        return (f"{fact}. What does that mean for its remaining candidates?" if level == 2 else
                f"{fact}, so {_conclusion(targets)}")
    if level == 2:
        return f"{_sentence(source)} still needs {_count(remaining, 'queen')}. Which candidates are still available?"
    return (f"Only {_cell_list(targets)} {'remains' if len(targets) == 1 else 'remain'} available in {source}. "
            f"It still needs {_count(remaining, 'queen')}, so {_conclusion(targets, queen=True)}")


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

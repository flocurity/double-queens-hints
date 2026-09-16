from collections.abc import Callable

from ..board import CellState, GroupKind, RegionId
from ..deduction import Deduction, Rule


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
    lines.extend(f"- {fact.target} touches {fact.candidate}" for fact in deduction.adjacencies)
    lines.append("CONCLUSION:")
    lines.extend(f"- {a.cell} = {a.state.name}" for a in deduction.actions)
    return "\n".join(lines)

from .board import Board, Cell, CellState, ContradictionError, Group, GroupKind, RegionId
from .deduction import Action, AdjacencyFact, CellFact, Deduction, Premise, QueenConstraint, Rule
from .rules.candidate_sets import derive_constraints
from .engine import best_deduction, find_deductions, next_hint
from .hints import DebugRenderContext, RegionPalette, render_board, render_deduction, render_hint
from .solver import LogicalSolveResult, SolveStatus, solve_logically

__all__ = [
    "Board", "Cell", "CellState", "ContradictionError", "Group", "GroupKind", "RegionId",
    "Action", "CellFact", "Deduction", "Premise", "Rule", "best_deduction",
    "find_deductions", "next_hint", "DebugRenderContext", "RegionPalette",
    "render_board", "render_deduction", "render_hint",
    "LogicalSolveResult", "SolveStatus", "solve_logically",
    "QueenConstraint", "AdjacencyFact", "derive_constraints",
]

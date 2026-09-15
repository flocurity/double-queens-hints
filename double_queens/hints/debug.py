"""Cosmetic region symbols never enter the reasoning model."""
from collections import Counter
from html import escape
import os
import sys

from ..board import Board, CellState

_COLORS = ("🔴", "🔵", "🟢", "🟡", "🟣", "🟠", "🟤", "⚫", "⚪", "🩶", "🩵")


def _supports_emojis() -> bool:
    # Encoding is a useful heuristic, but cannot detect installed font glyphs.
    if os.environ.get("TERM") == "dumb":
        return False
    encoding = getattr(sys.stdout, "encoding", None)
    if not encoding:
        return False
    try:
        ("".join(_COLORS) + "👑❌").encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return False
    return True


def _name(region: str) -> str:
    return escape(region).replace("|", "&#124;").replace("\n", " ").replace("`", "&#96;")


def render_board(
    board: Board, *, use_emojis: bool | None = None, legend: bool = False
) -> str:
    """Render compact cells, with an optional legend and emoji override."""
    if use_emojis is None:
        use_emojis = _supports_emojis()
    visuals = {region: _COLORS[i % len(_COLORS)]
               for i, region in enumerate(board.region_ids)}

    def symbol(region: str) -> str:
        return visuals[region] if use_emojis else _name(region)

    lines: list[str] = []
    if legend:
        lines += ["Color Region Legend", ""]
        for region, emoji in visuals.items():
            lines.append(f"- {emoji} = {_name(region)}" if use_emojis else f"- {_name(region)}")
        lines.append("")
    lines += ["| Line / Col | " + " | ".join(f"Col {c + 1}" for c in range(board.size))
              + " | Queen Region(s) |", "| :--- | " + " :---: |" * (board.size + 1)]
    for r in range(board.size):
        row = []
        for cell in board.row(r):
            region = board.regions[r][cell.col]
            state = board.at(cell)
            if use_emojis:
                marker = {CellState.QUEEN: "👑", CellState.EXCLUDED: "❌",
                          CellState.UNKNOWN: visuals[region]}[state]
            else:
                prefix = {CellState.QUEEN: "Q ", CellState.EXCLUDED: "X ",
                          CellState.UNKNOWN: ""}[state]
                marker = prefix + _name(region)
            row.append(marker)
        counts = Counter(board.regions[r][c.col] for c in board.queens(board.row(r)))
        multiplier = "×" if use_emojis else "x"
        summary = "  ".join(symbol(region) + (f" {multiplier}{count}" if count > 1 else "")
                            for region, count in sorted(counts.items())) or ("—" if use_emojis else "-")
        lines.append(f"| **Line {r + 1}** | " + " | ".join(row) + f" | {summary} |")
    return "\n".join(lines)

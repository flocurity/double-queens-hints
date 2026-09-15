"""Cosmetic region symbols never enter the reasoning model."""
from collections import Counter
from html import escape

from ..board import Board, CellState

_COLORS = ("🔴", "🔵", "🟢", "🟡", "🟣", "🟠", "🟤", "⚫", "⚪", "🩶", "🩵")


def render_board(board: Board) -> str:
    visuals = {region: (_COLORS[i % len(_COLORS)], f"R{i + 1}")
               for i, region in enumerate(board.region_ids)}

    def symbol(region: str) -> str:
        emoji, label = visuals[region]
        return f"{emoji} `[{label}]`"

    lines = ["Color Region Legend", ""]
    for region, (emoji, label) in visuals.items():
        name = escape(region).replace("|", "&#124;").replace("\n", " ").replace("`", "&#96;")
        lines.append(f"- [{label}] = {emoji} {name}")
    lines += ["", "| Line / Col | " + " | ".join(f"Col {c + 1}" for c in range(board.size))
              + " | Queen Region(s) |", "| :--- | " + " :---: |" * (board.size + 1)]
    for r in range(board.size):
        row = []
        for cell in board.row(r):
            region = board.regions[r][cell.col]
            emoji, label = visuals[region]
            marker = {CellState.QUEEN: "👑", CellState.EXCLUDED: "❌", CellState.UNKNOWN: emoji}[board.at(cell)]
            row.append(f"{marker} `[{label}]`")
        counts = Counter(board.regions[r][c.col] for c in board.queens(board.row(r)))
        summary = "  ".join(symbol(region) + (f" ×{count}" if count > 1 else "")
                            for region, count in sorted(counts.items())) or "—"
        lines.append(f"| **Line {r + 1}** | " + " | ".join(row) + f" | {summary} |")
    return "\n".join(lines)

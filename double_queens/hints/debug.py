"""Cosmetic region symbols never enter the reasoning model."""
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from html import escape
import os
import sys
import unicodedata

from ..board import Board, CellState

_COLORS = ("🔴", "🔵", "🟢", "🟡", "🟣", "🟠", "🟤", "⚫", "⚪", "🩶", "🩵")

# Newer hearts are drawn by the font but treated as narrow by VS Code's
# older terminal width tables. Keep compatibility data out of puzzle logic.
_VSCODE_WIDTHS = {"🩶": 1, "🩵": 1}


@dataclass(frozen=True)
class _DisplayLayout:
    """Best-effort Unicode sizing with explicit terminal/font calibration.

    Overrides are complete glyph strings, so multi-code-point glyphs can be
    calibrated too. This is not a font measurement or a full Unicode shaper.
    """

    glyph_widths: Mapping[str, int]

    def width(self, text: str) -> int:
        total = 0
        while text:
            glyph = next((g for g in sorted(self.glyph_widths, key=len, reverse=True)
                          if text.startswith(g)), None)
            if glyph is not None:
                total += self.glyph_widths[glyph]
                text = text[len(glyph):]
                continue
            char, text = text[0], text[1:]
            if unicodedata.combining(char) or unicodedata.category(char) in ('Mn', 'Me', 'Cf'):
                continue
            total += 2 if unicodedata.east_asian_width(char) in ('W', 'F') else 1
        return total

    def pad(self, text: str, width: int) -> str:
        return text + ' ' * max(0, width - self.width(text))


def _display_layout(profile: str, glyph_widths: Mapping[str, int] | None) -> _DisplayLayout:
    if profile == 'auto':
        profile = 'vscode' if os.environ.get('TERM_PROGRAM') == 'vscode' else 'unicode'
    if profile not in ('unicode', 'vscode'):
        raise ValueError('terminal_profile must be auto, unicode, or vscode')
    widths = dict(_VSCODE_WIDTHS) if profile == 'vscode' else {}
    if glyph_widths:
        for glyph, width in glyph_widths.items():
            if not glyph or not isinstance(width, int) or width < 0:
                raise ValueError('Glyph overrides require nonempty strings and nonnegative integer widths')
        widths.update(glyph_widths)
    return _DisplayLayout(widths)


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
    board: Board, *, use_emojis: bool | None = None, legend: bool = False,
    terminal_profile: str = 'auto', glyph_widths: Mapping[str, int] | None = None,
) -> str:
    """Render Markdown; calibrate glyph_widths for local terminal/font metrics."""
    layout = _display_layout(terminal_profile, glyph_widths)
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
    table = [["Line / Col", *(f"Col {c + 1}" for c in range(board.size)),
              "Queen Region(s)"]]
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
        table.append([f"Line {r + 1:02d}", *row, summary])
    widths = [max(5, *(layout.width(row[c]) for row in table))
              for c in range(board.size + 2)]

    def format_row(row: list[str]) -> str:
        return "| " + " | ".join(
            layout.pad(value, width)
            for value, width in zip(row, widths)
        ) + " |"

    lines.append(format_row(table[0]))
    lines.append("| " + " | ".join(
        ":" + "-" * (width - 1) if c == 0 else ":" + "-" * (width - 2) + ":"
        for c, width in enumerate(widths)
    ) + " |")
    lines.extend(format_row(row) for row in table[1:])
    return "\n".join(lines)

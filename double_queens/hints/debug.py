"""Cosmetic region symbols never enter the reasoning model."""
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from html import escape
import os
import random
import sys
import unicodedata
from types import MappingProxyType

from ..board import Board, CellState, RegionId

_COLORS = ("🔴", "🔵", "🟢", "🟡", "🟣", "🟠", "🟤", "⚫", "⚪", "🩶", "🩵")

# Newer hearts are drawn by the font but treated as narrow by VS Code's
# older terminal width tables. Keep compatibility data out of puzzle logic.
_VSCODE_WIDTHS = {"🩶": 1, "🩵": 1}


@dataclass
class RegionPalette:
    """Stable, session-owned mapping from region IDs to display glyphs."""

    glyphs: tuple[str, ...]
    _mapping: dict[RegionId, str] = field(default_factory=dict, init=False)

    @classmethod
    def randomized(
        cls,
        *,
        seed: int | str | bytes | None = None,
        rng: random.Random | None = None,
        glyphs: Iterable[str] | None = None,
    ) -> "RegionPalette":
        """Create a shuffled palette; inject a seed or RNG for deterministic tests."""
        if seed is not None and rng is not None:
            raise ValueError("Provide either seed or rng, not both")
        available = list(_COLORS if glyphs is None else glyphs)
        if not available:
            raise ValueError("A region palette requires at least one glyph")
        if len(set(available)) != len(available):
            raise ValueError("Region palette glyphs must be unique")
        (rng or random.Random(seed)).shuffle(available)
        return cls(tuple(available))

    def prepare(self, region_ids: Iterable[RegionId | str]) -> None:
        """Assign unseen regions deterministically within this palette session."""
        for region_id in sorted(set(region_ids)):
            self.glyph_for(region_id)

    def glyph_for(self, region_id: RegionId | str) -> str:
        region = RegionId(region_id)
        if region not in self._mapping:
            self._mapping[region] = self.glyphs[len(self._mapping) % len(self.glyphs)]
        return self._mapping[region]

    @property
    def mapping(self) -> Mapping[RegionId, str]:
        """Expose a read-only snapshot for diagnostics and structured logging."""
        return MappingProxyType(dict(self._mapping))


@dataclass
class DebugRenderContext:
    """Presentation state shared by every board and hint in one debug trace."""

    palette: RegionPalette
    use_emojis: bool
    terminal_profile: str = "auto"
    glyph_widths: Mapping[str, int] | None = None

    @classmethod
    def randomized(
        cls,
        *,
        seed: int | str | bytes | None = None,
        rng: random.Random | None = None,
        use_emojis: bool | None = None,
        glyphs: Iterable[str] | None = None,
        terminal_profile: str = "auto",
        glyph_widths: Mapping[str, int] | None = None,
    ) -> "DebugRenderContext":
        return cls(
            palette=RegionPalette.randomized(seed=seed, rng=rng, glyphs=glyphs),
            use_emojis=_supports_emojis() if use_emojis is None else use_emojis,
            terminal_profile=terminal_profile,
            glyph_widths=glyph_widths,
        )

    def prepare(self, region_ids: Iterable[RegionId | str]) -> None:
        self.palette.prepare(region_ids)

    def glyph_for(self, region_id: RegionId | str) -> str:
        return self.palette.glyph_for(region_id)

    def display_region(self, region_id: RegionId | str) -> str:
        return self.glyph_for(region_id) if self.use_emojis else str(region_id)

    @property
    def mapping(self) -> Mapping[RegionId, str]:
        return self.palette.mapping


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
    context: DebugRenderContext | None = None,
) -> str:
    """Render a compact terminal grid using calibrated glyph display widths."""
    if context is not None:
        context.prepare(board.region_ids)
        use_emojis = context.use_emojis
        terminal_profile = context.terminal_profile
        glyph_widths = context.glyph_widths
    layout = _display_layout(terminal_profile, glyph_widths)
    if use_emojis is None:
        use_emojis = _supports_emojis()
    visuals = {
        region: context.glyph_for(region) if context is not None
        else _COLORS[i % len(_COLORS)]
        for i, region in enumerate(board.region_ids)
    }

    def symbol(region: str) -> str:
        return visuals[region] if use_emojis else _name(region)

    lines: list[str] = []
    if legend:
        lines += ["Color Region Legend", ""]
        for region, emoji in visuals.items():
            lines.append(f"- {emoji} = {_name(region)}" if use_emojis else f"- {_name(region)}")
        lines.append("")
    table = []
    summaries = []
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
                            for region, count in sorted(counts.items())) or "-"
        table.append(row)
        summaries.append(summary)
    headers = [str(c + 1) for c in range(board.size)]
    widths = [max(2, layout.width(headers[c]),
                  *(layout.width(row[c]) + (0 if use_emojis else 1) for row in table))
              for c in range(board.size)]
    row_width = max(2, len(str(board.size)))

    def grid(row: list[str]) -> str:
        return "".join(layout.pad(value, width) for value, width in zip(row, widths))

    lines.append(" " * (row_width + 1) + grid(headers) + "|Queen(s)")
    lines.extend(f"{r + 1:0{row_width}d} " + grid(row) + "|" + summary
                 for r, (row, summary) in enumerate(zip(table, summaries)))
    return "\n".join(lines)

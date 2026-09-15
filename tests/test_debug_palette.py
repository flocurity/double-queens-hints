"""Stable randomized palettes shared by debug boards and human hints."""
from types import MappingProxyType, SimpleNamespace

import pytest

from double_queens import (
    Action, Board, Cell, CellFact, CellState, DebugRenderContext, Deduction,
    Group, GroupKind, Premise, RegionPalette, Rule, render_board, render_hint,
)
from double_queens.hints import debug

U, Q, X = CellState.UNKNOWN, CellState.QUEEN, CellState.EXCLUDED
REGIONS = tuple(f"region_{index}" for index in range(8))


def palette_mapping(seed: int) -> dict[str, str]:
    palette = RegionPalette.randomized(seed=seed)
    palette.prepare(REGIONS)
    return {str(region): glyph for region, glyph in palette.mapping.items()}


def region_deduction() -> Deduction:
    cells = tuple(Cell(0, col) for col in range(4))
    return Deduction(
        actions=(Action(Cell(0, 3), Q),),
        rule=Rule.FORCED_REMAINING_CELLS,
        premises=(Premise(
            facts=(CellFact(Cell(0, 0), Q), CellFact(Cell(0, 1), X),
                   CellFact(Cell(0, 2), X), CellFact(Cell(0, 3), U)),
            group=Group(GroupKind.REGION, "region_0", cells),
            required_queens=2,
        ),),
    )


def test_seeded_region_palette_is_deterministic_and_observable():
    first = palette_mapping(1729)
    second = palette_mapping(1729)
    assert first == second
    assert isinstance(RegionPalette.randomized(seed=1).mapping, MappingProxyType)


def test_different_seeds_produce_different_deterministic_mappings():
    assert palette_mapping(1) != palette_mapping(2)
    assert palette_mapping(1) == palette_mapping(1)
    assert palette_mapping(2) == palette_mapping(2)


def test_palette_uses_each_available_glyph_before_reusing_one():
    glyphs = ("a", "b", "c")
    palette = RegionPalette.randomized(seed=4, glyphs=glyphs)
    assigned = [palette.glyph_for(f"region_{index}") for index in range(4)]
    assert set(assigned[:3]) == set(glyphs)
    assert len(set(assigned[:3])) == 3
    assert assigned[3] == assigned[0]


def test_repeated_board_rendering_with_one_context_preserves_colors():
    board = Board([[f"region_{row}" for _ in range(4)] for row in range(4)])
    context = DebugRenderContext.randomized(seed=23, use_emojis=True)
    first = render_board(board, context=context)
    mapping = dict(context.mapping)
    second = render_board(board, context=context)
    assert first == second
    assert dict(context.mapping) == mapping
    assert all(context.glyph_for(region) in first for region in board.region_ids)


def test_board_and_all_region_hint_levels_share_one_palette_glyph():
    board = Board([["region_0"] * 4, ["region_1"] * 4,
                   ["region_2"] * 4, ["region_3"] * 4])
    deduction = region_deduction()
    context = DebugRenderContext.randomized(seed=99, use_emojis=True)
    rendered_board = render_board(board, context=context)
    glyph = context.glyph_for("region_0")
    hints = [
        render_hint(deduction, level, region_display=context.display_region)
        for level in range(1, 5)
    ]
    assert glyph in rendered_board
    assert hints[0] == f"Look at region {glyph}."
    assert hints[1].startswith(f"Region {glyph} requires 2 queens")
    assert f"in region {glyph}" in hints[2]
    assert hints[3] == "Place a queen at L1C4."
    assert glyph not in hints[3]
    assert render_hint(deduction, 1) == "Look at region region_0."


def test_non_emoji_context_keeps_text_board_and_region_hints():
    board = Board([["region_0"] * 4, ["region_1"] * 4,
                   ["region_2"] * 4, ["region_3"] * 4])
    context = DebugRenderContext.randomized(seed=99, use_emojis=False)
    rendered = render_board(board, context=context)
    hints = [
        render_hint(region_deduction(), level, region_display=context.display_region)
        for level in range(1, 5)
    ]
    assert "region_0" in rendered
    assert not any(glyph in rendered for glyph in context.palette.glyphs)
    assert hints[0] == "Look at region region_0."
    assert hints[1].startswith("Region region_0 requires 2 queens")
    assert "in region region_0" in hints[2]
    assert hints[3] == "Place a queen at L1C4."


def test_context_reuses_existing_terminal_capability_detection(monkeypatch):
    monkeypatch.setenv("TERM", "dumb")
    monkeypatch.setattr(debug.sys, "stdout", SimpleNamespace(encoding="utf-8"))
    context = DebugRenderContext.randomized(seed=7)
    assert not context.use_emojis


@pytest.mark.parametrize(
    "kwargs",
    [
        {"seed": 1, "rng": __import__("random").Random(1)},
        {"glyphs": ()},
        {"glyphs": ("🔴", "🔴")},
    ],
)
def test_invalid_palette_configuration_is_rejected(kwargs):
    with pytest.raises(ValueError):
        RegionPalette.randomized(**kwargs)

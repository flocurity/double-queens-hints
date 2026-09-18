"""Three-column colored cells, with independent checks of content and styles."""
import pytest
from rich.console import Console
from rich.text import Text

from double_queens import Board, Cell, CellState, DebugRenderContext, render_board


def cell_style(text, row, col, size):
    lines = text.plain.splitlines(keepends=True)
    offset = sum(map(len, lines[:row + 1])) + max(2, len(str(size))) + 1 + col * 3
    return text.get_style_at_offset(Console(), offset)


def test_colored_cells_preserve_states_geometry_and_checkerboard():
    board = Board(['AABB', 'ACBB', 'ACDD', 'CCDD'],
                  [[1, 0, -1, 0], [0]*4, [0]*4, [0]*4])
    before = board.state
    context = DebugRenderContext.randomized(seed=42, use_emojis=True)
    rendered = render_board(board, context=context)
    text = Text.from_ansi(rendered)
    lines = text.plain.splitlines()
    assert lines[0] == '    1  2  3  4   Queen(s)'
    for r in range(4):
        assert lines[r + 1].startswith(f'{r + 1:02d} ')
        for c in range(4):
            marker = {CellState.UNKNOWN: ' ', CellState.QUEEN: 'Q', CellState.EXCLUDED: '×'}[board.at(Cell(r, c))]
            assert lines[r + 1][3+c*3:6+c*3] == f' {marker} '
            color = context.color_for(board.regions[r][c])
            rgb = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))
            expected = tuple(round(v * .93) for v in rgb) if (r+c) % 2 == 0 else rgb
            style = cell_style(text, r, c, 4)
            assert tuple(style.bgcolor.get_truecolor()) == expected
            assert style.bold
    assert not any(g in text.plain for g in ('|', '─', '│', '🔴', '👑', '❌'))
    assert board.state == before
    assert render_board(board, context=context) == rendered


@pytest.mark.parametrize('size', [1, 9, 10, 13])
def test_compact_dimensions_and_exact_grid_width(size):
    board = Board([[str(r)] * size for r in range(size)])
    lines = Text.from_ansi(render_board(board, use_emojis=True)).plain.splitlines()
    assert len(lines) == size + 5
    assert lines[0] == '   ' + ''.join(f'{c:^3}' for c in range(1, size+1)) + '  Queen(s)'
    for r, line in enumerate(lines[1:size + 1], 1):
        assert line == f'{r:02d} ' + ' ' * (size * 3) + '  -'
    assert str(Cell(5, 4)) == 'L6C5'


@pytest.mark.parametrize('profile', ['unicode', 'vscode', 'auto'])
def test_region_emoji_metrics_do_not_affect_grid(profile):
    board = Board([list('ABC')] * 3)
    context = DebugRenderContext.randomized(seed=1, use_emojis=True,
        glyphs=('🤍', '🩶', '🩵'), terminal_profile=profile, glyph_widths={'🤍': 1})
    text = Text.from_ansi(render_board(board, context=context))
    assert text.plain.splitlines()[1] == '01 ' + ' ' * 9 + '  -'
    assert all(cell_style(text, 0, c, 3).bgcolor is not None for c in range(3))


def test_symbol_width_override_preserves_three_columns():
    board = Board(['AAA'] * 3, [[1, -1, 0], [0]*3, [0]*3])
    text = Text.from_ansi(render_board(board, use_emojis=True, glyph_widths={'×': 2})).plain
    assert text.splitlines()[1].startswith('01  Q ×    ')


def test_legend_and_summary_use_same_region_background():
    board = Board(['AAA', 'BBB', 'CCC'], [[1, 0, 1], [0]*3, [0]*3])
    context = DebugRenderContext.randomized(seed=42, use_emojis=True)
    text = Text.from_ansi(render_board(board, context=context))
    plain = text.plain
    assert plain.splitlines()[1].endswith('  A    A ')
    assert '×2' not in plain
    assert text.get_style_at_offset(Console(), plain.index('A')).bgcolor.name == context.color_for('A')
    assert 'Color Region Legend' not in plain
    assert 'Color Region Legend' in render_board(board, use_emojis=True, legend=True)


def test_text_fallback_preserves_names_and_states_without_ansi():
    board = Board(['ABC'] * 3, [[1, -1, 0], [0]*3, [0]*3])
    rendered = render_board(board, use_emojis=False)
    assert '\x1b' not in rendered
    assert '|' not in rendered
    assert 'Q A' in rendered and 'X B' in rendered and 'C' in rendered


def test_symmetric_summaries_preserve_order_badges_and_empty_styles():
    board = Board(['ZAAA', 'BCCC', 'ZCCC', 'BCCC'],
                  [[1, 0, 1, 0], [0]*4, [1, 0, 0, 0], [0]*4])
    before = board.state
    context = DebugRenderContext.randomized(seed=17, use_emojis=True)
    rendered = render_board(board, context=context)
    text = Text.from_ansi(rendered)
    lines = text.plain.splitlines()
    assert len(lines) == 9
    assert lines[1][17:] == ' Z    A '  # Board order, not alphabetic order.
    assert lines[5] == lines[7] == ''
    # Check raw ANSI output too: blank lines must contain no style escapes.
    assert rendered.splitlines()[5] == rendered.splitlines()[7] == ''
    assert lines[6] == '   ' + ' Z ' + '   ' + ' A ' + '   '
    assert lines[8] == '   ' + ' Z ' + '   ' * 3
    assert '×2' not in text.plain
    offsets = [sum(len(line) + 1 for line in lines[:i]) for i in range(len(lines))]
    for line in (5, 7):
        assert text.get_style_at_offset(Console(), offsets[line]).bgcolor is None
    for slot, labels in enumerate((('Z', None, 'A', None), ('Z', None, None, None))):
        for col, label in enumerate(labels):
            for char in range(3):
                style = text.get_style_at_offset(Console(), offsets[6 + 2 * slot] + 3 + col * 3 + char)
                if label is None:
                    assert style.bgcolor is None
                else:
                    assert style.bgcolor.name == context.color_for(label)
    assert board.state == before
    assert render_board(board, context=context) == rendered


def test_column_badges_follow_top_to_bottom_not_region_sort_order():
    board = Board(['ZZZ', 'BBB', 'AAA'], [[1, 0, 0], [0]*3, [1, 0, 0]])
    lines = Text.from_ansi(render_board(board, use_emojis=True)).plain.splitlines()
    assert lines[-3][3:6] == ' Z '
    assert lines[-1][3:6] == ' A '


def test_long_region_names_use_same_visible_glyph_in_both_summaries():
    board = Board([['long_region']*3, ['B']*3, ['C']*3], [[1, 0, 0], [0]*3, [0]*3])
    context = DebugRenderContext.randomized(seed=3, use_emojis=True, terminal_profile='unicode')
    lines = Text.from_ansi(render_board(board, context=context)).plain.splitlines()
    glyph = context.glyph_for('long_region')
    assert glyph in lines[1] and glyph in lines[-3]
    assert Text(lines[-3][3:]).cell_len == 9
    fallback = render_board(board, use_emojis=False).splitlines()
    assert fallback[1].endswith('  long_region')
    assert fallback[-3].strip() == 'long_region'
    assert fallback[-2] == fallback[-4] == ''
    assert not fallback[-1].strip()


@pytest.mark.parametrize('options', [{'terminal_profile': 'invalid'}, {'glyph_widths': {'': 2}},
                                    {'glyph_widths': {'🤍': -1}}])
def test_invalid_display_calibration(options):
    with pytest.raises(ValueError):
        render_board(Board([['A']]), **options)

"""Regression coverage for terminal columns and presentation coordinates."""
import pytest

from debug_boards import debug_boards
from double_queens import Board, Cell, CellState, render_board
from double_queens.hints import debug
from double_queens.log import get_logger

log = get_logger(__name__)


def observed_width(text: str) -> int:
    # Independent, fixed display model for this test's known glyphs.
    width = len(text)
    for glyph, columns in {'🔴': 2, '🤍': 2, '🔵': 2, '🟢': 2,
                           '👑': 2, '❌': 2, '界': 2,
                           'e\u0301': 1, '👩\u200d💻': 2}.items():
        width += text.count(glyph) * (columns - len(glyph))
    return width


def pipe_columns(line: str) -> list[int]:
    return [observed_width(line[:i]) for i, char in enumerate(line) if char == '|']


@pytest.mark.parametrize('palette', [
    ('🔴', '🤍', '🔵', '🟢'),
    ('·', '界', 'e\u0301', '👩\u200d💻'),
])
@debug_boards
def test_mixed_glyphs_align_in_terminal(monkeypatch, palette):
    monkeypatch.setattr(debug, '_COLORS', palette)
    regions = ['AABB', 'ACBB', 'ACDD', 'CCDD']
    state = [[CellState.UNKNOWN] * 4 for _ in range(4)]
    state[0][0] = CellState.QUEEN
    state[3][3] = CellState.EXCLUDED
    board = Board(regions, state)
    before = board.state
    rendered = render_board(board, use_emojis=True, terminal_profile='unicode',
                            glyph_widths={'👩\u200d💻': 2})
    log.info('Mixed region glyphs:', board=rendered)
    lines = rendered.splitlines()
    expected_columns = pipe_columns(lines[0])
    assert len(expected_columns) == 7
    assert all(pipe_columns(line) == expected_columns for line in lines)
    assert len({observed_width(line) for line in lines}) == 1
    for r, source in enumerate(regions):
        cells = [cell.strip() for cell in lines[r + 2].split('|')[2:-2]]
        expected = [palette[ord(region) - ord('A')] for region in source]
        if r == 0:
            expected[0] = '👑'
        if r == 3:
            expected[3] = '❌'
        assert cells == expected
    assert board.state == before
    assert 'Color Region Legend' not in rendered


@debug_boards
def test_row_numbers_are_padded_without_changing_cell_coordinates():
    board = Board([[str(r)] * 12 for r in range(12)])
    rendered = render_board(board, use_emojis=False)
    lines = rendered.splitlines()
    assert [line.split('|')[1].strip() for line in lines[2:]] == [
        f'Line {r:02d}' for r in range(1, 13)
    ]
    assert all(pipe_columns(line) == pipe_columns(lines[0]) for line in lines)
    assert str(Cell(5, 4)) == 'L6C5'
    assert board.row(0)[0] == Cell(0, 0)


@pytest.mark.parametrize('white_width', [1, 2])
@debug_boards
def test_vscode_padding_uses_calibrated_widths(monkeypatch, white_width):
    palette = ('🔴', '🔵', '⚪', '🤍', '🩶', '🩵')
    monkeypatch.setattr(debug, '_COLORS', palette)
    monkeypatch.setenv('TERM_PROGRAM', 'vscode')
    board = Board([list('ABCDEF')] * 6)
    rendered = render_board(board, use_emojis=True, glyph_widths={'🤍': white_width})
    log.info('VS Code calibrated region cells:', board=rendered)
    # Six content columns have width five, plus one space on each side.
    cells = rendered.splitlines()[2].split('|')[2:-2]
    expected_widths = (2, 2, 2, white_width, 1, 1)
    for cell, glyph, width in zip(cells, palette, expected_widths):
        assert cell == ' ' + glyph + ' ' * (6 - width)
    # The one-column compensation accumulates correctly across a full row.
    simulated = len(rendered.splitlines()[2])
    for glyph, width in zip(palette, expected_widths):
        simulated += width - len(glyph)
    assert simulated == len(rendered.splitlines()[0])
    standard = render_board(board, use_emojis=True, terminal_profile='unicode')
    assert standard.splitlines()[2].split('|')[6] == ' 🩶    '


@debug_boards
def test_width_overrides_cover_summary_and_do_not_leak(monkeypatch):
    monkeypatch.setattr(debug, '_COLORS', ('🤍', '🔴', '🔵'))
    board = Board([list('AAA'), list('BBB'), list('CCC')], [[1, 0, 0], [0]*3, [0]*3])
    calibrated = render_board(board, use_emojis=True, terminal_profile='unicode', glyph_widths={'🤍': 1})
    standard = render_board(board, use_emojis=True, terminal_profile='unicode')
    assert len(calibrated.splitlines()[2].split('|')[-2]) == len(standard.splitlines()[2].split('|')[-2]) + 1
    assert debug._COLORS == ('🤍', '🔴', '🔵')


@pytest.mark.parametrize('options', [{'terminal_profile': 'invalid'}, {'glyph_widths': {'': 2}},
                                    {'glyph_widths': {'🤍': -1}}])
def test_invalid_display_calibration(options):
    with pytest.raises(ValueError):
        render_board(Board([['A']]), **options)

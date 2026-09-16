"""Real-game acceptance fixtures, manually transcribed without a solution."""
import pytest

from debug_boards import debug_boards, suspend_debug_tracing
from double_queens import (
    Action, Board, Cell, CellFact, CellState, ContradictionError, Deduction,
    Group, GroupKind, Premise, Rule, next_hint, render_board,
)
from double_queens.log import get_logger

log = get_logger(__name__)

# Source of truth: the user-supplied screenshot, "Niveau 21 - Double", 3/18.
# This real game is the historical L6C5 regression that motivated the project.
# A=grey-blue, B=purple, C=cyan, D=orange, E=yellow,
# F=coral/red, G=green, H=blue, I=pink.
# One character per cell, left to right; rows are top to bottom.
KNOWN_GAME_001_REGIONS = (
    'AAABBBCCC',  # L1
    'AAABBBBCC',  # L2
    'DAABBBCCC',  # L3
    'DAAAAEECF',  # L4
    'DGAAEEEFF',  # L5
    'DGGGGEFFF',  # L6
    'DDDGGEFFI',  # L7
    'HHHHHEEII',  # L8
    'HHEEEEIII',  # L9
)

# . = visibly unmarked/UNKNOWN, Q = confirmed crown, X = visible cross.
# No automatic adjacency exclusions or other inferred marks are added here.
KNOWN_GAME_001_INITIAL_STATE = (
    '.........',  # L1
    '....X.X..',  # L2
    '.........',  # L3
    'XXX...X..',  # L4
    'XQX...X..',  # L5
    'XXXX.....',  # L6
    '.XQXXX...',  # L7
    '.XXXQXXX.',  # L8
    '...XXX...',  # L9
)


def make_known_game_001() -> Board:
    """Decode only the explicit screenshot transcription into a fresh board."""
    states = {'.': CellState.UNKNOWN, 'Q': CellState.QUEEN, 'X': CellState.EXCLUDED}
    return Board(KNOWN_GAME_001_REGIONS,
                 [[states[mark] for mark in row] for row in KNOWN_GAME_001_INITIAL_STATE])


@pytest.fixture
def known_game_001() -> Board:
    return make_known_game_001()

@debug_boards(log_all_deductions=True)
def test_known_game_001_next_hint_l6c5(known_game_001: Board) -> None:
    board = known_game_001
    before = board.state
    assert board.size == 9
    assert board.queens(board.cells()) == (Cell(4, 1), Cell(6, 2), Cell(7, 4))
    assert len(board.excluded(board.cells())) == 26
    assert len(board.unknown(board.cells())) == 52
    board.validate()

    deduction = next_hint(board)
    assert deduction is not None
    assert board.state == before
    # Explicit evidence from the screenshot, independent of group-query output.
    green_cells = (Cell(4, 1), Cell(5, 1), Cell(5, 2), Cell(5, 3),
                   Cell(5, 4), Cell(6, 3), Cell(6, 4))
    assert deduction.rule == Rule.FORCED_REMAINING_CELLS
    assert deduction.actions == (Action(Cell(5, 4), CellState.QUEEN),)
    assert deduction.difficulty == 1
    assert deduction.premises == (Premise(
        facts=(
            CellFact(Cell(4, 1), CellState.QUEEN),
            CellFact(Cell(5, 1), CellState.EXCLUDED),
            CellFact(Cell(5, 2), CellState.EXCLUDED),
            CellFact(Cell(5, 3), CellState.EXCLUDED),
            CellFact(Cell(5, 4), CellState.UNKNOWN),
            CellFact(Cell(6, 3), CellState.EXCLUDED),
            CellFact(Cell(6, 4), CellState.EXCLUDED),
        ),
        group=Group(GroupKind.REGION, 'G', green_cells),
        required_queens=2,
    ),)

@debug_boards
def test_known_game_001_logical_replay(known_game_001: Board) -> None:
    board = known_game_001
    log.info('start', game="real 001")
    history: list[Deduction] = []
    try:
        while not board.is_solved():
            before = board.state
            deduction = next_hint(board)
            assert board.state == before
            if deduction is None:
                break
            history.append(deduction)
            unknown_before = len(board.unknown(board.cells()))
            board.apply(deduction)
            assert len(board.unknown(board.cells())) < unknown_before
    except ContradictionError:
        log.info('contradiction', game="real 001", board=render_board(board))
        raise

    assert history
    # Milestone 1's seven-step prefix is preserved; the new rule continues it.
    assert all(d.difficulty == 1 for d in history[:7])
    assert history[7].rule == Rule.COMMON_NEIGHBOR_EXCLUSION
    assert history[7].constraint.cells == frozenset((Cell(0, 5), Cell(1, 5)))
    assert history[7].constraint.queen_count == 1
    assert history[7].actions == (Action(Cell(0, 6), CellState.EXCLUDED),)
    assert len(history) == 32
    assert sum(d.rule == Rule.COMMON_NEIGHBOR_EXCLUSION for d in history) == 3
    assert board.is_solved()
    assert any(Action(Cell(5, 4), CellState.QUEEN) in d.actions for d in history)
    assert board.at(Cell(5, 4)) == CellState.QUEEN
    board.validate()
    if board.is_solved():
        log.info('solved', game="real 001")
        assert board.is_solved()
    elif len(history) == 7:
        log.info('STALLED', game="real 001",
                            reason='No supported milestone 1 deduction found')
        assert next_hint(board) is None
    else:
        log.info('Known game 001 logical progression changed from'
                 'the milestone 1 baseline', new_history=len(history))
        assert next_hint(board) is None
    # log.info(f'Deductions applied', count=len(history), board=render_board(board))
    final_state = board.state

    with suspend_debug_tracing():
        replay_board = make_known_game_001()
        for deduction in history:
            assert deduction == next_hint(replay_board)
            replay_board.apply(deduction)
        assert replay_board.state == final_state
        assert replay_board.regions == board.regions
        assert replay_board.is_solved() == board.is_solved()
        replay_board.validate()

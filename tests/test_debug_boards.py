"""Trace selection and structured log content, independent of console formatting."""
from inspect import signature
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

import debug_boards as helper
from double_queens import (
    Action, Board, Cell, CellFact, CellState, ContradictionError,
    DebugRenderContext, Deduction, Premise, Rule, find_deductions,
    render_deduction, render_hint, next_hint,
)


@pytest.fixture
def trace(monkeypatch):
    logger = Mock()
    context = DebugRenderContext.randomized(seed=42, use_emojis=True)
    monkeypatch.setattr(helper, 'log', logger)
    monkeypatch.setattr(helper, 'DebugRenderContext',
                        SimpleNamespace(randomized=lambda: context))
    return logger, context


def make_board():
    state = [[CellState.UNKNOWN] * 8 for _ in range(8)]
    state[0][0] = state[0][3] = CellState.QUEEN
    return Board([[str(r)] * 8 for r in range(8)], state)


@pytest.mark.parametrize('verbose', [False, True])
def test_trace_logs_selected_or_all_deductions_without_duplicates(trace, verbose):
    logger, context = trace

    def scenario(marker):
        board = make_board()
        candidates = find_deductions(board)
        # Deliberately apply a region deduction rather than the best hint.
        selected = next(d for d in candidates if d.rule == Rule.COMPLETED_GROUP
                        and d.premises[0].group.kind.value == 'region')
        board.apply(selected)
        return marker, candidates, selected

    decorated = (helper.debug_boards(log_all_deductions=True)(scenario)
                 if verbose else helper.debug_boards(scenario))
    assert signature(decorated) == signature(scenario)
    marker, candidates, selected = decorated('result')
    assert marker == 'result'
    details = [call for call in logger.info.call_args_list
               if call.args[0] in ('deduction created', 'deduction used')]
    expected = candidates if verbose else [selected]
    assert len(candidates) > 1
    assert [call.args[0] for call in details] == [
        'deduction created' if verbose else 'deduction used'] * len(expected)
    # Discovery logs creation order; the engine returns candidates in rank order.
    assert sorted(call.kwargs['deduction'] for call in details) == sorted(render_deduction(d) for d in expected)
    assert sorted(call.args[0] for call in logger.hint.call_args_list) == sorted([
        [render_hint(d, level, region_display=context.display_region) for level in range(1, 5)]
        for d in expected])
    boards = [call.kwargs for call in logger.info.call_args_list if call.args[0] == 'board']
    assert [entry['state'] for entry in boards] == ['created', 'after application']
    assert boards[-1]['step'] == 1
    assert [c.kwargs.get('step') for c in details] == [None if verbose else 1] * len(expected)
    assert [c.kwargs.get('step') for c in logger.hint.call_args_list] == [None if verbose else 1] * len(expected)
    glyph = context.glyph_for('0')
    assert all('\x1b[' in entry['board'] for entry in boards)
    selected_index = next(i for i, call in enumerate(details)
                          if call.kwargs['deduction'] == render_deduction(selected))
    selected_hints = logger.hint.call_args_list[selected_index].args[0]
    assert all(glyph in hint for hint in selected_hints[:3])
    assert len([c for c in logger.debug.call_args_list if c.args[0] == 'region_palette']) == 1
    if not verbose:
        events = [(c.args[0], c.kwargs.get('state')) if c[0] == 'info'
                  else ('hints', None) for c in logger.mock_calls if c[0] in ('info', 'hint')]
        start = events.index(('deduction used', None))
        assert events[start:] == [('deduction used', None),
                                  ('hints', None), ('board', 'after application')]


def test_discovery_only_is_quiet_in_bare_mode(trace):
    logger, _ = trace

    @helper.debug_boards
    def scenario():
        return find_deductions(make_board())

    assert scenario()
    assert not logger.hint.called
    assert not any(c.args[0].startswith('deduction') for c in logger.info.call_args_list)


@pytest.mark.parametrize('verbose', [False, True])
def test_malformed_hint_does_not_hide_rejected_application(trace, verbose):
    logger, _ = trace

    @helper.debug_boards(log_all_deductions=verbose)
    def scenario():
        board = make_board()
        before = board.state
        malformed = Deduction(
            (Action(Cell(3, 3), CellState.EXCLUDED), Action(Cell(0, 0), CellState.EXCLUDED)),
            Rule.QUEEN_ADJACENCY,
            (Premise((CellFact(Cell(7, 7), CellState.UNKNOWN),)),),
        )
        with pytest.raises(ContradictionError):
            board.apply(malformed)
        assert board.state == before

    scenario()
    assert not logger.hint.called
    assert len([c for c in logger.debug.call_args_list if c.args[0] == 'hint_rendering_skipped']) == 1
    assert logger.warning.call_args.args == ('application rejected',)
    assert logger.warning.call_args.kwargs['error_type'] == 'ContradictionError'
    assert logger.warning.call_args.kwargs['step'] == 1


def test_steps_reset_and_sequential_boards_are_not_repeated(trace):
    logger, _ = trace

    @helper.debug_boards
    def scenario():
        board = make_board()
        for _ in range(2):
            board.apply(next_hint(board))

    for _ in range(2):
        logger.reset_mock()
        scenario()
        assert [c.kwargs['step'] for c in logger.info.call_args_list
                if c.args[0] == 'deduction used'] == [1, 2]
        assert [c.kwargs['step'] for c in logger.hint.call_args_list] == [1, 2]
        assert [c.kwargs['state'] for c in logger.info.call_args_list
                if c.args[0] == 'board'] == ['created', 'after application', 'after application']


def test_boards_tracked_independently_and_external_changes_show_before(trace):
    logger, _ = trace
    original_apply = Board.apply
    external = make_board()

    @helper.debug_boards
    def scenario():
        first, second = make_board(), make_board()
        first.apply(next_hint(first))
        second.apply(next_hint(second))
        # Bypass the wrapper to simulate a change outside traced apply.
        original_apply(first, next_hint(first))
        first.apply(next_hint(first))
        external.apply(next_hint(external))

    scenario()
    boards = [c.kwargs for c in logger.info.call_args_list if c.args[0] == 'board']
    assert [(c['index'], c['state'], c.get('step')) for c in boards] == [
        (1, 'created', None), (2, 'created', None),
        (1, 'after application', 1), (2, 'after application', 2),
        (3, 'created', None),  # Validation copy created by the unwrapped apply.
        (1, 'before application', 3), (1, 'after application', 3),
        (4, 'before application', 4), (4, 'after application', 4),
    ]


@pytest.mark.parametrize('verbose', [False, True])
def test_suspension_is_nested_restored_on_error_and_does_not_consume_steps(trace, verbose):
    logger, _ = trace

    @helper.debug_boards(log_all_deductions=verbose)
    def scenario():
        board = make_board()
        board.apply(next_hint(board))
        count = len(logger.mock_calls)
        with pytest.raises(RuntimeError, match='sentinel'):
            with helper.suspend_debug_tracing():
                with helper.suspend_debug_tracing():
                    other = make_board()
                    other.apply(next_hint(other))
                board.apply(next_hint(board))
                assert len(logger.mock_calls) == count
                raise RuntimeError('sentinel')
        board.apply(next_hint(board))

    scenario()
    boards = [c.kwargs for c in logger.info.call_args_list if c.args[0] == 'board']
    assert [(c['state'], c.get('step')) for c in boards] == [
        ('created', None), ('after application', 1),
        ('before application', 2), ('after application', 2),
    ]


def test_known_game_traces_32_attempts_but_executes_all_64_applications(trace, monkeypatch):
    import test_known_games as games

    logger, _ = trace
    monkeypatch.setattr(games, 'log', Mock())
    original_apply = Board.apply
    applications = []

    def counted_apply(board, deduction):
        original_apply(board, deduction)
        applications.append(deduction)

    monkeypatch.setattr(Board, 'apply', counted_apply)
    games.test_known_game_001_logical_replay(games.make_known_game_001())
    assert len(applications) == 64
    assert applications[:32] == applications[32:]
    assert [c.kwargs['step'] for c in logger.info.call_args_list
            if c.args[0] == 'deduction used'] == list(range(1, 33))
    assert logger.hint.call_count == 32
    assert len([c for c in logger.info.call_args_list if c.args[0] == 'board']) == 33

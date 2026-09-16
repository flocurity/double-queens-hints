"""Test-only tracing; use pytest -s to display the logs."""
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from functools import wraps
from typing import ParamSpec, TypeVar
from unittest.mock import patch

from double_queens import (
    Board, DebugRenderContext, Deduction, render_board, render_deduction,
    render_hint,
)
from double_queens.log import get_logger

log = get_logger(__name__)

P = ParamSpec("P")
R = TypeVar("R")
_suspended = ContextVar("debug_boards_suspended", default=False)


@contextmanager
def suspend_debug_tracing() -> Iterator[None]:
    """Silence decorator tracing in this scope; nested scopes restore reliably."""
    token = _suspended.set(True)
    try:
        yield
    finally:
        _suspended.reset(token)


def debug_boards(
    test: Callable[P, R] | None = None, *, log_all_deductions: bool = False,
) -> Callable[P, R] | Callable[[Callable[P, R]], Callable[P, R]]:
    """Log applied deductions, or every candidate with log_all_deductions=True.

    Temporary wrappers call the original methods and preserve exceptions.
    functools.wraps preserves pytest fixture and parametrization discovery.
    Steps count observed apply attempts, including rejections, but not suspended
    applications. Each decorated execution starts a fresh trace.
    """
    if test is None:
        return lambda function: debug_boards(function, log_all_deductions=log_all_deductions)

    @wraps(test)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        original_init = Board.__init__
        original_apply = Board.apply
        original_post_init = Deduction.__post_init__
        applying = False
        boards: list[Board] = []
        last_render: dict[Board, str] = {}
        step = 0
        context = DebugRenderContext.randomized()
        palette_logged = False

        def show(board: Board, event: str, **fields) -> None:
            nonlocal palette_logged
            if _suspended.get():
                return
            index = next((i for i, item in enumerate(boards, 1) if item is board), None)
            if index is None:
                boards.append(board)
                index = len(boards)
            rendered = render_board(board, context=context)
            if event == "before application" and last_render.get(board) == rendered:
                return
            if context.use_emojis and not palette_logged:
                log.debug(
                    "region_palette",
                    mapping={str(region): glyph for region, glyph in context.mapping.items()},
                )
                palette_logged = True
            log.info("board", index=index, state=event, board=rendered, **fields)
            last_render[board] = rendered
        @wraps(original_init)
        def traced_init(board: Board, *init_args, **init_kwargs) -> None:
            try:
                original_init(board, *init_args, **init_kwargs)
            except Exception as error:
                if not _suspended.get():
                    log.error("board construction rejected", error_type=type(error).__name__, error=str(error))
                raise
            if not applying:
                show(board, "created")

        def show_deduction(deduction: Deduction, event: str, **fields) -> None:
            log.info(event, deduction=render_deduction(deduction), **fields)
            try:
                hints = [
                    render_hint(
                        deduction,
                        level,
                        region_display=context.display_region,
                    )
                    for level in range(1, 5)
                ]
            except StopIteration as error:
                log.debug(
                    "hint_rendering_skipped",
                    error_type=type(error).__name__,
                    error=str(error),
                    **fields,
                )
            else:
                log.hint(hints, **fields)

        def traced_post_init(deduction: Deduction) -> None:
            original_post_init(deduction)
            if log_all_deductions and not _suspended.get():
                show_deduction(deduction, "deduction created")

        def traced_apply(board: Board, deduction: Deduction) -> None:
            nonlocal applying, step
            observed = not _suspended.get()
            if observed:
                step += 1
                show(board, "before application", step=step)
                if not log_all_deductions:
                    show_deduction(deduction, "deduction used", step=step)
            applying = True
            board_before = render_board(board, context=context)
            try:
                original_apply(board, deduction)
            except Exception as error:
                if observed:
                    log.warning("application rejected", step=step, error_type=type(error).__name__, error=str(error))
                assert board_before == render_board(board, context=context), (
                    "Board was mutated by a rejected deduction"
                )
                raise
            else:
                show(board, "after application", step=step)
            finally:
                applying = False

        # Pytest may leave its progress marker on the current line, jump one line
        log.blank()
        log.info("test started", test=test.__name__)
        if args or kwargs:
            log.debug("parameters", args=args, kwargs=kwargs)
        token = _suspended.set(False)
        try:
            with patch.object(Board, "__init__", traced_init), \
                 patch.object(Board, "apply", traced_apply), \
                 patch.object(Deduction, "__post_init__", traced_post_init):
                return test(*args, **kwargs)
        finally:
            _suspended.reset(token)

    return wrapped

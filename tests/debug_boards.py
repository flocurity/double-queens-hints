"""Test-only tracing; pytest captures prints unless run with -s."""
from collections.abc import Callable
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


def debug_boards(test: Callable[P, R]) -> Callable[P, R]:
    """Print boards and deductions created during a test, including solver steps.

    Temporary wrappers call the original methods and preserve exceptions.
    functools.wraps preserves pytest fixture and parametrization discovery.
    """
    @wraps(test)
    def wrapped(*args: P.args, **kwargs: P.kwargs) -> R:
        original_init = Board.__init__
        original_apply = Board.apply
        original_post_init = Deduction.__post_init__
        applying = False
        boards: list[Board] = []
        context = DebugRenderContext.randomized()
        palette_logged = False

        def show(board: Board, event: str) -> None:
            nonlocal palette_logged
            index = next((i for i, item in enumerate(boards, 1) if item is board), None)
            if index is None:
                boards.append(board)
                index = len(boards)
            rendered = render_board(board, context=context)
            if context.use_emojis and not palette_logged:
                log.debug(
                    "region_palette",
                    mapping={str(region): glyph for region, glyph in context.mapping.items()},
                )
                palette_logged = True
            log.info("board", index=index, state=event, board=rendered)
        @wraps(original_init)
        def traced_init(board: Board, *init_args, **init_kwargs) -> None:
            try:
                original_init(board, *init_args, **init_kwargs)
            except Exception as error:
                log.error("board construction rejected", error_type=type(error).__name__, error=str(error))
                raise
            if not applying:
                show(board, "created")

        def traced_post_init(deduction: Deduction) -> None:
            original_post_init(deduction)
            log.info("deduction created", deduction=render_deduction(deduction))
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
                )
            else:
                log.hint(hints)

        def traced_apply(board: Board, deduction: Deduction) -> None:
            nonlocal applying
            show(board, "before application")
            # remove redundant log: if it is used it has been created before
            #log.info("deduction used", deduction=render_deduction(deduction))
            applying = True
            board_before = render_board(board, context=context)
            try:
                original_apply(board, deduction)
            except Exception as error:
                log.warning("application rejected", error_type=type(error).__name__, error=str(error))
                assert board_before == render_board(board, context=context), (
                    "Board was mutated by a rejected deduction"
                )
                raise
            else:
                show(board, "after application")
            finally:
                applying = False

        # Pytest may leave its progress marker on the current line, jump one line
        log.blank()
        log.info("test started", test=test.__name__)
        if args or kwargs:
            log.debug("parameters", args=args, kwargs=kwargs)
        with patch.object(Board, "__init__", traced_init), \
             patch.object(Board, "apply", traced_apply), \
             patch.object(Deduction, "__post_init__", traced_post_init):
            return test(*args, **kwargs)

    return wrapped

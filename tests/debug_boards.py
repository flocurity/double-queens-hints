"""Test-only tracing; pytest captures prints unless run with -s."""
from collections.abc import Callable
from functools import wraps
from typing import ParamSpec, TypeVar
from unittest.mock import patch

from double_queens import Board, Deduction, render_board, render_deduction

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

        def show(board: Board, event: str) -> None:
            index = next((i for i, item in enumerate(boards, 1) if item is board), None)
            if index is None:
                boards.append(board)
                index = len(boards)
            print(f"\n### Board {index}: {event}\n")
            print(render_board(board))

        @wraps(original_init)
        def traced_init(board: Board, *init_args, **init_kwargs) -> None:
            try:
                original_init(board, *init_args, **init_kwargs)
            except Exception as error:
                print(f"\nBoard construction rejected: {type(error).__name__}: {error}")
                raise
            if not applying:
                show(board, "created")

        def traced_post_init(deduction: Deduction) -> None:
            original_post_init(deduction)
            print("\n### Deduction created\n")
            print(render_deduction(deduction))

        def traced_apply(board: Board, deduction: Deduction) -> None:
            nonlocal applying
            show(board, "before application")
            print(render_deduction(deduction))
            applying = True
            try:
                original_apply(board, deduction)
            except Exception as error:
                print(f"\nApplication rejected: {type(error).__name__}: {error}")
                show(board, "after rejected application")
                raise
            else:
                show(board, "after application")
            finally:
                applying = False

        print(f"\n## {test.__name__}")
        if args or kwargs:
            print(f"Parameters: {args!r} {kwargs!r}")
        with patch.object(Board, "__init__", traced_init), \
             patch.object(Board, "apply", traced_apply), \
             patch.object(Deduction, "__post_init__", traced_post_init):
            return test(*args, **kwargs)

    return wrapped

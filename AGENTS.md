# AGENTS.md

## Project

Double Queens Hint is an explainable logical hint engine for the Double Queens puzzle.

Read SPEC.md before making architectural or logical changes.

## Core rule

The hint/deduction engine is the source of all logical solving intelligence.

solve_logically() must only repeatedly request and apply deductions produced
by the hint engine.

Never introduce hidden guessing, backtracking, exhaustive search, SAT/SMT,
or solution-based reasoning into human-facing hints.

## Python environment and dependencies

Use `uv` for Python environment and dependency management.

- Use `pyproject.toml` as the source of truth for project dependencies.
- Use `uv.lock` for reproducible dependency resolution and commit it to Git.
- Use `uv add <package>` to add runtime dependencies.
- Use `uv add --dev <package>` to add development/test dependencies.
- Use `uv remove <package>` to remove dependencies.
- Use `uv sync` to synchronize the development environment.
- Run Python commands through `uv run`.
- Run tests with `uv run pytest`.
- Do not create or maintain `requirements.txt` unless explicitly requested.
- Do not use `pip install` directly for project dependencies.
- Do not manually modify the `.venv` environment.
- If the project has not yet been initialized for uv, initialize/configure it
  using `pyproject.toml` before adding dependencies.
- Before coding, synchronize the environment with `uv sync` and run the
  existing test suite to establish a clean baseline.
- If dependency updates are explicitly requested, update them first and run
  the complete test suite before modifying application code.
- Do not upgrade dependencies opportunistically as part of an unrelated task.

## Development

- Use Python.
- Keep puzzle state, deduction rules, rendering, and solving separated.
- Every new logical rule requires unit tests.
- Every Deduction must retain enough structured provenance to explain itself.
- Prefer small, testable components.
- Run the complete test suite after changes.
- Do not silently weaken or bypass tests to make them pass.

## Code quality

- Use type hints for all public APIs.
- Prefer dataclasses and enums for domain concepts over loosely structured
  dictionaries and magic strings.
- Keep functions and classes focused on a single responsibility.
- Do not introduce abstractions unless they are justified by the current
  milestone or clearly required by SPEC.md.
- Prefer readable domain code over clever or overly generic code.

## Testing

- Use pytest.
- Tests must validate behavior, not implementation details.
- Every deduction rule must have positive and negative test cases.
- When fixing a bug, add a regression test before or alongside the fix.
- Do not modify or weaken an existing test merely to make the implementation pass.
- Run the complete test suite with `uv run pytest` before considering a task complete.

## Git and generated files

- Do not commit or modify files outside the repository.
- Do not commit `.venv`, caches, coverage output, IDE metadata, or other generated artifacts.
- Keep `.gitignore` appropriate for a Python/uv project.
- Do not create Git commits unless explicitly requested.

## Scope discipline

- Do not implement speculative features from future milestones.
- Do not add dependencies when the Python standard library is sufficient.
- If SPEC.md is ambiguous in a way that materially affects the architecture,
  stop and ask rather than silently choosing a major interpretation.
- Small implementation details may be decided autonomously when they do not
  affect the public architecture or puzzle semantics.

## Scope

Follow the milestone boundaries defined in SPEC.md.

Do not implement future milestones unless explicitly requested.